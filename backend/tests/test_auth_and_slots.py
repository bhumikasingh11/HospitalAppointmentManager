import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, WorkingHour, DoctorLeave, Appointment, RoleEnum, AppointmentStatus
from app.auth import hash_password, create_access_token
from app.services.slot_service import generate_doctor_slots

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

def test_auth_registration_and_login():
    reg_resp = client.post("/api/auth/register", json={
        "name": "Alice Patient",
        "email": "alice@test.com",
        "password": "secretpassword",
        "role": "PATIENT"
    })
    assert reg_resp.status_code == 201
    assert reg_resp.json()["email"] == "alice@test.com"

    login_resp = client.post("/api/auth/login", json={
        "email": "alice@test.com",
        "password": "secretpassword"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token is not None

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "Alice Patient"

def test_slot_generation():
    db = TestingSessionLocal()
    # 1. Create doctor
    doc_user = User(name="Dr. House", email="house@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    db.add(doc_user)
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Diagnostics", slot_duration=30)
    db.add(doctor)
    db.commit()

    # Suppose target date is next Monday
    today = date.today()
    days_until_monday = (0 - today.weekday() + 7) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    target_date = today + timedelta(days=days_until_monday)

    # Set working hours: Monday (day 0) 09:00 - 11:00 (4 slots: 09:00, 09:30, 10:00, 10:30)
    wh = WorkingHour(doctor_id=doctor.id, day_of_week=target_date.weekday(), start_time=time(9, 0), end_time=time(11, 0))
    db.add(wh)
    db.commit()

    # Slots before bookings
    slots = generate_doctor_slots(db, doctor.id, target_date, current_datetime=datetime.combine(today, time(8, 0)))
    assert len(slots) == 4
    assert slots[0]["start_time"] == time(9, 0)
    assert slots[0]["end_time"] == time(9, 30)

    # Add a booked appointment at 09:30
    patient = User(name="Bob", email="bob@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    db.add(patient)
    db.commit()

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=target_date,
        start_time=time(9, 30),
        end_time=time(10, 0),
        status=AppointmentStatus.BOOKED
    )
    db.add(appt)
    db.commit()

    # Slots after booking: 09:30 should be excluded -> 3 slots remaining
    slots_after = generate_doctor_slots(db, doctor.id, target_date, current_datetime=datetime.combine(today, time(8, 0)))
    assert len(slots_after) == 3
    starts = [s["start_time"] for s in slots_after]
    assert time(9, 30) not in starts
    assert time(9, 0) in starts
    assert time(10, 0) in starts

    # Set leave on target_date -> slots should be empty
    leave = DoctorLeave(doctor_id=doctor.id, leave_date=target_date, reason="Conference")
    db.add(leave)
    db.commit()

    slots_on_leave = generate_doctor_slots(db, doctor.id, target_date, current_datetime=datetime.combine(today, time(8, 0)))
    assert len(slots_on_leave) == 0
    db.close()
