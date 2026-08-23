import pytest
from datetime import date, time, timedelta, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, WorkingHour, RoleEnum
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

def test_no_duplicate_slots_even_with_duplicate_working_hours():
    db = TestingSessionLocal()
    # 1. Create doctor
    doc_user = User(name="Dr. Single Slot", email="singleslot@hospital.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    patient = User(name="Pat", email="pat@hospital.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    db.add_all([doc_user, patient])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Dermatology", slot_duration=30)
    db.add(doctor)
    db.commit()

    target_date = date.today() + timedelta(days=2)
    weekday = target_date.weekday()

    # Intentionally insert duplicate working hours for the same weekday (09:00 - 10:00)
    wh1 = WorkingHour(doctor_id=doctor.id, day_of_week=weekday, start_time=time(9, 0), end_time=time(10, 0))
    wh2 = WorkingHour(doctor_id=doctor.id, day_of_week=weekday, start_time=time(9, 0), end_time=time(10, 0))
    db.add_all([wh1, wh2])
    db.commit()

    # 2. Query slot service
    slots = generate_doctor_slots(db, doctor.id, target_date, current_datetime=datetime.combine(date.today(), time(8, 0)))
    # For 09:00 to 10:00 with 30-min duration, there should be exactly 2 slots: 09:00 and 09:30
    assert len(slots) == 2
    assert [s["start_time"] for s in slots] == [time(9, 0), time(9, 30)]

    # 3. Query via API endpoint
    api_res = client.get(f"/api/doctors/{doctor.id}/slots?date={target_date}")
    assert api_res.status_code == 200
    api_slots = api_res.json()
    assert len(api_slots) == 2
    starts = [s["start_time"] for s in api_slots]
    assert starts == ["09:00:00", "09:30:00"]
    # Check no duplicates
    assert len(starts) == len(set(starts))

    # 4. Verify booking a slot still works
    token = create_access_token({"sub": str(patient.id), "role": "PATIENT"})
    book_res = client.post("/api/appointments", json={
        "doctor_id": doctor.id,
        "appointment_date": str(target_date),
        "start_time": "09:00:00",
        "symptoms": "Skin allergy"
    }, headers={"Authorization": f"Bearer {token}"})
    assert book_res.status_code == 201
    assert book_res.json()["status"] == "BOOKED"

    # 5. After booking, 09:00 should be excluded, leaving exactly 1 slot (09:30)
    slots_after = client.get(f"/api/doctors/{doctor.id}/slots?date={target_date}").json()
    assert len(slots_after) == 1
    assert slots_after[0]["start_time"] == "09:30:00"

    db.close()
