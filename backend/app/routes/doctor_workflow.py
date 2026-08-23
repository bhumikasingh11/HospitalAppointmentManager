from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Appointment, Doctor, Prescription, AppointmentStatus, User
from app.auth import require_doctor
from app.schemas.doctor_workflow import (
    CompleteAppointmentRequest,
    DoctorAppointmentDetailResponse
)
from app.services.llm_service import generate_post_visit_summary

router = APIRouter(prefix="/api/doctor/appointments", tags=["Doctor Workflow"])

@router.get("", response_model=List[DoctorAppointmentDetailResponse])
def get_doctor_appointments(
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found for this account")

    appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_profile.id
    ).order_by(Appointment.appointment_date.desc(), Appointment.start_time.asc()).all()

    return appointments

@router.get("/{appointment_id}", response_model=DoctorAppointmentDetailResponse)
def get_doctor_appointment_detail(
    appointment_id: int,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.doctor_id != doctor_profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. This appointment belongs to another doctor.")

    return appointment

@router.post("/{appointment_id}/complete", response_model=DoctorAppointmentDetailResponse)
def complete_appointment(
    appointment_id: int,
    req: CompleteAppointmentRequest,
    current_user: User = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.doctor_id != doctor_profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. This appointment belongs to another doctor.")

    # 1. Save doctor notes
    appointment.post_visit_notes = req.notes

    # 2. Save prescriptions
    # Clear existing if any
    db.query(Prescription).filter(Prescription.appointment_id == appointment.id).delete()
    
    prescription_dicts = []
    for p in req.prescriptions:
        presc = Prescription(
            appointment_id=appointment.id,
            medicine_name=p.medicine_name,
            dosage=p.dosage,
            frequency=p.frequency,
            duration=p.duration,
            instructions=p.instructions
        )
        db.add(presc)
        prescription_dicts.append(p.dict())

    # 3. Generate patient-friendly summary with safe fallback
    summary_data = generate_post_visit_summary(
        notes=req.notes,
        prescriptions=prescription_dicts
    )

    formatted_summary = (
        f"{summary_data.get('patient_friendly_summary', '')}\n\n"
        f"Medication Schedule:\n{summary_data.get('medication_schedule', '')}\n\n"
        f"Follow-up Steps:\n{summary_data.get('follow_up_steps', '')}"
    )
    appointment.post_visit_summary = formatted_summary

    # 4. Mark status COMPLETED
    appointment.status = AppointmentStatus.COMPLETED

    db.commit()
    db.refresh(appointment)
    return appointment
