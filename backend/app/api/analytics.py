from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import AnalyticsSummary
from app.security import get_current_user
from app.services.analytics_service import build_summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_summary(db, user.id)
