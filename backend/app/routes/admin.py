from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import (
    Doctor,
    User,
    WorkingHour,
    DoctorLeave,
    Appointment,
    RoleEnum,
    AppointmentStatus,
)
from app.auth import require_admin
from app.schemas.doctor import (
    DoctorCreateRequest,
    DoctorUpdateRequest,
    DoctorResponse,
    WorkingHourCreate,
    WorkingHourResponse,
    DoctorLeaveCreate,
    DoctorLeaveResponse
)

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

@router.get("/doctors", response_model=List[DoctorResponse])
def list_doctors_admin(db: Session = Depends(get_db)):
    return db.query(Doctor).all()

@router.post("/doctors", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_admin(req: DoctorCreateRequest, db: Session = Depends(get_db)):
    from app.auth import hash_password

    if req.user_id:
        user = db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.role = RoleEnum.DOCTOR
    else:
        if not req.email or not req.password or not req.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or (name, email, password) must be provided"
            )
        existing_user = db.query(User).filter(User.email == req.email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
        user = User(
            name=req.name,
            email=req.email,
            password_hash=hash_password(req.password),
            role=RoleEnum.DOCTOR
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    existing_doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if existing_doctor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile already exists for this user")

    doctor = Doctor(
        user_id=user.id,
        specialization=req.specialization,
        slot_duration=req.slot_duration
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

@router.put("/doctors/{doctor_id}", response_model=DoctorResponse)
def update_doctor_admin(doctor_id: int, req: DoctorUpdateRequest, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    
    if req.specialization is not None:
        doctor.specialization = req.specialization
    if req.slot_duration is not None:
        doctor.slot_duration = req.slot_duration

    db.commit()
    db.refresh(doctor)
    return doctor

@router.post("/doctors/{doctor_id}/working-hours", response_model=WorkingHourResponse, status_code=status.HTTP_201_CREATED)
def set_working_hours(doctor_id: int, req: WorkingHourCreate, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    
    existing_wh = db.query(WorkingHour).filter(
        WorkingHour.doctor_id == doctor_id,
        WorkingHour.day_of_week == req.day_of_week,
        WorkingHour.start_time == req.start_time
    ).first()
    if existing_wh:
        existing_wh.end_time = req.end_time
        db.commit()
        db.refresh(existing_wh)
        return existing_wh

    wh = WorkingHour(
        doctor_id=doctor_id,
        day_of_week=req.day_of_week,
        start_time=req.start_time,
        end_time=req.end_time
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh

@router.post("/doctors/{doctor_id}/leaves", response_model=DoctorLeaveResponse, status_code=status.HTTP_201_CREATED)
def set_doctor_leave(doctor_id: int, req: DoctorLeaveCreate, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    try:
        # 1. Save leave record
        leave = DoctorLeave(
            doctor_id=doctor_id,
            leave_date=req.leave_date,
            reason=req.reason
        )
        db.add(leave)

        # 2. Find existing active appointments on leave date
        affected_appts = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == req.leave_date,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.HELD])
        ).all()

        # 3. Mark affected appointments as CANCELLED and queue notifications
        from app.services.notification_service import create_and_dispatch_notification
        from app.services.calendar_service import delete_calendar_event

        for appt in affected_appts:
            appt.status = AppointmentStatus.CANCELLED
            
            # Queue notification for affected patient
            create_and_dispatch_notification(
                db=db,
                user_id=appt.patient_id,
                notification_type="DOCTOR_LEAVE_CANCELLATION",
                appointment_id=appt.id
            )

            # Delete Google Calendar event if present
            try:
                delete_calendar_event(db=db, appointment_id=appt.id)
            except Exception:
                pass

        db.commit()
        db.refresh(leave)
        return leave

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to record leave: {str(e)}")
