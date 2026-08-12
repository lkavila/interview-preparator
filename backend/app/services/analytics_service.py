from datetime import date, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import (
    Course,
    Exercise,
    ExerciseAttempt,
    Lesson,
    StudySession,
    TestAttempt,
)
from app.schemas import (
    AnalyticsSummary,
    CourseAccuracy,
    LessonAccuracy,
    StudyDay,
)

MIN_ATTEMPTS_FOR_RANKING = 2


def build_summary(db: Session, user_id: int) -> AnalyticsSummary:
    # Overall exercise attempt stats
    total_attempts, total_correct = (
        db.query(
            func.count(ExerciseAttempt.id),
            func.coalesce(func.sum(case((ExerciseAttempt.is_correct, 1), else_=0)), 0),
        )
        .filter(ExerciseAttempt.user_id == user_id)
        .one()
    )
    total_attempts = int(total_attempts or 0)
    total_correct = int(total_correct or 0)

    # Study time (last 30 days)
    since = date.today() - timedelta(days=29)
    sessions = (
        db.query(StudySession)
        .filter(StudySession.user_id == user_id, StudySession.day >= since)
        .order_by(StudySession.day)
        .all()
    )
    total_seconds = (
        db.query(func.coalesce(func.sum(StudySession.seconds), 0))
        .filter(StudySession.user_id == user_id)
        .scalar()
    )

    # Accuracy per course (exercise attempts joined through lessons)
    course_rows = (
        db.query(
            Course.slug,
            Course.title,
            func.count(ExerciseAttempt.id),
            func.sum(case((ExerciseAttempt.is_correct, 1), else_=0)),
        )
        .join(Lesson, Lesson.course_id == Course.id)
        .join(Exercise, Exercise.lesson_id == Lesson.id)
        .join(ExerciseAttempt, ExerciseAttempt.exercise_id == Exercise.id)
        .filter(ExerciseAttempt.user_id == user_id)
        .group_by(Course.id)
        .order_by(Course.order_index)
        .all()
    )
    by_course = [
        CourseAccuracy(
            course_slug=slug,
            course_title=title,
            attempts=int(attempts),
            correct=int(correct or 0),
            accuracy=round((correct or 0) / attempts * 100, 1) if attempts else 0.0,
        )
        for slug, title, attempts, correct in course_rows
    ]

    # Accuracy per lesson for weak/strong ranking
    lesson_rows = (
        db.query(
            Lesson.id,
            Lesson.slug,
            Lesson.content,
            Course.slug,
            func.count(ExerciseAttempt.id),
            func.sum(case((ExerciseAttempt.is_correct, 1), else_=0)),
        )
        .join(Course, Course.id == Lesson.course_id)
        .join(Exercise, Exercise.lesson_id == Lesson.id)
        .join(ExerciseAttempt, ExerciseAttempt.exercise_id == Exercise.id)
        .filter(ExerciseAttempt.user_id == user_id)
        .group_by(Lesson.id, Course.slug)
        .all()
    )
    lesson_accs = [
        LessonAccuracy(
            lesson_id=lid,
            lesson_slug=lslug,
            question=content.get("question", {}),
            course_slug=cslug,
            attempts=int(attempts),
            correct=int(correct or 0),
            accuracy=round((correct or 0) / attempts * 100, 1) if attempts else 0.0,
        )
        for lid, lslug, content, cslug, attempts, correct in lesson_rows
        if attempts >= MIN_ATTEMPTS_FOR_RANKING
    ]
    weakest = sorted(lesson_accs, key=lambda x: (x.accuracy, -x.attempts))[:8]
    strongest = sorted(lesson_accs, key=lambda x: (-x.accuracy, -x.attempts))[:8]

    return AnalyticsSummary(
        total_attempts=total_attempts,
        total_correct=total_correct,
        overall_accuracy=round(total_correct / total_attempts * 100, 1) if total_attempts else 0.0,
        total_study_seconds=int(total_seconds or 0),
        study_days=[StudyDay(day=s.day, seconds=s.seconds) for s in sessions],
        by_course=by_course,
        weakest_lessons=weakest,
        strongest_lessons=strongest,
    )
