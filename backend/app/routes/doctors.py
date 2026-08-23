from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models import Doctor, User
from app.schemas.doctor import DoctorResponse, SlotResponse
from app.services.slot_service import generate_doctor_slots

router = APIRouter(prefix="/api/doctors", tags=["Doctors"])

@router.get("", response_model=List[DoctorResponse])
def list_doctors(
    specialization: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Doctor).join(Doctor.user)
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    if search:
        query = query.filter(
            (Doctor.specialization.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )
    return query.all()

@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor

@router.get("/{doctor_id}/slots", response_model=List[SlotResponse])
def get_doctor_slots(
    doctor_id: int,
    date_val: date = Query(..., alias="date"),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    slots = generate_doctor_slots(db=db, doctor_id=doctor_id, target_date=date_val)
    return slots
