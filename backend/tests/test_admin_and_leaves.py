import pytest
from datetime import date, time, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, WorkingHour, DoctorLeave, Appointment, Notification, RoleEnum, AppointmentStatus
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

def test_admin_leave_conflict_resolution():
    db = TestingSessionLocal()
    # 1. Setup Admin, Doctor, and 2 Patients
    admin_user = User(name="Admin", email="admin@hospital.com", password_hash=hash_password("pw"), role=RoleEnum.ADMIN)
    doc_user = User(name="Dr. Gregory", email="gregory@hospital.com", password_hash=hash_password("pw"), role=RoleEnum.DOCTOR)
    patient1 = User(name="Patient 1", email="p1@hospital.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    patient2 = User(name="Patient 2", email="p2@hospital.com", password_hash=hash_password("pw"), role=RoleEnum.PATIENT)
    db.add_all([admin_user, doc_user, patient1, patient2])
    db.commit()

    doctor = Doctor(user_id=doc_user.id, specialization="Cardiology", slot_duration=30)
    db.add(doctor)
    db.commit()

    # 2. Book 2 appointments on target date
    leave_date = date.today() + timedelta(days=3)
    appt1 = Appointment(
        patient_id=patient1.id,
        doctor_id=doctor.id,
        appointment_date=leave_date,
        start_time=time(9, 0),
        end_time=time(9, 30),
        status=AppointmentStatus.BOOKED
    )
    appt2 = Appointment(
        patient_id=patient2.id,
        doctor_id=doctor.id,
        appointment_date=leave_date,
        start_time=time(9, 30),
        end_time=time(10, 0),
        status=AppointmentStatus.BOOKED
    )
    db.add_all([appt1, appt2])
    db.commit()
    appt1_id = appt1.id
    appt2_id = appt2.id

    admin_token = create_access_token({"sub": str(admin_user.id), "role": "ADMIN"})
    patient_token = create_access_token({"sub": str(patient1.id), "role": "PATIENT"})

    # Non-admin cannot set leave
    forbidden_resp = client.post(
        f"/api/admin/doctors/{doctor.id}/leaves",
        json={"leave_date": str(leave_date), "reason": "Emergency Leave"},
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert forbidden_resp.status_code == 403

    # Admin sets leave on target date
    leave_resp = client.post(
        f"/api/admin/doctors/{doctor.id}/leaves",
        json={"leave_date": str(leave_date), "reason": "Medical Conference"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert leave_resp.status_code == 201

    # Verify both appointments are now CANCELLED in DB
    refreshed_appt1 = db.query(Appointment).filter(Appointment.id == appt1_id).first()
    refreshed_appt2 = db.query(Appointment).filter(Appointment.id == appt2_id).first()
    assert refreshed_appt1.status == AppointmentStatus.CANCELLED
    assert refreshed_appt2.status == AppointmentStatus.CANCELLED

    # Verify notifications were queued for affected patients
    notifs = db.query(Notification).filter(Notification.type == "DOCTOR_LEAVE_CANCELLATION").all()
    assert len(notifs) == 2
    patient_ids = {n.user_id for n in notifs}
    assert patient1.id in patient_ids
    assert patient2.id in patient_ids
    db.close()
