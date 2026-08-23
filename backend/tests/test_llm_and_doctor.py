import pytest
from datetime import date, time, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, WorkingHour, Appointment, Prescription, RoleEnum, AppointmentStatus
from app.auth import hash_password, create_access_token
from app.services.llm_service import generate_pre_visit_summary, generate_post_visit_summary

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

def test_llm_fallbacks():
    # When no API key is provided, should gracefully return safe fallbacks
    pre_visit = generate_pre_visit_summary("Severe chest pain and cough")
    assert "urgency" in pre_visit
    assert "chief_complaint" in pre_visit
    assert "suggested_questions" in pre_visit
    assert len(pre_visit["suggested_questions"]) == 3

    post_visit = generate_post_visit_summary(
        notes="Patient diagnosed with acute bronchitis.",
        prescriptions=[{"medicine_name": "Amoxicillin", "dosage": "500mg", "frequency": "3 times daily", "duration": "7 days", "instructions": "Take with food"}]
    )
    assert "patient_friendly_summary" in post_visit
    assert "medication_schedule" in post_visit
    assert "follow_up_steps" in post_visit

def test_doctor_workflow():
    db = TestingSessionLocal()
    # Create doctor 1, doctor 2, and patient
    doc_user1 = User(name="Dr. Gregory", email="gregory@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    doc_user2 = User(name="Dr. Cuddy", email="cuddy@test.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    patient = User(name="Alice", email="alice@test.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    db.add_all([doc_user1, doc_user2, patient])
    db.commit()

    doctor1 = Doctor(user_id=doc_user1.id, specialization="Internal Medicine", slot_duration=30)
    doctor2 = Doctor(user_id=doc_user2.id, specialization="Endocrinology", slot_duration=30)
    db.add_all([doctor1, doctor2])
    db.commit()

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor1.id,
        appointment_date=date.today() + timedelta(days=1),
        start_time=time(10, 0),
        end_time=time(10, 30),
        status=AppointmentStatus.BOOKED,
        symptoms="Persistent fever and sore throat"
    )
    db.add(appt)
    db.commit()
    appt_id = appt.id

    token_doc1 = create_access_token({"sub": str(doc_user1.id), "role": "DOCTOR"})
    token_doc2 = create_access_token({"sub": str(doc_user2.id), "role": "DOCTOR"})

    # Doctor 2 trying to access Doctor 1's appointment -> 403
    forbidden_resp = client.get(f"/api/doctor/appointments/{appt_id}", headers={"Authorization": f"Bearer {token_doc2}"})
    assert forbidden_resp.status_code == 403

    # Doctor 1 accessing own appointment -> 200
    doc1_resp = client.get(f"/api/doctor/appointments/{appt_id}", headers={"Authorization": f"Bearer {token_doc1}"})
    assert doc1_resp.status_code == 200
    assert doc1_resp.json()["symptoms"] == "Persistent fever and sore throat"

    # Doctor 1 completes consultation
    complete_resp = client.post(
        f"/api/doctor/appointments/{appt_id}/complete",
        json={
            "notes": "Throat infection observed. Prescribed antibiotics.",
            "prescriptions": [
                {
                    "medicine_name": "Azithromycin",
                    "dosage": "250mg",
                    "frequency": "Once daily",
                    "duration": "5 days",
                    "instructions": "Take before breakfast"
                }
            ]
        },
        headers={"Authorization": f"Bearer {token_doc1}"}
    )
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["status"] == "COMPLETED"
    assert data["post_visit_notes"] == "Throat infection observed. Prescribed antibiotics."
    assert data["post_visit_summary"] is not None
    assert len(data["prescriptions"]) == 1
    assert data["prescriptions"][0]["medicine_name"] == "Azithromycin"
    db.close()
