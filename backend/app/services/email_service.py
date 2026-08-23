import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using configured email provider API (e.g. Resend / SendGrid / Mailgun).
    If no API key is set, logs the email and succeeds cleanly for development/testing.
    """
    if not settings.EMAIL_API_KEY:
        logger.info(f"[EMAIL SIMULATION] To: {to_email} | Subject: {subject}\nBody:\n{body}")
        return True

    try:
        # Example using HTTP provider API (e.g. Resend / SendGrid)
        headers = {
            "Authorization": f"Bearer {settings.EMAIL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": f"<div style='font-family: sans-serif;'>{body.replace(chr(10), '<br/>')}</div>"
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post("https://api.resend.com/emails", headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Email successfully sent to {to_email}")
            return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise e
