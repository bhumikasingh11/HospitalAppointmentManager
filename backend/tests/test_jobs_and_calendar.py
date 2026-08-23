import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, WorkingHour, Appointment, Notification, CalendarEvent, Prescription, RoleEnum, AppointmentStatus
from app.auth import hash_password, create_access_token
from app.services.notification_service import create_and_dispatch_notification
from app.services.calendar_service import create_calendar_event, delete_calendar_event
from app.tasks import cleanup_expired_holds_task, send_appointment_reminders_task, send_medication_reminders_task

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_notification_creation_and_calendar_sync():
    db = TestingSessionLocal()
    patient = User(name="David", email="david@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    doc_user = User(name="Dr. Sarah", email="sarah@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    db.add_all([patient, doc_user])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Neurology", slot_duration=30)
    db.add(doctor)
    db.commit()

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today() + timedelta(days=1),
        start_time=time(9, 0),
        end_time=time(9, 30),
        status=AppointmentStatus.BOOKED,
        symptoms="Migraine"
    )
    db.add(appt)
    db.commit()

    # 1. Create notification
    notif = create_and_dispatch_notification(
        db=db,
        user_id=patient.id,
        notification_type="BOOKING_CONFIRMATION",
        appointment_id=appt.id
    )
    assert notif.id is not None
    assert notif.status == "PENDING"
    assert notif.type == "BOOKING_CONFIRMATION"

    # 2. Create Calendar event
    event_id = create_calendar_event(db=db, appointment=appt)
    assert event_id is not None
    stored_event = db.query(CalendarEvent).filter(CalendarEvent.appointment_id == appt.id).first()
    assert stored_event is not None
    assert stored_event.google_event_id == event_id

    # 3. Delete Calendar event on cancel
    deleted = delete_calendar_event(db=db, appointment_id=appt.id)
    assert deleted is True
    assert db.query(CalendarEvent).filter(CalendarEvent.appointment_id == appt.id).first() is None
    db.close()

def test_background_jobs():
    db = TestingSessionLocal()
    with patch("app.tasks.SessionLocal", return_value=db):
        # 1. Test expired hold cleanup
        patient = User(name="Test", email="test@test.com", password_hash="pw", role=RoleEnum.PATIENT)
        doc_user = User(name="Doc", email="doc@test.com", password_hash="pw", role=RoleEnum.DOCTOR)
        db.add_all([patient, doc_user])
        db.commit()

        doctor = Doctor(user_id=doc_user.id, specialization="General", slot_duration=30)
        db.add(doctor)
        db.commit()

        expired_hold = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=date.today() + timedelta(days=2),
            start_time=time(14, 0),
            end_time=time(14, 30),
            status=AppointmentStatus.HELD,
            created_at=datetime.utcnow() - timedelta(minutes=10)
        )
        db.add(expired_hold)
        db.commit()

        cleaned_count = cleanup_expired_holds_task()
        assert cleaned_count >= 1
        db.refresh(expired_hold)
        assert expired_hold.status == AppointmentStatus.CANCELLED
    db.close()
