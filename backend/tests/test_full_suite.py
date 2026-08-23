import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import (
    User, Doctor, WorkingHour, DoctorLeave, Appointment,
    Prescription, Notification, CalendarEvent, RoleEnum, AppointmentStatus
)
from app.auth import hash_password, create_access_token
from app.services.llm_service import generate_pre_visit_summary, generate_post_visit_summary
from app.services.slot_service import generate_doctor_slots
from app.services.calendar_service import create_calendar_event, update_calendar_event, delete_calendar_event
from app.tasks import (
    send_notification_email_task,
    cleanup_expired_holds_task,
    send_appointment_reminders_task,
    send_medication_reminders_task
)

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

# 1. Auth & Roles
def test_full_auth_and_roles():
    # Register Patient
    p_res = client.post("/api/auth/register", json={
        "name": "Patient One",
        "email": "p1@test.com",
        "password": "pass",
        "role": "PATIENT"
    })
    assert p_res.status_code == 201

    # Login
    l_res = client.post("/api/auth/login", json={"email": "p1@test.com", "password": "pass"})
    assert l_res.status_code == 200
    token = l_res.json()["access_token"]

    # Role guard check: Patient cannot access admin endpoint
    admin_guard = client.get("/api/admin/doctors", headers={"Authorization": f"Bearer {token}"})
    assert admin_guard.status_code == 403

# 2. Doctor Search & Slots
def test_doctor_search_and_slots():
    db = TestingSessionLocal()
    doc_user = User(name="Dr. Gregory House", email="house@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    db.add(doc_user)
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Diagnostics", slot_duration=30)
    db.add(doctor)
    db.commit()

    # Search doctors
    search_res = client.get("/api/doctors?specialization=Diagnostics")
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1

    # Add working hours for tomorrow
    tomorrow = date.today() + timedelta(days=1)
    wh = WorkingHour(doctor_id=doctor.id, day_of_week=tomorrow.weekday(), start_time=time(9, 0), end_time=time(10, 0))
    db.add(wh)
    db.commit()

    # Get slots
    slots_res = client.get(f"/api/doctors/{doctor.id}/slots?date={tomorrow}")
    assert slots_res.status_code == 200
    assert len(slots_res.json()) == 2
    db.close()

# 3. Booking, Simultaneous Concurrency & 5-minute Hold
def test_booking_simultaneous_and_hold():
    db = TestingSessionLocal()
    patient1 = User(name="User 1", email="u1@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    patient2 = User(name="User 2", email="u2@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    doc_user = User(name="Dr. Strange", email="strange@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    db.add_all([patient1, patient2, doc_user])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Surgery", slot_duration=30)
    db.add(doctor)
    db.commit()

    booking_date = date.today() + timedelta(days=2)
    wh = WorkingHour(doctor_id=doctor.id, day_of_week=booking_date.weekday(), start_time=time(9, 0), end_time=time(11, 0))
    db.add(wh)
    db.commit()

    t1 = create_access_token({"sub": str(patient1.id), "role": "PATIENT"})
    t2 = create_access_token({"sub": str(patient2.id), "role": "PATIENT"})

    # First booking succeeds
    res1 = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(booking_date),
        "start_time": "09:00:00",
        "symptoms": "Severe pain"
    }, headers={"Authorization": f"Bearer {t1}"})
    assert res1.status_code == 201

    # Simultaneous duplicate slot booking returns 409
    res2 = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(booking_date),
        "start_time": "09:00:00",
        "symptoms": "Pain"
    }, headers={"Authorization": f"Bearer {t2}"})
    assert res2.status_code == 409
    assert "Slot was just booked" in res2.json()["detail"]

    # 5-minute hold expiration cleanup
    expired_hold = Appointment(
        patient_id=patient2.id,
        doctor_id=doctor.id,
        appointment_date=booking_date,
        start_time=time(10, 0),
        end_time=time(10, 30),
        status=AppointmentStatus.HELD,
        created_at=datetime.utcnow() - timedelta(minutes=6)
    )
    db.add(expired_hold)
    db.commit()

    cleaned = cleanup_expired_holds_task()
    assert cleaned >= 1
    db.refresh(expired_hold)
    assert expired_hold.status == AppointmentStatus.CANCELLED
    db.close()

# 4. Cancel & Reschedule
def test_cancel_and_reschedule():
    db = TestingSessionLocal()
    patient = User(name="User 3", email="u3@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    doc_user = User(name="Dr. Watson", email="watson@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    db.add_all([patient, doc_user])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="General", slot_duration=30)
    db.add(doctor)
    db.commit()

    d1 = date.today() + timedelta(days=2)
    d2 = date.today() + timedelta(days=3)

    wh1 = WorkingHour(doctor_id=doctor.id, day_of_week=d1.weekday(), start_time=time(9, 0), end_time=time(12, 0))
    wh2 = WorkingHour(doctor_id=doctor.id, day_of_week=d2.weekday(), start_time=time(9, 0), end_time=time(12, 0))
    db.add_all([wh1, wh2])
    db.commit()

    token = create_access_token({"sub": str(patient.id), "role": "PATIENT"})

    # Book initial appointment
    res = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(d1),
        "start_time": "09:00:00",
        "symptoms": "Cough"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # Reschedule to d2 at 10:00:00
    resched = client.post(f"/api/appointments/{appt_id}/reschedule", json={
        "new_date": str(d2),
        "new_start_time": "10:00:00"
    }, headers={"Authorization": f"Bearer {token}"})
    assert resched.status_code == 200
    new_id = resched.json()["id"]
    assert resched.json()["start_time"] == "10:00:00"

    # Old appointment cancelled
    old = db.query(Appointment).filter(Appointment.id == appt_id).first()
    assert old.status == AppointmentStatus.CANCELLED

    # Cancel new appointment
    canc = client.post(f"/api/appointments/{new_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert canc.status_code == 200
    assert canc.json()["status"] == "CANCELLED"
    db.close()

# 5. Doctor Leave Conflict Handling
def test_doctor_leave_conflict():
    db = TestingSessionLocal()
    admin = User(name="Admin", email="ad@test.com", password_hash="pw", role=RoleEnum.ADMIN)
    patient = User(name="Pat", email="pat@test.com", password_hash="pw", role=RoleEnum.PATIENT)
    doc_user = User(name="Doc", email="doc@test.com", password_hash="pw", role=RoleEnum.DOCTOR)
    db.add_all([admin, patient, doc_user])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Cardiology", slot_duration=30)
    db.add(doctor)
    db.commit()

    target_date = date.today() + timedelta(days=4)
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=target_date,
        start_time=time(9, 0),
        end_time=time(9, 30),
        status=AppointmentStatus.BOOKED
    )
    db.add(appt)
    db.commit()

    admin_token = create_access_token({"sub": str(admin.id), "role": "ADMIN"})

    leave_res = client.post(f"/api/admin/doctors/{doctor.id}/leaves", json={
        "leave_date": str(target_date),
        "reason": "Personal"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert leave_res.status_code == 201

    db.refresh(appt)
    assert appt.status == AppointmentStatus.CANCELLED
    notif = db.query(Notification).filter(Notification.appointment_id == appt.id).first()
    assert notif is not None
    assert notif.type == "DOCTOR_LEAVE_CANCELLATION"
    db.close()

# 6. AI Success & Fallback
def test_ai_fallback_and_doctor_notes():
    # Test safe fallback
    ai_pre = generate_pre_visit_summary("")
    assert ai_pre["urgency"] == "Low"

    ai_post = generate_post_visit_summary("", [])
    assert "patient_friendly_summary" in ai_post

# 7. Calendar Create, Update, Delete
def test_calendar_crud():
    db = TestingSessionLocal()
    patient = User(name="CalUser", email="cal@test.com", password_hash="pw", role=RoleEnum.PATIENT)
    doc_user = User(name="CalDoc", email="caldoc@test.com", password_hash="pw", role=RoleEnum.DOCTOR)
    db.add_all([patient, doc_user])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Derm", slot_duration=30)
    db.add(doctor)
    db.commit()

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today() + timedelta(days=1),
        start_time=time(9, 0),
        end_time=time(9, 30),
        status=AppointmentStatus.BOOKED
    )
    db.add(appt)
    db.commit()

    event_id = create_calendar_event(db, appt)
    assert event_id != ""

    updated = update_calendar_event(db, appt)
    assert updated is True

    deleted = delete_calendar_event(db, appt.id)
    assert deleted is True
    db.close()
