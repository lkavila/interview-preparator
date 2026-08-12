from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(5), default="es")
    theme: Mapped[str] = mapped_column(String(10), default="dark")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str] = mapped_column(String(40), default="book")
    title: Mapped[dict] = mapped_column(JSONB)  # {"en": ..., "es": ...}
    description: Mapped[dict] = mapped_column(JSONB)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Lesson.order_index"
    )
    test_questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="TestQuestion.order_index"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("course_id", "slug", name="uq_lesson_course_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(120))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    # {"question": {en,es}, "definition": {en,es}, "examples": [{en,es}, ...]}
    content: Mapped[dict] = mapped_column(JSONB)

    course: Mapped["Course"] = relationship(back_populates="lessons")
    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="Exercise.order_index"
    )


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(30))  # multiple_choice | matching | ordering | table_builder | sql | code | open_text
    validation_mode: Mapped[str] = mapped_column(String(10), default="static")  # static | llm
    data: Mapped[dict] = mapped_column(JSONB)  # prompt/options, bilingual, safe for client
    solution: Mapped[dict] = mapped_column(JSONB)  # server-side only

    lesson: Mapped["Lesson"] = relationship(back_populates="exercises")


class TestQuestion(Base):
    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(30))  # multiple_choice | open_text
    data: Mapped[dict] = mapped_column(JSONB)
    solution: Mapped[dict] = mapped_column(JSONB)

    course: Mapped["Course"] = relationship(back_populates="test_questions")


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    answer: Mapped[dict] = mapped_column(JSONB)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)  # 0..100
    total: Mapped[int] = mapped_column(Integer)
    correct: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict] = mapped_column(JSONB)  # {question_id: {answer, correct}}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LessonComponent(Base):
    """Configurable UI component attached to a lesson (visibility controlled from DB)."""

    __tablename__ = "lesson_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    # quiz_card | interview_question_card | fun_fact_carousel | concept_diagram | image_gallery | badge_progress
    component_type: Mapped[str] = mapped_column(String(40))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    lesson: Mapped["Lesson"] = relationship()


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_key", name="uq_badge_user_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    badge_key: Mapped[str] = mapped_column(String(60))
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_study_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
