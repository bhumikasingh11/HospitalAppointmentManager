import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, WorkingHour, Appointment, RoleEnum, AppointmentStatus
from app.auth import hash_password, create_access_token

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

def test_booking_flow_and_conflict():
    db = TestingSessionLocal()
    # Create doctor & patient
    patient = User(name="Alice", email="alice@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    patient2 = User(name="Bob", email="bob@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    doc_user = User(name="Dr. House", email="house@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    db.add_all([patient, patient2, doc_user])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Cardiology", slot_duration=30)
    db.add(doctor)
    db.commit()

    target_date = date.today() + timedelta(days=2)
    wh = WorkingHour(doctor_id=doctor.id, day_of_week=target_date.weekday(), start_time=time(9, 0), end_time=time(12, 0))
    db.add(wh)
    db.commit()

    token1 = create_access_token({"sub": str(patient.id), "role": "PATIENT"})
    token2 = create_access_token({"sub": str(patient2.id), "role": "PATIENT"})

    # 1. Successful booking
    resp1 = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(target_date),
        "start_time": "09:00:00",
        "symptoms": "Headache"
    }, headers={"Authorization": f"Bearer {token1}"})

    assert resp1.status_code == 201
    appt_data = resp1.json()
    assert appt_data["status"] == "BOOKED"
    assert appt_data["start_time"] == "09:00:00"
    assert appt_data["end_time"] == "09:30:00"

    # 2. Conflicting booking for the same slot -> 409
    resp2 = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(target_date),
        "start_time": "09:00:00",
        "symptoms": "Dizziness"
    }, headers={"Authorization": f"Bearer {token2}"})

    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Slot was just booked. Please select another."

    # 3. Cancel appointment
    cancel_resp = client.post(f"/api/appointments/{appt_data['id']}/cancel", headers={"Authorization": f"Bearer {token1}"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # 4. Now that old slot is cancelled, patient2 can book it
    resp3 = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(target_date),
        "start_time": "09:00:00",
        "symptoms": "Dizziness"
    }, headers={"Authorization": f"Bearer {token2}"})
    assert resp3.status_code == 201
    assert resp3.json()["status"] == "BOOKED"
    db.close()
