import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, CourseExam, ExamSession, TestAttempt, TestQuestion, User
from app.schemas import (
    ExamSessionOut,
    ExamSummary,
    TestQuestionOut,
    TestQuestionResult,
    TestResult,
    TestSubmission,
)
from app.services import badge_service, exam_sampling, ollama_service, validation_service
from app.services.ollama_service import OllamaUnavailable
from app.security import get_current_user

router = APIRouter(prefix="/api/courses/{slug}/test", tags=["tests"])
exams_router = APIRouter(prefix="/api/courses/{slug}/exams", tags=["tests"])

DEFAULT_PASS_SCORE = 70.0
# Slack for network latency between the client's last tick and the request
# landing: a submission that leaves on time must not be punished for arriving
# a moment late.
EXAM_GRACE_SECONDS = 5
# Ceiling for sessions on exams that declare no time limit, so rows do not
# stay open forever. Never used as a deadline for scoring.
UNTIMED_SESSION_HOURS = 6


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


def _questions_in_order(db: Session, ids: list[int]) -> list[TestQuestion]:
    """The questions a session served, in the order they were served."""
    rows = db.query(TestQuestion).filter(TestQuestion.id.in_(ids)).all()
    by_id = {q.id: q for q in rows}
    return [by_id[i] for i in ids if i in by_id]


def _start_session(
    db: Session, user: User, course: Course, exam: CourseExam
) -> tuple[ExamSession, list[TestQuestion]]:
    """Draw the questions for one attempt and open its server-side clock."""
    if exam.sampling:
        ids = exam_sampling.sample_question_ids(db, exam)
        questions = _questions_in_order(db, ids)
    else:
        questions = _questions(db, course, exam)
        ids = [q.id for q in questions]
    if not questions:
        raise HTTPException(status_code=404, detail="test_not_found")

    started = datetime.now(timezone.utc)
    span = (
        timedelta(minutes=exam.time_limit_minutes)
        if exam.time_limit_minutes
        else timedelta(hours=UNTIMED_SESSION_HOURS)
    )
    session = ExamSession(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        course_id=course.id,
        exam_id=exam.id,
        question_ids=ids,
        started_at=started,
        expires_at=started + span,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, questions


def _session_payload(
    session: ExamSession, exam: CourseExam, questions: list[TestQuestion]
) -> ExamSessionOut:
    now = datetime.now(timezone.utc)
    return ExamSessionOut(
        session_token=session.token,
        server_time=now,
        expires_at=session.expires_at,
        seconds_remaining=max(0, int((session.expires_at - now).total_seconds())),
        time_limit_minutes=exam.time_limit_minutes,
        pass_score=exam.pass_score,
        questions=[TestQuestionOut.model_validate(q) for q in questions],
    )


def _load_session(db: Session, user: User, course: Course, token: str) -> ExamSession:
    session = (
        db.query(ExamSession)
        .filter(
            ExamSession.token == token,
            ExamSession.user_id == user.id,
            ExamSession.course_id == course.id,
        )
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="exam_session_not_found")
    return session


def exam_summaries(db: Session, course: Course, user: User) -> list[ExamSummary]:
    """Every exam of a course with the user's best score on each.

    Three queries regardless of how many exams the course ships."""
    exams = (
        db.query(CourseExam)
        .filter(CourseExam.course_id == course.id)
        .order_by(CourseExam.order_index)
        .all()
    )
    if not exams:
        return []

    per_category: dict[int, dict[str | None, int]] = defaultdict(dict)
    totals: dict[int, int] = defaultdict(int)
    for exam_id, category, count in (
        db.query(TestQuestion.exam_id, TestQuestion.category, func.count(TestQuestion.id))
        .filter(TestQuestion.course_id == course.id, TestQuestion.exam_id.isnot(None))
        .group_by(TestQuestion.exam_id, TestQuestion.category)
        .all()
    ):
        per_category[exam_id][category] = count
        totals[exam_id] += count

    # Attempts that broke the clock are kept for history but never become a best
    # score, so a timed exam cannot be beaten by simply taking longer.
    stats = {
        exam_id: (best, attempts)
        for exam_id, best, attempts in db.query(
            TestAttempt.exam_id, func.max(TestAttempt.score), func.count(TestAttempt.id)
        )
        .filter(
            TestAttempt.user_id == user.id,
            TestAttempt.course_id == course.id,
            TestAttempt.exam_id.isnot(None),
            TestAttempt.timed_out.is_(False),
        )
        .group_by(TestAttempt.exam_id)
        .all()
    }

    summaries: list[ExamSummary] = []
    for e in exams:
        served, bank = exam_sampling.served_and_bank(
            e, per_category.get(e.id, {}), totals.get(e.id, 0)
        )
        best, attempts = stats.get(e.id, (None, 0))
        summaries.append(
            ExamSummary(
                slug=e.slug,
                order_index=e.order_index,
                title=e.title,
                description=e.description or {},
                question_count=served,
                pass_score=e.pass_score,
                time_limit_minutes=e.time_limit_minutes,
                best_score=best,
                attempts=attempts,
                sampling=e.sampling,
                bank_size=bank,
            )
        )
    return summaries


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
    session: ExamSession | None = None
    timed_out = False

    if payload.session_token:
        session = _load_session(db, user, course, payload.session_token)
        if session.exam_id != (exam.id if exam else None):
            raise HTTPException(status_code=400, detail="session_exam_mismatch")
        if session.submitted_at is not None:
            raise HTTPException(status_code=409, detail="session_already_submitted")
        # Grade the questions the server handed out, never the ones the client
        # sends back: otherwise an attempt could swap in easier questions.
        questions = _questions_in_order(db, session.question_ids)
        if exam is not None and exam.time_limit_minutes:
            deadline = session.expires_at + timedelta(seconds=EXAM_GRACE_SECONDS)
            # Late submissions are still graded — losing 12 minutes of work to a
            # network hiccup would be worse — but they do not count.
            timed_out = datetime.now(timezone.utc) > deadline
    else:
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
            timed_out=timed_out,
        )
    )
    if session is not None:
        session.submitted_at = datetime.now(timezone.utc)  # one submission per session
    db.commit()

    # A score that only happened because the clock was ignored earns nothing.
    new_badges = [] if timed_out else badge_service.check_test_badges(db, user, score)
    return TestResult(
        score=score,
        correct=correct_count,
        total=len(questions),
        pass_score=exam.pass_score if exam else DEFAULT_PASS_SCORE,
        results=results,
        new_badges=new_badges,
        timed_out=timed_out,
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
    return exam_summaries(db, course, user)


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


@exams_router.post("/{exam_slug}/start", response_model=ExamSessionOut)
def start_exam(
    slug: str,
    exam_slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Draw this attempt's questions and start the server-side clock."""
    course = _get_course(db, slug)
    exam = _get_exam(db, course, exam_slug)
    session, questions = _start_session(db, user, course, exam)
    return _session_payload(session, exam, questions)


@exams_router.get("/sessions/{token}", response_model=ExamSessionOut)
def resume_exam_session(
    slug: str,
    token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-serve an in-flight attempt after a reload.

    The same questions come back and the clock keeps running — refreshing the
    page must not hand back time."""
    course = _get_course(db, slug)
    session = _load_session(db, user, course, token)
    if session.submitted_at is not None:
        raise HTTPException(status_code=409, detail="session_already_submitted")
    if session.exam_id is None:
        raise HTTPException(status_code=404, detail="exam_session_not_found")
    exam = db.query(CourseExam).filter(CourseExam.id == session.exam_id).one()

    # Nothing left to resume once the clock has run out: the caller should start
    # a new attempt rather than be handed a session with zero seconds on it.
    if exam.time_limit_minutes and datetime.now(timezone.utc) > session.expires_at + timedelta(
        seconds=EXAM_GRACE_SECONDS
    ):
        raise HTTPException(status_code=409, detail="exam_session_expired")

    questions = _questions_in_order(db, session.question_ids)
    # Re-seeding a question bank replaces its rows, which leaves older sessions
    # pointing at ids that no longer exist. Such a session cannot be graded, so
    # it is reported as stale instead of resumed with a short or empty set.
    if len(questions) != len(session.question_ids):
        raise HTTPException(status_code=409, detail="exam_session_stale")

    return _session_payload(session, exam, questions)


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
