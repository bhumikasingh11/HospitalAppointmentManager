# System Design Document

## 1. Double-Booking Prevention & Concurrency Protection
The database serves as the single source of truth for appointment concurrency. To guarantee that simultaneous requests for the same doctor, date, and start time never both succeed:
1. A database-level unique constraint is enforced: `UniqueConstraint('doctor_id', 'appointment_date', 'start_time', name='uq_doctor_date_slot')`.
2. The booking transaction executes slot validation and inserts the slot atomically.
3. If two concurrent transactions attempt to book the identical slot, the database constraint triggers a uniqueness violation (`IntegrityError`). The booking service intercepts this and returns a clean `HTTP 409 Conflict` with the message: *"Slot was just booked. Please select another."*

## 2. Slot Hold Mechanism
To prevent race conditions during patient symptom intake and confirmation:
- Slots temporarily transition into a `HELD` status before confirmation (`BOOKED`).
- A 5-minute threshold is enforced: when querying slot availability or processing bookings, any `HELD` slot older than 5 minutes is treated as expired and automatically marked `CANCELLED`.
- A background Celery task (`cleanup_expired_holds_task`) runs periodically to sweep and cancel unconfirmed holds, immediately releasing them back into the pool of available slots.

## 3. Doctor Leave Conflicts
When an administrator records a doctor's leave for a specific date:
1. The leave record (`DoctorLeave`) is persisted.
2. In the same atomic database transaction, all active appointments (`BOOKED` or `HELD`) for that doctor on that date are queried.
3. Affected appointments are updated to `CANCELLED` status (retaining full audit and clinical history).
4. `DOCTOR_LEAVE_CANCELLATION` notification records are created in the database for each affected patient.
5. Google Calendar events associated with the cancelled appointments are deleted.
6. The slot generation service immediately excludes the leave date from future queries, preventing any new bookings.

## 4. Notification Failure & Retry Architecture
The notification system is decoupled from core API request-response lifecycles:
- Booking and consultation endpoints persist notification records in `PENDING` status and enqueue asynchronous Celery tasks (`send_notification_email_task`).
- The Celery worker picks up the task and updates status to `SENDING`.
- If the email provider API fails or times out:
  - The worker catches the error, increments `retry_count`, logs `error_message`, and triggers Celery's exponential retry mechanism (`max_retries=3`).
  - If all 3 attempts fail, status is set to `FAILED`.
- Core appointments remain 100% valid regardless of email delivery success or failure.

## 5. LLM Failure Handling & Resilience
Groq LLM calls (`generate_pre_visit_summary` and `generate_post_visit_summary`) are isolated behind the `llm_service.py` module:
- All external API calls use explicit HTTP client timeouts (10 seconds) and structured JSON parsing.
- If the LLM provider experiences outages, invalid tokens, rate limits, or malformed outputs:
  - The exception is caught and logged.
  - Safe, deterministic fallback summaries (e.g., standard triage questions and clinical notes summaries) are returned instantly.
  - Core appointment booking, doctor notes submission, and consultation completion proceed without interruption.
