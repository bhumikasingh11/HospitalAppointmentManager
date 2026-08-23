# Healthcare Appointment & Follow-Up Manager

An end-to-end healthcare platform for **patient appointment booking, AI-powered clinical assistance, doctor consultations, prescriptions, follow-up management, notifications, and Google Calendar integration**.

## Tech Stack

* **Frontend:** React + Vite, React Router, Axios
* **Backend:** FastAPI, SQLAlchemy, Pydantic
* **Database:** PostgreSQL (Supabase)
* **Authentication:** JWT + Role-Based Access Control
* **Background Jobs:** Celery + Upstash Redis
* **AI:** Groq API
* **Email:** Resend API
* **Calendar:** Google Calendar OAuth 2.0

## Main Features

### Patient

* Search doctors and view availability
* Book, cancel, and reschedule appointments
* Temporary slot hold protection
* Submit symptoms before consultation
* AI pre-visit assessment
* View consultation and prescription history
* Respond to appointments
* Provide follow-up status
* Edit/deactivate profile
* Emergency assistance option

### Doctor

* View consultation queue
* Review patient symptoms and AI pre-visit analysis
* Record clinical notes and diagnosis
* Prescribe medications
* Complete consultations
* Generate AI-powered patient-friendly summaries

### Admin

* Add and manage doctors
* Configure specialization and slot duration
* Configure working hours
* Record doctor leave
* Automatically handle conflicting appointments
* Trigger patient notifications for affected appointments

### Background Processing

* Asynchronous notification emails
* Appointment reminders
* Medication reminders
* Expired appointment-hold cleanup
* Email retry handling

## Architecture

```text
React Frontend
      ↓
FastAPI Backend
      ↓
Supabase PostgreSQL
      │
      ├── Groq AI
      ├── Google Calendar
      │
      └── Upstash Redis
              ↓
         Celery Worker
              ↓
          Resend Email
```

## Project Structure

```text
HospitalAppointmentManager/
├── backend/
├── frontend/
├── screenshots/
├── README.md
├── SYSTEM_DESIGN.md
└── .gitignore
```

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create `.env` in the **project root**:

```env
DATABASE_URL=<SUPABASE_POSTGRESQL_URL>
SECRET_KEY=<YOUR_SECRET>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

REDIS_URL=<UPSTASH_REDIS_URL>

GROQ_API_KEY=<YOUR_GROQ_API_KEY>
GROQ_MODEL=openai/gpt-oss-20b

EMAIL_API_KEY=<YOUR_RESEND_API_KEY>
EMAIL_FROM=<YOUR_EMAIL_SENDER>

GOOGLE_CLIENT_ID=<YOUR_GOOGLE_CLIENT_ID>
GOOGLE_CLIENT_SECRET=<YOUR_GOOGLE_CLIENT_SECRET>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/callback
```

**Do not commit `.env` or any API keys.**

### Initialize Database

```bash
python -m app.init_db
```

### Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

### Start Celery Worker

In another terminal:

```bash
cd backend
venv\Scripts\activate
celery -A app.celery_app.celery_app worker --loglevel=info --pool=solo
```

### Start Frontend

```bash
cd frontend
npm install
npm run dev
```

## AI Workflow

### Pre-Visit

Patient symptoms → Groq AI → urgency + complaint summary + suggested doctor questions.

### Post-Visit

Doctor notes + prescriptions → Groq AI → patient-friendly summary + medication schedule + follow-up guidance.

## Important Design Features

* JWT authentication with role-based access
* Database-level appointment conflict protection
* Temporary appointment holds
* Doctor leave conflict handling
* Asynchronous background processing with Celery
* Retry mechanism for failed email notifications
* Soft account deactivation while preserving historical records

## Screenshots

Screenshots demonstrating the application are available in the [`screenshots`](screenshots/) folder.

## Testing

Run backend tests with:

```bash
cd backend
pytest tests/
```

## Submission

Public GitHub repository:

**https://github.com/bhumikasingh11/HospitalAppointmentManager**

> The repository intentionally excludes `.env`, database files, virtual environments, `node_modules`, and build artifacts.
