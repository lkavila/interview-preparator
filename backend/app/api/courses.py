from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Course,
    Lesson,
    LessonComponent,
    TestAttempt,
    TestQuestion,
    User,
    UserLessonProgress,
)
from app.schemas import (
    CourseDetail,
    CourseSummary,
    EnrichmentResponse,
    ExerciseOut,
    LessonComponentOut,
    LessonOut,
    LessonSummary,
)
from app.api.tests import exam_summaries
from app.security import get_current_user
from app.services import badge_service, enrichment_service

router = APIRouter(prefix="/api", tags=["courses"])


def _completed_lesson_ids(db: Session, user_id: int) -> set[int]:
    rows = db.query(UserLessonProgress.lesson_id).filter(UserLessonProgress.user_id == user_id).all()
    return {r[0] for r in rows}


@router.get("/courses", response_model=list[CourseSummary])
def list_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    courses = (
        db.query(Course).options(selectinload(Course.lessons)).order_by(Course.order_index).all()
    )
    completed = _completed_lesson_ids(db, user.id)

    best_scores = dict(
        db.query(TestAttempt.course_id, func.max(TestAttempt.score))
        .filter(TestAttempt.user_id == user.id)
        .group_by(TestAttempt.course_id)
        .all()
    )

    return [
        CourseSummary(
            id=c.id,
            slug=c.slug,
            order_index=c.order_index,
            icon=c.icon,
            title=c.title,
            description=c.description,
            lesson_count=len(c.lessons),
            completed_lessons=sum(1 for l in c.lessons if l.id in completed),
            best_test_score=best_scores.get(c.id),
        )
        for c in courses
    ]


@router.get("/courses/{slug}", response_model=CourseDetail)
def course_detail(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = (
        db.query(Course)
        .options(selectinload(Course.lessons), selectinload(Course.test_questions))
        .filter(Course.slug == slug)
        .one_or_none()
    )
    if course is None:
        raise HTTPException(status_code=404, detail="course_not_found")
    completed = _completed_lesson_ids(db, user.id)

    best_score = (
        db.query(func.max(TestAttempt.score))
        .filter(TestAttempt.user_id == user.id, TestAttempt.course_id == course.id)
        .scalar()
    )

    final_test_count = (
        db.query(func.count(TestQuestion.id))
        .filter(TestQuestion.course_id == course.id, TestQuestion.exam_id.is_(None))
        .scalar()
        or 0
    )
    exams = exam_summaries(db, course, user)

    return CourseDetail(
        id=course.id,
        slug=course.slug,
        order_index=course.order_index,
        icon=course.icon,
        title=course.title,
        description=course.description,
        lesson_count=len(course.lessons),
        completed_lessons=sum(1 for l in course.lessons if l.id in completed),
        best_test_score=best_score,
        test_question_count=final_test_count,
        exams=exams,
        lessons=[
            LessonSummary(
                id=l.id,
                slug=l.slug,
                order_index=l.order_index,
                question=l.content.get("question", {}),
                completed=l.id in completed,
            )
            for l in course.lessons
        ],
    )


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def lesson_detail(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = (
        db.query(Lesson)
        .options(selectinload(Lesson.exercises), selectinload(Lesson.course))
        .filter(Lesson.id == lesson_id)
        .one_or_none()
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson_not_found")

    siblings = (
        db.query(Lesson.id, Lesson.order_index)
        .filter(Lesson.course_id == lesson.course_id)
        .order_by(Lesson.order_index)
        .all()
    )
    ids = [s[0] for s in siblings]
    idx = ids.index(lesson.id)

    completed = (
        db.query(UserLessonProgress)
        .filter(UserLessonProgress.user_id == user.id, UserLessonProgress.lesson_id == lesson.id)
        .one_or_none()
        is not None
    )

    components = (
        db.query(LessonComponent)
        .filter(LessonComponent.lesson_id == lesson.id, LessonComponent.enabled.is_(True))
        .order_by(LessonComponent.order_index)
        .all()
    )

    return LessonOut(
        id=lesson.id,
        slug=lesson.slug,
        order_index=lesson.order_index,
        course_slug=lesson.course.slug,
        course_title=lesson.course.title,
        content=lesson.content,
        exercises=[ExerciseOut.model_validate(e) for e in lesson.exercises],
        components=[LessonComponentOut.model_validate(c) for c in components],
        completed=completed,
        prev_lesson_id=ids[idx - 1] if idx > 0 else None,
        next_lesson_id=ids[idx + 1] if idx < len(ids) - 1 else None,
    )


@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson_not_found")
    existing = (
        db.query(UserLessonProgress)
        .filter(UserLessonProgress.user_id == user.id, UserLessonProgress.lesson_id == lesson_id)
        .one_or_none()
    )
    if existing is None:
        db.add(UserLessonProgress(user_id=user.id, lesson_id=lesson_id))
        db.commit()
    new_badges = badge_service.check_lesson_badges(db, user)
    return {"ok": True, "new_badges": new_badges}


@router.get("/lessons/{lesson_id}/enrichment", response_model=EnrichmentResponse)
def lesson_enrichment(
    lesson_id: int,
    refresh: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dynamic LLM-generated content for a lesson (fun facts, interview questions, quiz).

    Generated on first open, cached in MongoDB per language; serves derived
    fallback content when the local LLM is unavailable."""
    lesson = (
        db.query(Lesson)
        .options(selectinload(Lesson.exercises))
        .filter(Lesson.id == lesson_id)
        .one_or_none()
    )
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson_not_found")
    return enrichment_service.get_enrichment(lesson, user.language, user.id, refresh=refresh)
