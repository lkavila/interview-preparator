"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("theme", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("icon", sa.String(length=40), nullable=False),
        sa.Column("title", JSONB(), nullable=False),
        sa.Column("description", JSONB(), nullable=False),
    )
    op.create_index("ix_courses_slug", "courses", ["slug"], unique=True)

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.UniqueConstraint("course_id", "slug", name="uq_lesson_course_slug"),
    )
    op.create_index("ix_lessons_course_id", "lessons", ["course_id"])

    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("validation_mode", sa.String(length=10), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("solution", JSONB(), nullable=False),
    )
    op.create_index("ix_exercises_lesson_id", "exercises", ["lesson_id"])

    op.create_table(
        "test_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("solution", JSONB(), nullable=False),
    )
    op.create_index("ix_test_questions_course_id", "test_questions", ["course_id"])

    op.create_table(
        "user_lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )
    op.create_index("ix_user_lesson_progress_user_id", "user_lesson_progress", ["user_id"])
    op.create_index("ix_user_lesson_progress_lesson_id", "user_lesson_progress", ["lesson_id"])

    op.create_table(
        "exercise_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", sa.Integer(), sa.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answer", JSONB(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exercise_attempts_user_id", "exercise_attempts", ["user_id"])
    op.create_index("ix_exercise_attempts_exercise_id", "exercise_attempts", ["exercise_id"])
    op.create_index("ix_exercise_attempts_created_at", "exercise_attempts", ["created_at"])

    op.create_table(
        "test_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("answers", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_attempts_user_id", "test_attempts", ["user_id"])
    op.create_index("ix_test_attempts_course_id", "test_attempts", ["course_id"])

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "day", name="uq_study_user_day"),
    )
    op.create_index("ix_study_sessions_user_id", "study_sessions", ["user_id"])
    op.create_index("ix_study_sessions_day", "study_sessions", ["day"])


def downgrade() -> None:
    op.drop_table("study_sessions")
    op.drop_table("test_attempts")
    op.drop_table("exercise_attempts")
    op.drop_table("user_lesson_progress")
    op.drop_table("test_questions")
    op.drop_table("exercises")
    op.drop_table("lessons")
    op.drop_table("courses")
    op.drop_table("users")
