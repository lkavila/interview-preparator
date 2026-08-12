from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import BadgeOut
from app.security import get_current_user
from app.services import badge_service

router = APIRouter(prefix="/api/badges", tags=["badges"])


@router.get("", response_model=list[BadgeOut])
def list_badges(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return badge_service.user_badges(db, user)
