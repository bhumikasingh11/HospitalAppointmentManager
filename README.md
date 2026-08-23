# Healthcare Appointment & Follow-Up Manager

An end-to-end healthcare platform for patient booking, AI clinical summaries, doctor consultations, prescriptions, schedule & leave management, background notifications, and Google Calendar sync.

---

## 1. Overview & Stack

- **Frontend**: React + Vite, React Router, Axios, Pure CSS.
- **Backend**: FastAPI (Python 3.10+), SQLAlchemy ORM, Pydantic.
- **Database**: PostgreSQL (Supabase / Local) with SQLite fallback.
- **Authentication**: JWT & Role-Based Access Control (PATIENT, DOCTOR, ADMIN).
- **Asynchronous Tasks**: Redis + Celery.
- **AI Integration**: Groq API (models: `gemma2-9b-it`, `llama-3.2-3b-preview`, `mixtral-8x7b-32768`).
- **Email Service**: Resend / SendGrid / Provider API with simulation fallback.
- **Calendar**: Google Calendar OAuth 2.0 API.

---

## 2. Features

- **Patient Workflow**: Search specialists, pick dates & slot intervals, enter symptoms, book with 5-minute hold protection, view pre-visit AI insights, manage & cancel appointments.
- **Doctor Workflow**: View daily consultation queue, inspect patient symptoms & pre-visit AI analysis, log clinical diagnosis notes, add prescriptions, and generate patient-friendly post-visit summaries.
- **Admin Workflow**: Register doctors, configure working hours & slot durations, record doctor leaves with automated cancellation of conflicting bookings and patient notifications.
- **Background Jobs**: Expired hold cleanup, appointment reminders, medication reminders, and 3x email retry mechanism.
- **Concurrency & Concurrency Protection**: Database-level unique constraints (`uq_doctor_date_slot`), atomic transactions, and conflict detection (HTTP 409).

---

## 3. Architecture

```
[ Frontend (React + Vite) ]
           | (REST API + JWT)
[ FastAPI Backend ]
    |---> [ PostgreSQL / SQLite DB ] (Source of Truth)
    |---> [ Groq LLM API ] (Pre-visit & Post-visit Summaries)
    |---> [ Google Calendar API ] (OAuth 2.0 Sync)
    |---> [ Redis Message Broker ] ---> [ Celery Worker / Beat ] ---> [ Email Provider ]
```

---

## 4. Setup & Running from Command Line

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate virtual environment
python -m venv venv
# On Windows (cmd/powershell):
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure .env
cp ../.env.example .env

# 5. Run FastAPI backend server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

### Celery Background Worker

```bash
# From backend directory with venv activated:
celery -A app.celery_app.celery_app worker --loglevel=info
```

### Running Automated Tests

```bash
# From backend directory:
pytest tests/
```

---

## 5. Environment Variables (`.env`)

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/hospital_db
SECRET_KEY=your-super-secret-jwt-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=gemma2-9b-it
EMAIL_API_KEY=your-email-api-key
EMAIL_FROM=noreply@hospital.com
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/callback
```

---

## 6. Database Schema

- `users`: `id`, `name`, `email`, `password_hash`, `role` (`PATIENT`, `DOCTOR`, `ADMIN`), `created_at`
- `doctors`: `id`, `user_id`, `specialization`, `slot_duration`
- `working_hours`: `id`, `doctor_id`, `day_of_week`, `start_time`, `end_time`
- `doctor_leaves`: `id`, `doctor_id`, `leave_date`, `reason`
- `appointments`: `id`, `patient_id`, `doctor_id`, `appointment_date`, `start_time`, `end_time`, `status` (`HELD`, `BOOKED`, `CANCELLED`, `COMPLETED`), `symptoms`, `pre_visit_summary`, `urgency`, `post_visit_notes`, `post_visit_summary`, `created_at`
- `prescriptions`: `id`, `appointment_id`, `medicine_name`, `dosage`, `frequency`, `duration`, `instructions`
- `notifications`: `id`, `user_id`, `appointment_id`, `type`, `status`, `retry_count`, `scheduled_at`, `sent_at`, `error_message`
- `calendar_events`: `id`, `appointment_id`, `user_id`, `google_event_id`

---

## 7. Key REST API Endpoints

- **Auth**: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- **Doctors**: `GET /api/doctors`, `GET /api/doctors/{id}`, `GET /api/doctors/{id}/slots`
- **Appointments**: `POST /api/appointments`, `GET /api/appointments/my`, `GET /api/appointments/{id}`, `POST /api/appointments/{id}/cancel`, `POST /api/appointments/{id}/reschedule`
- **Doctor Workflow**: `GET /api/doctor/appointments`, `GET /api/doctor/appointments/{id}`, `POST /api/doctor/appointments/{id}/complete`
- **Admin**: `GET /api/admin/doctors`, `POST /api/admin/doctors`, `PUT /api/admin/doctors/{id}`, `POST /api/admin/doctors/{id}/working-hours`, `POST /api/admin/doctors/{id}/leaves`
- **Calendar**: `GET /api/calendar/connect`, `GET /api/calendar/callback`

---

## 8. LLM Prompts & Failure Resilience

- **Pre-Visit Prompt**: Directs clinical analysis of symptoms into JSON with urgency (`Low`/`Medium`/`High`), concise chief complaint, and 3 suggested diagnostic questions.
- **Post-Visit Prompt**: Transforms doctor's clinical notes and prescription tables into an empathetic patient-friendly summary, medication schedule, and follow-up guidance.
- **Resilience**: Groq calls are isolated in `llm_service.py` with structured JSON parsing, strict timeouts, and fallback defaults so core booking and consultation completion never fail.

---

## 9. Google Calendar Setup

1. Create a project in Google Cloud Console and enable the **Google Calendar API**.
2. Configure OAuth 2.0 Client ID with Authorized Redirect URI: `http://localhost:8000/api/calendar/callback`.
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
4. Users authorize via `/api/calendar/connect`; booking and rescheduling synchronize events automatically.

---

## 10. Deployment & Limitations

- **Deployment**: Backend deployable on Render / Fly.io / AWS ECS; Frontend on Vercel / Netlify; Database on Supabase PostgreSQL; Redis on Upstash / Redis Cloud.
- **Limitations**: In-memory token caching for OAuth in local development mode; Celery tasks require running Redis instance in production.
