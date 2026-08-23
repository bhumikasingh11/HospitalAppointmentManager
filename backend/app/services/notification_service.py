import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Notification, User, Appointment

logger = logging.getLogger(__name__)

def create_and_dispatch_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    appointment_id: int = None,
    scheduled_at: datetime = None
) -> Notification:
    if scheduled_at is None:
        scheduled_at = datetime.utcnow()

    notif = Notification(
        user_id=user_id,
        appointment_id=appointment_id,
        type=notification_type,
        status="PENDING",
        retry_count=0,
        scheduled_at=scheduled_at
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Trigger Celery background task if available
    try:
        from app.tasks import send_notification_email_task
        send_notification_email_task.delay(notif.id)
    except Exception as e:
        logger.warning(f"Could not queue notification to Celery broker: {e}")

    return notif
