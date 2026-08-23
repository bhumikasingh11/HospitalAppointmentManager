from datetime import datetime, date, time, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import Doctor, WorkingHour, DoctorLeave, Appointment, AppointmentStatus, User

HOLD_DURATION_MINUTES = 5

def clean_expired_holds(db: Session, doctor_id: int, appt_date: date, start_time: time):
    cutoff = datetime.utcnow() - timedelta(minutes=HOLD_DURATION_MINUTES)
    expired_holds = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appt_date,
        Appointment.start_time == start_time,
        Appointment.status == AppointmentStatus.HELD,
        Appointment.created_at < cutoff
    ).all()
    for hold in expired_holds:
        hold.status = AppointmentStatus.CANCELLED
    if expired_holds:
        db.commit()

def validate_slot_availability(db: Session, doctor: Doctor, appt_date: date, start_time: time) -> time:
    # 1. Date cannot be in the past
    now = datetime.utcnow()
    if appt_date < now.date():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot book an appointment in the past")
    if appt_date == now.date() and start_time <= now.time():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot book a past slot today")

    # 2. Check doctor leaves
    leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor.id,
        DoctorLeave.leave_date == appt_date
    ).first()
    if leave:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor is on leave on this date")

    # 3. Check working hours
    day_of_week = appt_date.weekday()
    working_hours = db.query(WorkingHour).filter(
        WorkingHour.doctor_id == doctor.id,
        WorkingHour.day_of_week == day_of_week
    ).all()

    slot_duration = timedelta(minutes=doctor.slot_duration)
    slot_dt = datetime.combine(appt_date, start_time)
    end_dt = slot_dt + slot_duration
    end_time = end_dt.time()

    is_valid_wh = False
    for wh in working_hours:
        wh_start_dt = datetime.combine(appt_date, wh.start_time)
        wh_end_dt = datetime.combine(appt_date, wh.end_time)
        if slot_dt >= wh_start_dt and end_dt <= wh_end_dt:
            # Check slot alignment
            minutes_from_start = int((slot_dt - wh_start_dt).total_seconds() / 60)
            if minutes_from_start % doctor.slot_duration == 0:
                is_valid_wh = True
                break

    if not is_valid_wh:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot is not within doctor's working hours")

    # 4. Clean expired holds
    clean_expired_holds(db, doctor.id, appt_date, start_time)

    # 5. Check active bookings or active holds
    existing = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == appt_date,
        Appointment.start_time == start_time,
        Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.HELD])
    ).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot was just booked. Please select another.")

    return end_time

def book_appointment(
    db: Session,
    patient_id: int,
    doctor_id: int,
    appointment_date: date,
    start_time: time,
    symptoms: str = None
) -> Appointment:
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    end_time = validate_slot_availability(db, doctor, appointment_date, start_time)

    try:
        # Step 1: Create HELD appointment
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.HELD,
            symptoms=symptoms
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        # Generate pre-visit summary without breaking booking on error
        try:
            from app.services.llm_service import generate_pre_visit_summary
            ai_data = generate_pre_visit_summary(
                symptoms=symptoms or "",
                specialization=doctor.specialization if doctor else "General Medicine"
            )
            appointment.pre_visit_summary = f"{ai_data.get('chief_complaint', '')}\n\nSuggested Questions:\n" + "\n".join(f"- {q}" for q in ai_data.get("suggested_questions", []))
            appointment.urgency = ai_data.get("urgency", "Medium")
        except Exception:
            pass

        # Step 2: Transition from HELD to BOOKED
        appointment.status = AppointmentStatus.BOOKED
        db.commit()
        db.refresh(appointment)

        # Trigger notification & Google Calendar event safely
        try:
            from app.services.notification_service import create_and_dispatch_notification
            create_and_dispatch_notification(
                db=db,
                user_id=patient_id,
                notification_type="BOOKING_CONFIRMATION",
                appointment_id=appointment.id
            )
        except Exception:
            pass

        try:
            from app.services.calendar_service import create_calendar_event
            create_calendar_event(db=db, appointment=appointment)
        except Exception:
            pass

        return appointment

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot was just booked. Please select another."
        )

def cancel_appointment(db: Session, appointment_id: int, user: User) -> Appointment:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if user.role.value == "PATIENT" and appointment.patient_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this appointment")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment is already cancelled")

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(appointment)

    # Safe notification and calendar deletion
    try:
        from app.services.notification_service import create_and_dispatch_notification
        create_and_dispatch_notification(
            db=db,
            user_id=appointment.patient_id,
            notification_type="CANCELLATION",
            appointment_id=appointment.id
        )
    except Exception:
        pass

    try:
        from app.services.calendar_service import delete_calendar_event
        delete_calendar_event(db=db, appointment_id=appointment.id)
    except Exception:
        pass

    return appointment

def reschedule_appointment(
    db: Session,
    appointment_id: int,
    new_date: date,
    new_start_time: time,
    user: User
) -> Appointment:
    old_appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not old_appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if user.role.value == "PATIENT" and old_appointment.patient_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reschedule this appointment")

    if old_appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reschedule a cancelled appointment")

    doctor = db.query(Doctor).filter(Doctor.id == old_appointment.doctor_id).first()
    new_end_time = validate_slot_availability(db, doctor, new_date, new_start_time)

    try:
        # Reserve new slot with a new appointment entry in HELD state
        new_appointment = Appointment(
            patient_id=old_appointment.patient_id,
            doctor_id=old_appointment.doctor_id,
            appointment_date=new_date,
            start_time=new_start_time,
            end_time=new_end_time,
            status=AppointmentStatus.BOOKED,
            symptoms=old_appointment.symptoms,
            pre_visit_summary=old_appointment.pre_visit_summary,
            urgency=old_appointment.urgency
        )
        db.add(new_appointment)
        # Release old slot by cancelling it
        old_appointment.status = AppointmentStatus.CANCELLED
        db.commit()
        db.refresh(new_appointment)

        # Update or create calendar event
        try:
            from app.services.calendar_service import create_calendar_event
            create_calendar_event(db=db, appointment=new_appointment)
        except Exception:
            pass

        try:
            from app.services.notification_service import create_and_dispatch_notification
            create_and_dispatch_notification(
                db=db,
                user_id=new_appointment.patient_id,
                notification_type="BOOKING_CONFIRMATION",
                appointment_id=new_appointment.id
            )
        except Exception:
            pass

        return new_appointment

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot was just booked. Please select another."
        )
