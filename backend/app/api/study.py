from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudySession, User
from app.schemas import HeartbeatRequest, StudyDay
from app.security import get_current_user
from app.services import badge_service

router = APIRouter(prefix="/api/study", tags=["study"])


@router.post("/heartbeat", response_model=StudyDay)
def heartbeat(
    payload: HeartbeatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    session = (
        db.query(StudySession)
        .filter(StudySession.user_id == user.id, StudySession.day == today)
        .one_or_none()
    )
    if session is None:
        session = StudySession(user_id=user.id, day=today, seconds=0)
        db.add(session)
    session.seconds += payload.seconds
    db.commit()
    new_badges = badge_service.check_study_badges(db, user)
    return StudyDay(day=session.day, seconds=session.seconds, new_badges=new_badges)


@router.get("/today", response_model=StudyDay)
def today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = date.today()
    session = (
        db.query(StudySession)
        .filter(StudySession.user_id == user.id, StudySession.day == d)
        .one_or_none()
    )
    return StudyDay(day=d, seconds=session.seconds if session else 0)


@router.get("/history", response_model=list[StudyDay])
def history(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=max(1, min(days, 365)) - 1)
    sessions = (
        db.query(StudySession)
        .filter(StudySession.user_id == user.id, StudySession.day >= since)
        .order_by(StudySession.day)
        .all()
    )
    return [StudyDay(day=s.day, seconds=s.seconds) for s in sessions]
