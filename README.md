# Healthcare Appointment & Follow-Up Manager

An end-to-end healthcare platform for patient appointment booking, AI-powered
pre-visit assessment, doctor consultations, prescriptions, follow-up management,
doctor schedule and leave management, asynchronous notifications, and Google
Calendar synchronization.

---

## 1. Overview & Stack

- **Frontend:** React + Vite, React Router, Axios, CSS
- **Backend:** FastAPI, Python, SQLAlchemy, Pydantic
- **Database:** PostgreSQL hosted on Supabase
- **Authentication:** JWT + Role-Based Access Control
  (`PATIENT`, `DOCTOR`, `ADMIN`)
- **Background Jobs:** Celery + Upstash Redis
- **AI:** Groq API
- **Email:** Resend API
- **Calendar:** Google Calendar OAuth 2.0 API

---

## 2. Features

### Patient

- Search doctors by specialization
- View doctor availability
- Select appointment date and time slot
- Book appointments with 5-minute hold protection
- Enter symptoms/reason for visit
- View AI-generated pre-visit assessment
- Cancel appointments
- View appointment history
- Respond to upcoming appointments
- Select attendance method
- Provide post-visit follow-up status
- Edit profile
- Deactivate account
- Emergency assistance information

### Doctor

- View upcoming appointments
- View patient symptoms
- View AI pre-visit assessment
- Conduct consultation
- Record clinical notes/diagnosis
- Prescribe medications
- Complete consultation
- Generate AI patient-friendly post-visit summary

### Admin

- Manage doctors
- Configure specialization
- Configure consultation slot duration
- Configure working hours
- Record doctor leave
- Automatically resolve conflicting appointments
- Generate patient notifications for affected appointments

### Background Processing

- Asynchronous notification emails
- Appointment reminders
- Medication reminders
- Expired appointment-hold cleanup
- Email retry mechanism

---

## 3. Architecture

```text
React + Vite
      |
      | REST API + JWT
      v
FastAPI Backend
      |
      +----> Supabase PostgreSQL
      |
      +----> Groq API
      |
      +----> Google Calendar API
      |
      +----> Upstash Redis
                    |
                    v
              Celery Worker
                    |
                    v
                Resend API
