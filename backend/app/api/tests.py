from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, TestAttempt, TestQuestion, User
from app.schemas import (
    TestQuestionOut,
    TestQuestionResult,
    TestResult,
    TestSubmission,
)
from app.services import badge_service, ollama_service, validation_service
from app.services.ollama_service import OllamaUnavailable
from app.security import get_current_user

router = APIRouter(prefix="/api/courses/{slug}/test", tags=["tests"])


def _get_course(db: Session, slug: str) -> Course:
    course = db.query(Course).filter(Course.slug == slug).one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="course_not_found")
    return course


def _pick_lang(value, language: str) -> str:
    if isinstance(value, dict):
        return value.get(language) or value.get("en") or ""
    return str(value)


@router.get("", response_model=list[TestQuestionOut])
def get_test(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _get_course(db, slug)
    questions = (
        db.query(TestQuestion)
        .filter(TestQuestion.course_id == course.id)
        .order_by(TestQuestion.order_index)
        .all()
    )
    return [TestQuestionOut.model_validate(q) for q in questions]


@router.post("/attempt", response_model=TestResult)
def submit_test(
    slug: str,
    payload: TestSubmission,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, slug)
    questions = (
        db.query(TestQuestion)
        .filter(TestQuestion.course_id == course.id)
        .order_by(TestQuestion.order_index)
        .all()
    )
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
            score=score,
            total=len(questions),
            correct=correct_count,
            answers=stored,
        )
    )
    db.commit()

    new_badges = badge_service.check_test_badges(db, user, score)
    return TestResult(
        score=score, correct=correct_count, total=len(questions), results=results, new_badges=new_badges
    )
