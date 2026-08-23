from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Appointment, User, RoleEnum, AppointmentStatus
from app.auth import get_current_user, require_patient
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
    AppointmentResponse
)
from app.services.booking_service import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

class AppointmentResponseUpdate(BaseModel):
    response: str  # ATTEND / LATE / RESCHEDULE

class FollowUpResponseUpdate(BaseModel):
    response: str  # BETTER / SAME / NOT_IMPROVING

class AttendanceMethodUpdate(BaseModel):
    method: str  # CLINIC / RESCHEDULE

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    req: AppointmentCreateRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    appointment = book_appointment(
        db=db,
        patient_id=current_user.id,
        doctor_id=req.doctor_id,
        appointment_date=req.appointment_date,
        start_time=req.start_time,
        symptoms=req.symptoms
    )
    return appointment

@router.get("/my", response_model=List[AppointmentResponse])
def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == RoleEnum.PATIENT:
        return db.query(Appointment).filter(Appointment.patient_id == current_user.id).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()
    elif current_user.role == RoleEnum.DOCTOR:
        doctor_profile = current_user.doctor_profile
        if not doctor_profile:
            return []
        return db.query(Appointment).filter(Appointment.doctor_id == doctor_profile.id).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()
    elif current_user.role == RoleEnum.ADMIN:
        return db.query(Appointment).order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()
    return []

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment_by_id(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Access control
    if current_user.role == RoleEnum.PATIENT and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this appointment")
    if current_user.role == RoleEnum.DOCTOR:
        doctor_profile = current_user.doctor_profile
        if not doctor_profile or appointment.doctor_id != doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this appointment")

    return appointment

@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment_endpoint(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return cancel_appointment(db=db, appointment_id=appointment_id, user=current_user)

@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment_endpoint(
    appointment_id: int,
    req: AppointmentRescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        new_date=req.new_date,
        new_start_time=req.new_start_time,
        user=current_user
    )

@router.patch("/{appointment_id}/response", response_model=AppointmentResponse)
def set_appointment_response(
    appointment_id: int,
    req: AppointmentResponseUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    valid = {"ATTEND", "LATE", "RESCHEDULE"}
    if req.response not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Response must be one of: {valid}")
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == current_user.id,
        Appointment.status == AppointmentStatus.BOOKED
    ).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booked appointment not found")
    appt.appointment_response = req.response
    db.commit()
    db.refresh(appt)
    return appt

@router.patch("/{appointment_id}/followup", response_model=AppointmentResponse)
def set_follow_up_response(
    appointment_id: int,
    req: FollowUpResponseUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    valid = {"BETTER", "SAME", "NOT_IMPROVING"}
    if req.response not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Response must be one of: {valid}")
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == current_user.id,
        Appointment.status == AppointmentStatus.COMPLETED
    ).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completed appointment not found")
    appt.follow_up_response = req.response
    db.commit()
    db.refresh(appt)
    return appt

@router.patch("/{appointment_id}/attendance", response_model=AppointmentResponse)
def set_attendance_method(
    appointment_id: int,
    req: AttendanceMethodUpdate,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
):
    valid = {"CLINIC", "RESCHEDULE"}
    if req.method not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Method must be one of: {valid}")
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == current_user.id,
        Appointment.status == AppointmentStatus.BOOKED
    ).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booked appointment not found")
    appt.attendance_method = req.method
    db.commit()
    db.refresh(appt)
    return appt
