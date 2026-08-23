import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import User, Doctor, WorkingHour, DoctorLeave, Appointment, Prescription, Notification, CalendarEvent, RoleEnum, AppointmentStatus
from datetime import date, time, datetime

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Healthcare Appointment Manager"}

def test_database_models():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    
    # Test User creation
    patient = User(name="John Doe", email="john@example.com", password_hash="hash123", role=RoleEnum.PATIENT)
    doctor_user = User(name="Dr. Smith", email="smith@example.com", password_hash="hash456", role=RoleEnum.DOCTOR)
    db.add_all([patient, doctor_user])
    db.commit()

    # Test Doctor creation
    doctor = Doctor(user_id=doctor_user.id, specialization="Cardiology", slot_duration=30)
    db.add(doctor)
    db.commit()

    # Test Appointment creation
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date(2026, 9, 1),
        start_time=time(9, 0),
        end_time=time(9, 30),
        status=AppointmentStatus.BOOKED,
        symptoms="Chest pain"
    )
    db.add(appt)
    db.commit()

    # Test uniqueness constraint
    duplicate_appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date(2026, 9, 1),
        start_time=time(9, 0),
        end_time=time(9, 30),
        status=AppointmentStatus.HELD
    )
    db.add(duplicate_appt)
    with pytest.raises(Exception):
        db.commit()
    db.rollback()

    db.close()
