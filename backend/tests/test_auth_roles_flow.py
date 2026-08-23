import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Doctor, RoleEnum
from app.seed import seed_admin

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

def test_full_auth_roles_workflow():
    db = TestingSessionLocal()

    # 1. /register creates PATIENT only
    p_res = client.post("/api/auth/register", json={
        "name": "Jane Patient",
        "email": "jane@hospital.com",
        "password": "patientpassword",
        "role": "ADMIN"  # attempt privilege escalation
    })
    assert p_res.status_code == 201
    assert p_res.json()["role"] == "PATIENT"

    # 2. Seed initial Admin account
    admin_account = seed_admin(name="Super Admin", email="admin@hospital.com", password="admin123")
    assert admin_account.role == RoleEnum.ADMIN

    # 3. Admin logs in using standard /login
    admin_login = client.post("/api/auth/login", json={
        "email": "admin@hospital.com",
        "password": "admin123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    assert admin_login.json()["role"] == "ADMIN"

    # 4. Admin creates DOCTOR account and profile
    create_doc_res = client.post("/api/admin/doctors", json={
        "name": "Dr. Gregory House",
        "email": "house@hospital.com",
        "password": "docpassword123",
        "specialization": "Diagnostic Medicine",
        "slot_duration": 30
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert create_doc_res.status_code == 201
    doc_id = create_doc_res.json()["id"]

    # 5. Doctor logs in using standard /login
    doc_login = client.post("/api/auth/login", json={
        "email": "house@hospital.com",
        "password": "docpassword123"
    })
    assert doc_login.status_code == 200
    assert doc_login.json()["role"] == "DOCTOR"

    # 6. /doctors displays doctors created by admin
    docs_res = client.get("/api/doctors")
    assert docs_res.status_code == 200
    docs = docs_res.json()
    assert len(docs) == 1
    assert docs[0]["specialization"] == "Diagnostic Medicine"
    assert docs[0]["user"]["name"] == "Dr. Gregory House"

    db.close()
