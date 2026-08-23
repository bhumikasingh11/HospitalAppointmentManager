from pydantic import BaseModel
from typing import Optional
from datetime import date, time, datetime
from app.models import AppointmentStatus
from app.schemas.doctor import DoctorResponse
from app.schemas.auth import UserResponse

class AppointmentCreateRequest(BaseModel):
    doctor_id: int
    appointment_date: date
    start_time: time
    symptoms: Optional[str] = None

class AppointmentRescheduleRequest(BaseModel):
    new_date: date
    new_start_time: time

class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    symptoms: Optional[str] = None
    pre_visit_summary: Optional[str] = None
    urgency: Optional[str] = None
    post_visit_notes: Optional[str] = None
    post_visit_summary: Optional[str] = None
    appointment_response: Optional[str] = None
    follow_up_response: Optional[str] = None
    attendance_method: Optional[str] = None
    created_at: datetime
    doctor: Optional[DoctorResponse] = None
    patient: Optional[UserResponse] = None

    class Config:
        from_attributes = True
