from pydantic import BaseModel
from typing import List, Optional
from app.schemas.appointment import AppointmentResponse

class PrescriptionItem(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None

class PrescriptionResponse(BaseModel):
    id: int
    appointment_id: int
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None

    class Config:
        from_attributes = True

class CompleteAppointmentRequest(BaseModel):
    notes: str
    prescriptions: List[PrescriptionItem] = []

class DoctorAppointmentDetailResponse(AppointmentResponse):
    prescriptions: List[PrescriptionResponse] = []

    class Config:
        from_attributes = True
