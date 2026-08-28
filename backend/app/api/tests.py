from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, CourseExam, TestAttempt, TestQuestion, User
from app.schemas import (
    ExamSummary,
    TestQuestionOut,
    TestQuestionResult,
    TestResult,
    TestSubmission,
)
from app.services import badge_service, ollama_service, validation_service
from app.services.ollama_service import OllamaUnavailable
from app.security import get_current_user

router = APIRouter(prefix="/api/courses/{slug}/test", tags=["tests"])
exams_router = APIRouter(prefix="/api/courses/{slug}/exams", tags=["tests"])

DEFAULT_PASS_SCORE = 70.0


def _get_course(db: Session, slug: str) -> Course:
    course = db.query(Course).filter(Course.slug == slug).one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="course_not_found")
    return course


def _get_exam(db: Session, course: Course, exam_slug: str) -> CourseExam:
    exam = (
        db.query(CourseExam)
        .filter(CourseExam.course_id == course.id, CourseExam.slug == exam_slug)
        .one_or_none()
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="exam_not_found")
    return exam


def _questions(db: Session, course: Course, exam: CourseExam | None) -> list[TestQuestion]:
    """Questions of one exam, or of the course's classic final test when exam is None."""
    query = db.query(TestQuestion).filter(TestQuestion.course_id == course.id)
    query = query.filter(
        TestQuestion.exam_id.is_(None) if exam is None else TestQuestion.exam_id == exam.id
    )
    return query.order_by(TestQuestion.order_index).all()


def _pick_lang(value, language: str) -> str:
    if isinstance(value, dict):
        return value.get(language) or value.get("en") or ""
    return str(value)


def _grade(
    db: Session,
    user: User,
    course: Course,
    exam: CourseExam | None,
    payload: TestSubmission,
) -> TestResult:
    questions = _questions(db, course, exam)
    if not questions:
        raise HTTPException(status_code=404, detail="test_not_found")

    results: list[TestQuestionResult] = []
    stored: dict[str, dict] = {}
    correct_count = 0

    for q in questions:
        answer = payload.answers.get(q.id)
        correct = False
        feedback = None
        if answer is not None:
            if q.type == "multiple_choice":
                correct = validation_service.validate_multiple_choice(answer, q.solution)
            else:  # open_text graded by LLM; if unavailable, count as incorrect with a note
                answer_text = str(answer.get("text", "")).strip()
                if answer_text:
                    prompt = _pick_lang(q.data.get("prompt", {}), user.language)
                    criteria = _pick_lang(q.solution.get("criteria", {}), user.language)
                    try:
                        correct, feedback = ollama_service.validate_answer(
                            prompt=prompt,
                            answer=answer_text,
                            criteria=criteria,
                            reference=q.solution.get("reference"),
                            language=user.language,
                            user_id=user.id,
                        )
                    except OllamaUnavailable:
                        feedback = (
                            "IA no disponible: la respuesta no pudo ser evaluada."
                            if user.language == "es"
                            else "AI unavailable: the answer could not be graded."
                        )
        if correct:
            correct_count += 1
        stored[str(q.id)] = {"answer": answer, "correct": correct}
        solution_out = dict(q.solution) if q.type == "multiple_choice" else None
        results.append(
            TestQuestionResult(question_id=q.id, correct=correct, feedback=feedback, solution=solution_out)
        )

    score = round(correct_count / len(questions) * 100, 1)
    db.add(
        TestAttempt(
            user_id=user.id,
            course_id=course.id,
            exam_id=exam.id if exam else None,
            score=score,
            total=len(questions),
            correct=correct_count,
            answers=stored,
        )
    )
    db.commit()

    new_badges = badge_service.check_test_badges(db, user, score)
    return TestResult(
        score=score,
        correct=correct_count,
        total=len(questions),
        pass_score=exam.pass_score if exam else DEFAULT_PASS_SCORE,
        results=results,
        new_badges=new_badges,
    )


# ---------------------------------------------------------------------------
# Classic final test (one per course)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TestQuestionOut])
def get_test(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _get_course(db, slug)
    return [TestQuestionOut.model_validate(q) for q in _questions(db, course, None)]


@router.post("/attempt", response_model=TestResult)
def submit_test(
    slug: str,
    payload: TestSubmission,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, slug)
    return _grade(db, user, course, None, payload)


# ---------------------------------------------------------------------------
# Practice exams (certification mocks: several per course, each its own length)
# ---------------------------------------------------------------------------


@exams_router.get("", response_model=list[ExamSummary])
def list_exams(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _get_course(db, slug)
    exams = (
        db.query(CourseExam)
        .filter(CourseExam.course_id == course.id)
        .order_by(CourseExam.order_index)
        .all()
    )
    counts = dict(
        db.query(TestQuestion.exam_id, func.count(TestQuestion.id))
        .filter(TestQuestion.course_id == course.id, TestQuestion.exam_id.isnot(None))
        .group_by(TestQuestion.exam_id)
        .all()
    )
    stats = {
        exam_id: (best, attempts)
        for exam_id, best, attempts in db.query(
            TestAttempt.exam_id, func.max(TestAttempt.score), func.count(TestAttempt.id)
        )
        .filter(
            TestAttempt.user_id == user.id,
            TestAttempt.course_id == course.id,
            TestAttempt.exam_id.isnot(None),
        )
        .group_by(TestAttempt.exam_id)
        .all()
    }
    return [
        ExamSummary(
            slug=e.slug,
            order_index=e.order_index,
            title=e.title,
            description=e.description or {},
            question_count=counts.get(e.id, 0),
            pass_score=e.pass_score,
            time_limit_minutes=e.time_limit_minutes,
            best_score=stats.get(e.id, (None, 0))[0],
            attempts=stats.get(e.id, (None, 0))[1],
        )
        for e in exams
    ]


@exams_router.get("/{exam_slug}", response_model=list[TestQuestionOut])
def get_exam(
    slug: str,
    exam_slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, slug)
    exam = _get_exam(db, course, exam_slug)
    return [TestQuestionOut.model_validate(q) for q in _questions(db, course, exam)]


@exams_router.post("/{exam_slug}/attempt", response_model=TestResult)
def submit_exam(
    slug: str,
    exam_slug: str,
    payload: TestSubmission,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, slug)
    exam = _get_exam(db, course, exam_slug)
    return _grade(db, user, course, exam, payload)
