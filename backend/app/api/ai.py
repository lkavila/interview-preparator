from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, Lesson, User
from pydantic import BaseModel, Field

from app.schemas import GenerateExerciseRequest, TutorRequest, TutorResponse
from app.security import get_current_user
from app.services import ollama_service
from app.services.ollama_service import OllamaUnavailable

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def status():
    return {"available": ollama_service.is_available()}


@router.post("/tutor", response_model=TutorResponse)
def tutor(payload: TutorRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    context = ""
    if payload.lesson_id is not None:
        lesson = db.get(Lesson, payload.lesson_id)
        if lesson is not None:
            q = lesson.content.get("question", {})
            d = lesson.content.get("definition", {})
            context = f"{q.get('en', '')}\n{d.get('en', '')}"[:2000]
    try:
        answer = ollama_service.tutor_answer(payload.question, context, user.language, user.id)
    except OllamaUnavailable:
        raise HTTPException(status_code=503, detail="llm_unavailable")
    return TutorResponse(answer=answer)


@router.post("/generate-exercise")
def generate_exercise(
    payload: GenerateExerciseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.slug == payload.course_slug).one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="course_not_found")
    topic = payload.topic or course.title.get("en", course.slug)
    try:
        return ollama_service.generate_exercise(topic, user.language, user.id)
    except OllamaUnavailable:
        raise HTTPException(status_code=503, detail="llm_unavailable")


class CourseDraftRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=120)
    questions: list[str] = Field(default_factory=list, max_length=20)


@router.post("/generate-course-draft")
def generate_course_draft(payload: CourseDraftRequest, user: User = Depends(get_current_user)):
    """Returns a draft course JSON (seed schema) to review and save under seeds/courses/."""
    try:
        return ollama_service.generate_course_draft(payload.topic, payload.questions, user.id)
    except OllamaUnavailable:
        raise HTTPException(status_code=503, detail="llm_unavailable")
