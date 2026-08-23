from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.init_db import init_db
from app.routes.auth import router as auth_router
from app.routes.doctors import router as doctors_router
from app.routes.admin import router as admin_router
from app.routes.appointments import router as appointments_router
from app.routes.doctor_workflow import router as doctor_workflow_router
from app.routes.calendar import router as calendar_router

app = FastAPI(title="Healthcare Appointment & Follow-Up Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(admin_router)
app.include_router(appointments_router)
app.include_router(doctor_workflow_router)
app.include_router(calendar_router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Healthcare Appointment Manager"}
