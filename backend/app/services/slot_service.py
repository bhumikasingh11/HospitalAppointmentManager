from datetime import datetime, date, time, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Doctor, WorkingHour, DoctorLeave, Appointment, AppointmentStatus

def generate_doctor_slots(
    db: Session,
    doctor_id: int,
    target_date: date,
    current_datetime: datetime = None
) -> List[Dict[str, time]]:
    if current_datetime is None:
        current_datetime = datetime.utcnow()

    # 1. Check if doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return []

    # 2. Check if the target date is in the past
    if target_date < current_datetime.date():
        return []

    # 3. Check if doctor is on leave on target_date
    leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor_id,
        DoctorLeave.leave_date == target_date
    ).first()
    if leave:
        return []

    # 4. Get working hours for the day of the week (0=Monday, 6=Sunday)
    day_of_week = target_date.weekday()
    working_hours = db.query(WorkingHour).filter(
        WorkingHour.doctor_id == doctor_id,
        WorkingHour.day_of_week == day_of_week
    ).all()

    if not working_hours:
        return []

    # 5. Fetch booked or held appointments for this doctor on target_date
    existing_appts = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == target_date,
        Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.HELD])
    ).all()
    
    busy_starts = {appt.start_time for appt in existing_appts}

    slot_duration = timedelta(minutes=doctor.slot_duration)
    available_slots: List[Dict[str, time]] = []
    seen_starts = set()

    for wh in working_hours:
        curr_dt = datetime.combine(target_date, wh.start_time)
        end_dt = datetime.combine(target_date, wh.end_time)

        while curr_dt + slot_duration <= end_dt:
            slot_start = curr_dt.time()
            slot_end = (curr_dt + slot_duration).time()

            # Exclude past slots if date is today
            is_past = (
                target_date == current_datetime.date()
                and slot_start <= current_datetime.time()
            )

            # Exclude busy slots (HELD or BOOKED) and deduplicate
            if not is_past and slot_start not in busy_starts and slot_start not in seen_starts:
                seen_starts.add(slot_start)
                available_slots.append({
                    "start_time": slot_start,
                    "end_time": slot_end
                })

            curr_dt += slot_duration

    # Sort slots by start_time
    available_slots.sort(key=lambda s: s["start_time"])
    return available_slots
