"""Badge/achievement system. Badges are awarded server-side from verifiable events
and stored in the user_badges table."""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ExerciseAttempt, StudySession, TestAttempt, User, UserBadge, UserLessonProgress

CATALOG: list[dict] = [
    {
        "key": "first_lesson",
        "icon": "🎯",
        "name": {"en": "First step", "es": "Primer paso"},
        "description": {"en": "Complete your first lesson.", "es": "Completa tu primera lección."},
    },
    {
        "key": "lessons_10",
        "icon": "📚",
        "name": {"en": "Getting serious", "es": "En serio"},
        "description": {"en": "Complete 10 lessons.", "es": "Completa 10 lecciones."},
    },
    {
        "key": "lessons_50",
        "icon": "🏛️",
        "name": {"en": "Scholar", "es": "Erudito"},
        "description": {"en": "Complete 50 lessons.", "es": "Completa 50 lecciones."},
    },
    {
        "key": "attempts_50",
        "icon": "💪",
        "name": {"en": "Practice machine", "es": "Máquina de práctica"},
        "description": {"en": "Submit 50 exercise attempts.", "es": "Envía 50 intentos de ejercicios."},
    },
    {
        "key": "correct_25",
        "icon": "✅",
        "name": {"en": "Sharp shooter", "es": "Puntería fina"},
        "description": {"en": "Get 25 exercises right.", "es": "Acierta 25 ejercicios."},
    },
    {
        "key": "first_test",
        "icon": "📝",
        "name": {"en": "Test taker", "es": "Examinado"},
        "description": {"en": "Finish your first course test.", "es": "Termina tu primer test de curso."},
    },
    {
        "key": "test_80",
        "icon": "🌟",
        "name": {"en": "Interview ready", "es": "Listo para la entrevista"},
        "description": {"en": "Score 80% or more on a course test.", "es": "Obtén 80% o más en un test."},
    },
    {
        "key": "test_100",
        "icon": "🏆",
        "name": {"en": "Perfect score", "es": "Puntaje perfecto"},
        "description": {"en": "Score 100% on a course test.", "es": "Obtén 100% en un test."},
    },
    {
        "key": "streak_3",
        "icon": "🔥",
        "name": {"en": "On a roll", "es": "En racha"},
        "description": {"en": "Study 3 days in a row.", "es": "Estudia 3 días seguidos."},
    },
    {
        "key": "streak_7",
        "icon": "⚡",
        "name": {"en": "Unstoppable", "es": "Imparable"},
        "description": {"en": "Study 7 days in a row.", "es": "Estudia 7 días seguidos."},
    },
]

CATALOG_BY_KEY = {b["key"]: b for b in CATALOG}


def _earned_keys(db: Session, user_id: int) -> set[str]:
    rows = db.query(UserBadge.badge_key).filter(UserBadge.user_id == user_id).all()
    return {r[0] for r in rows}


def _award(db: Session, user_id: int, keys: list[str]) -> list[str]:
    """Insert badges the user doesn't have yet. Returns the newly awarded keys."""
    if not keys:
        return []
    earned = _earned_keys(db, user_id)
    new = [k for k in keys if k not in earned and k in CATALOG_BY_KEY]
    for key in new:
        db.add(UserBadge(user_id=user_id, badge_key=key))
    if new:
        db.commit()
    return new


def _study_streak(db: Session, user_id: int) -> int:
    days = {
        r[0]
        for r in db.query(StudySession.day)
        .filter(StudySession.user_id == user_id, StudySession.seconds > 0)
        .all()
    }
    streak = 0
    d = date.today()
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


def check_lesson_badges(db: Session, user: User) -> list[str]:
    completed = (
        db.query(func.count(UserLessonProgress.id))
        .filter(UserLessonProgress.user_id == user.id)
        .scalar()
        or 0
    )
    keys = []
    if completed >= 1:
        keys.append("first_lesson")
    if completed >= 10:
        keys.append("lessons_10")
    if completed >= 50:
        keys.append("lessons_50")
    return _award(db, user.id, keys)


def check_attempt_badges(db: Session, user: User) -> list[str]:
    total = (
        db.query(func.count(ExerciseAttempt.id))
        .filter(ExerciseAttempt.user_id == user.id)
        .scalar()
        or 0
    )
    correct = (
        db.query(func.count(ExerciseAttempt.id))
        .filter(ExerciseAttempt.user_id == user.id, ExerciseAttempt.is_correct.is_(True))
        .scalar()
        or 0
    )
    keys = []
    if total >= 50:
        keys.append("attempts_50")
    if correct >= 25:
        keys.append("correct_25")
    return _award(db, user.id, keys)


def check_test_badges(db: Session, user: User, score: float) -> list[str]:
    keys = ["first_test"]
    if score >= 80:
        keys.append("test_80")
    if score >= 100:
        keys.append("test_100")
    return _award(db, user.id, keys)


def check_study_badges(db: Session, user: User) -> list[str]:
    streak = _study_streak(db, user.id)
    keys = []
    if streak >= 3:
        keys.append("streak_3")
    if streak >= 7:
        keys.append("streak_7")
    return _award(db, user.id, keys)


def user_badges(db: Session, user: User) -> list[dict]:
    earned = {
        b.badge_key: b.earned_at
        for b in db.query(UserBadge).filter(UserBadge.user_id == user.id).all()
    }
    return [
        {
            **badge,
            "earned": badge["key"] in earned,
            "earned_at": earned.get(badge["key"]),
        }
        for badge in CATALOG
    ]
