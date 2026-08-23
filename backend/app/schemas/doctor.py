from pydantic import BaseModel
from typing import List, Optional
from datetime import date, time
from app.schemas.auth import UserResponse

class WorkingHourCreate(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: time
    end_time: time

class WorkingHourResponse(BaseModel):
    id: int
    day_of_week: int
    start_time: time
    end_time: time

    class Config:
        from_attributes = True

class DoctorLeaveCreate(BaseModel):
    leave_date: date
    reason: Optional[str] = None

class DoctorLeaveResponse(BaseModel):
    id: int
    leave_date: date
    reason: Optional[str]

    class Config:
        from_attributes = True

class DoctorCreateRequest(BaseModel):
    user_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    specialization: str
    slot_duration: int = 30

class DoctorUpdateRequest(BaseModel):
    specialization: Optional[str] = None
    slot_duration: Optional[int] = None

class DoctorResponse(BaseModel):
    id: int
    user_id: int
    specialization: str
    slot_duration: int
    user: Optional[UserResponse] = None
    working_hours: List[WorkingHourResponse] = []
    leaves: List[DoctorLeaveResponse] = []

    class Config:
        from_attributes = True

class SlotResponse(BaseModel):
    start_time: time
    end_time: time
