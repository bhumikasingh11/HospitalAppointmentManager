from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.services.calendar_service import get_google_oauth_url, exchange_oauth_code

router = APIRouter(prefix="/api/calendar", tags=["Google Calendar"])

@router.get("/connect")
def connect_google_calendar(current_user: User = Depends(get_current_user)):
    url = get_google_oauth_url(user_id=current_user.id)
    return {"authorization_url": url}

@router.get("/callback")
def google_calendar_callback(code: str = Query(...), state: str = Query(...)):
    try:
        user_id = int(state)
        token_info = exchange_oauth_code(code=code, user_id=user_id)
        return {
            "status": "connected",
            "message": "Google Calendar successfully connected",
            "token": token_info.get("token_type")
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to connect Google Calendar: {e}")
