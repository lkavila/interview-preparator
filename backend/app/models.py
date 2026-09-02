from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
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
    # every question of the course; the classic final test is the subset with exam_id IS NULL
    test_questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="TestQuestion.order_index"
    )
    exams: Mapped[list["CourseExam"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CourseExam.order_index"
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


class CourseExam(Base):
    """A named practice exam inside a course (e.g. a 50-question mock exam).

    Courses keep their classic final test as questions with ``exam_id IS NULL``;
    any extra exam gets a row here and owns its own questions."""

    __tablename__ = "course_exams"
    __table_args__ = (UniqueConstraint("course_id", "slug", name="uq_exam_course_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[dict] = mapped_column(JSONB, default=dict)
    pass_score: Mapped[float] = mapped_column(Float, default=70.0)  # 0..100
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # {"VERBAL": 15, ...} turns `questions` into a bank the attempt is sampled
    # from; NULL keeps the classic behaviour of serving every question in order.
    sampling: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    course: Mapped["Course"] = relationship(back_populates="exams")
    questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="TestQuestion.order_index"
    )


class TestQuestion(Base):
    __tablename__ = "test_questions"
    __table_args__ = (Index("ix_test_questions_exam_category", "exam_id", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    # NULL = the course's classic final test
    exam_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_exams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(30))  # multiple_choice | open_text
    # Topic tag used to balance a sampled attempt (VERBAL | NUMERIC | LOGIC).
    # NULL on the courses that serve a fixed question set.
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB)
    solution: Mapped[dict] = mapped_column(JSONB)
    # Inline figure for spatial-reasoning questions, sanitised before rendering.
    svg_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    course: Mapped["Course"] = relationship(back_populates="test_questions")
    exam: Mapped["CourseExam | None"] = relationship(back_populates="questions")


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
    # NULL = attempt on the course's classic final test
    exam_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_exams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    score: Mapped[float] = mapped_column(Float)  # 0..100
    total: Mapped[int] = mapped_column(Integer)
    correct: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict] = mapped_column(JSONB)  # {question_id: {answer, correct}}
    # Submitted past the server deadline: graded and stored, but excluded from
    # best scores and badges.
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExamSession(Base):
    """Server-side clock for one timed attempt.

    The session owns both the deadline and the exact questions that were served,
    so a client can neither extend its own time nor swap in easier questions."""

    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    # NULL = a session on the course's classic final test
    exam_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_exams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    question_ids: Mapped[list] = mapped_column(JSONB)  # sampled ids, in served order
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LessonComponent(Base):
    """Configurable UI component attached to a lesson (visibility controlled from DB)."""

    __tablename__ = "lesson_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    # quiz_card | interview_question_card | fun_fact_carousel | concept_diagram | image_gallery
    # | sql_playground | badge_progress
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
