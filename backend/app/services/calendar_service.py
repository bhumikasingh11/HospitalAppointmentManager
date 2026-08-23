import logging
import urllib.parse
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from app.config import settings
from app.models import CalendarEvent, Appointment, User

logger = logging.getLogger(__name__)

# Temporary in-memory token store for demo/simulated OAuth (or extendable to user OAuth table)
USER_CALENDAR_TOKENS = {}

def get_google_oauth_url(user_id: int) -> str:
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID or "mock-client-id",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id)
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def exchange_oauth_code(code: str, user_id: int) -> dict:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        token_info = {"access_token": f"mock-access-token-{user_id}", "token_type": "Bearer"}
        USER_CALENDAR_TOKENS[user_id] = token_info
        return token_info

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    with httpx.Client(timeout=10.0) as client:
        response = client.post(token_url, data=data)
        response.raise_for_status()
        token_info = response.json()
        USER_CALENDAR_TOKENS[user_id] = token_info
        return token_info

def create_calendar_event(db: Session, appointment: Appointment) -> str:
    try:
        user_id = appointment.patient_id
        event_summary = f"Doctor Consultation - Dr. #{appointment.doctor_id}"
        start_iso = f"{appointment.appointment_date}T{appointment.start_time}Z"
        end_iso = f"{appointment.appointment_date}T{appointment.end_time}Z"

        token_data = USER_CALENDAR_TOKENS.get(user_id)
        
        # If real Google API call is configured
        if settings.GOOGLE_CLIENT_ID and token_data and "access_token" in token_data:
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            payload = {
                "summary": event_summary,
                "description": f"Symptoms: {appointment.symptoms or 'N/A'}",
                "start": {"dateTime": start_iso},
                "end": {"dateTime": end_iso}
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post("https://www.googleapis.com/calendar/v3/calendars/primary/events", headers=headers, json=payload)
                res.raise_for_status()
                google_event_id = res.json().get("id", f"g_event_{appointment.id}")
        else:
            google_event_id = f"g_event_{appointment.id}_{int(datetime.utcnow().timestamp())}"

        # Store Google event ID in DB
        cal_event = CalendarEvent(
            appointment_id=appointment.id,
            user_id=user_id,
            google_event_id=google_event_id
        )
        db.add(cal_event)
        db.commit()
        return google_event_id

    except Exception as e:
        logger.warning(f"Google Calendar event creation failed (safe fallback): {e}")
        return ""

def update_calendar_event(db: Session, appointment: Appointment) -> bool:
    try:
        cal_event = db.query(CalendarEvent).filter(CalendarEvent.appointment_id == appointment.id).first()
        if not cal_event:
            return False

        user_id = appointment.patient_id
        token_data = USER_CALENDAR_TOKENS.get(user_id)

        if settings.GOOGLE_CLIENT_ID and token_data and "access_token" in token_data:
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            payload = {
                "start": {"dateTime": f"{appointment.appointment_date}T{appointment.start_time}Z"},
                "end": {"dateTime": f"{appointment.appointment_date}T{appointment.end_time}Z"}
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.patch(f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{cal_event.google_event_id}", headers=headers, json=payload)
                res.raise_for_status()

        return True
    except Exception as e:
        logger.warning(f"Google Calendar event update failed (safe fallback): {e}")
        return False

def delete_calendar_event(db: Session, appointment_id: int) -> bool:
    try:
        cal_event = db.query(CalendarEvent).filter(CalendarEvent.appointment_id == appointment_id).first()
        if not cal_event:
            return False

        user_id = cal_event.user_id
        token_data = USER_CALENDAR_TOKENS.get(user_id)

        if settings.GOOGLE_CLIENT_ID and token_data and "access_token" in token_data:
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            with httpx.Client(timeout=10.0) as client:
                client.delete(f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{cal_event.google_event_id}", headers=headers)

        db.delete(cal_event)
        db.commit()
        return True
    except Exception as e:
        logger.warning(f"Google Calendar event deletion failed (safe fallback): {e}")
        return False
