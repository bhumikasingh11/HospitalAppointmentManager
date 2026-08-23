import enum
from datetime import datetime, date, time
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Time,
    Boolean,
    ForeignKey,
    Enum,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


class RoleEnum(str, enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class AppointmentStatus(str, enum.Enum):
    HELD = "HELD"
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.PATIENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    doctor_profile = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")
    patient_appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="user", cascade="all, delete-orphan")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialization = Column(String(255), nullable=False)
    slot_duration = Column(Integer, default=30, nullable=False)  # in minutes

    user = relationship("User", back_populates="doctor_profile")
    working_hours = relationship("WorkingHour", back_populates="doctor", cascade="all, delete-orphan")
    leaves = relationship("DoctorLeave", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")


class WorkingHour(Base):
    __tablename__ = "working_hours"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    doctor = relationship("Doctor", back_populates="working_hours")


class DoctorLeave(Base):
    __tablename__ = "doctor_leaves"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    leave_date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)

    doctor = relationship("Doctor", back_populates="leaves")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    appointment_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.HELD, nullable=False)
    symptoms = Column(Text, nullable=True)
    pre_visit_summary = Column(Text, nullable=True)
    urgency = Column(String(50), nullable=True)
    post_visit_notes = Column(Text, nullable=True)
    post_visit_summary = Column(Text, nullable=True)
    # Patient response fields
    appointment_response = Column(String(50), nullable=True)   # ATTEND / LATE / RESCHEDULE
    follow_up_response = Column(String(50), nullable=True)     # BETTER / SAME / NOT_IMPROVING
    attendance_method = Column(String(50), nullable=True)      # CLINIC / RESCHEDULE
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("User", back_populates="patient_appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    prescriptions = relationship("Prescription", back_populates="appointment", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="appointment", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="appointment", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("doctor_id", "appointment_date", "start_time", name="uq_doctor_date_slot"),
    )


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    medicine_name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=False)
    frequency = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=False)
    instructions = Column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="prescriptions")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True)
    type = Column(String(50), nullable=False)  # BOOKING_CONFIRMATION, REMINDER, etc.
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, SENT, FAILED
    retry_count = Column(Integer, default=0, nullable=False)
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="notifications")
    appointment = relationship("Appointment", back_populates="notifications")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_event_id = Column(String(255), nullable=False)

    appointment = relationship("Appointment", back_populates="calendar_events")
    user = relationship("User", back_populates="calendar_events")
