import logging
from datetime import datetime, timedelta
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Notification, User, Appointment, Prescription, AppointmentStatus
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email_task(self, notification_id: int):
    db = SessionLocal()
    try:
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notif:
            logger.error(f"Notification #{notification_id} not found")
            return

        user = db.query(User).filter(User.id == notif.user_id).first()
        if not user:
            logger.error(f"User #{notif.user_id} not found for notification")
            return

        notif.status = "SENDING"
        db.commit()

        # Build email content based on notification type
        subject = f"Notification: {notif.type.replace('_', ' ').title()}"
        body = f"Hello {user.name},\n\nThis is a notification regarding your healthcare appointment."

        if notif.appointment_id:
            appt = db.query(Appointment).filter(Appointment.id == notif.appointment_id).first()
            if appt:
                if notif.type == "BOOKING_CONFIRMATION":
                    subject = f"Booking Confirmation: Appointment #{appt.id}"
                    body = (
                        f"Dear {user.name},\n\nYour appointment is confirmed for {appt.appointment_date} "
                        f"at {appt.start_time.strftime('%H:%M')}.\n\nThank you for choosing HospitalCare."
                    )
                elif notif.type == "APPOINTMENT_REMINDER":
                    subject = f"Upcoming Appointment Reminder: #{appt.id}"
                    body = (
                        f"Dear {user.name},\n\nReminder: You have an upcoming appointment tomorrow on {appt.appointment_date} "
                        f"at {appt.start_time.strftime('%H:%M')}."
                    )
                elif notif.type == "CANCELLATION":
                    subject = f"Appointment Cancelled: #{appt.id}"
                    body = f"Dear {user.name},\n\nYour appointment on {appt.appointment_date} has been cancelled."
                elif notif.type == "DOCTOR_LEAVE_CANCELLATION":
                    subject = f"Appointment Reschedule Needed: #{appt.id}"
                    body = f"Dear {user.name},\n\nYour doctor is unavailable on {appt.appointment_date}. Please reschedule your visit."
                elif notif.type == "MEDICATION_REMINDER":
                    subject = f"Medication Reminder - Post Consultation"
                    body = f"Dear {user.name},\n\nPlease remember to follow your prescribed medication schedule.\n\nSummary:\n{appt.post_visit_summary or ''}"

        # Send email
        send_email(to_email=user.email, subject=subject, body=body)

        # Mark SENT
        notif.status = "SENT"
        notif.sent_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        db.rollback()
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        if notif:
            notif.retry_count += 1
            notif.error_message = str(exc)
            if notif.retry_count >= 3:
                notif.status = "FAILED"
            else:
                notif.status = "PENDING"
            db.commit()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
    finally:
        db.close()

@celery_app.task
def cleanup_expired_holds_task():
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        expired = db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.HELD,
            Appointment.created_at < cutoff
        ).all()
        for appt in expired:
            appt.status = AppointmentStatus.CANCELLED
        db.commit()
        logger.info(f"Cleaned up {len(expired)} expired holds.")
        return len(expired)
    finally:
        db.close()

@celery_app.task
def send_appointment_reminders_task():
    db = SessionLocal()
    try:
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        upcoming_appts = db.query(Appointment).filter(
            Appointment.appointment_date == tomorrow,
            Appointment.status == AppointmentStatus.BOOKED
        ).all()

        count = 0
        for appt in upcoming_appts:
            existing = db.query(Notification).filter(
                Notification.appointment_id == appt.id,
                Notification.type == "APPOINTMENT_REMINDER"
            ).first()
            if not existing:
                notif = Notification(
                    user_id=appt.patient_id,
                    appointment_id=appt.id,
                    type="APPOINTMENT_REMINDER",
                    status="PENDING",
                    scheduled_at=datetime.utcnow()
                )
                db.add(notif)
                db.commit()
                db.refresh(notif)
                send_notification_email_task.delay(notif.id)
                count += 1
        return count
    finally:
        db.close()

@celery_app.task
def send_medication_reminders_task():
    db = SessionLocal()
    try:
        recent_completed = db.query(Appointment).filter(
            Appointment.status == AppointmentStatus.COMPLETED
        ).all()

        count = 0
        for appt in recent_completed:
            existing = db.query(Notification).filter(
                Notification.appointment_id == appt.id,
                Notification.type == "MEDICATION_REMINDER"
            ).first()
            if not existing and appt.prescriptions:
                notif = Notification(
                    user_id=appt.patient_id,
                    appointment_id=appt.id,
                    type="MEDICATION_REMINDER",
                    status="PENDING",
                    scheduled_at=datetime.utcnow()
                )
                db.add(notif)
                db.commit()
                db.refresh(notif)
                send_notification_email_task.delay(notif.id)
                count += 1
        return count
    finally:
        db.close()
