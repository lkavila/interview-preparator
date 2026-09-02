"""question banks (sampled exams) + server-side exam sessions

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # An exam with `sampling` treats its questions as a bank and draws a fresh,
    # category-balanced subset on every attempt.
    op.add_column("course_exams", sa.Column("sampling", JSONB(), nullable=True))

    op.add_column("test_questions", sa.Column("category", sa.String(length=20), nullable=True))
    op.add_column("test_questions", sa.Column("svg_content", sa.Text(), nullable=True))
    op.create_index(
        "ix_test_questions_exam_category", "test_questions", ["exam_id", "category"]
    )

    op.add_column(
        "test_attempts",
        sa.Column("timed_out", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "exam_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_id",
            sa.Integer(),
            sa.ForeignKey("course_exams.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("question_ids", JSONB(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_exam_sessions_token", "exam_sessions", ["token"], unique=True)
    op.create_index("ix_exam_sessions_user_id", "exam_sessions", ["user_id"])
    op.create_index("ix_exam_sessions_course_id", "exam_sessions", ["course_id"])
    op.create_index("ix_exam_sessions_exam_id", "exam_sessions", ["exam_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_sessions_exam_id", table_name="exam_sessions")
    op.drop_index("ix_exam_sessions_course_id", table_name="exam_sessions")
    op.drop_index("ix_exam_sessions_user_id", table_name="exam_sessions")
    op.drop_index("ix_exam_sessions_token", table_name="exam_sessions")
    op.drop_table("exam_sessions")

    op.drop_column("test_attempts", "timed_out")

    op.drop_index("ix_test_questions_exam_category", table_name="test_questions")
    op.drop_column("test_questions", "svg_content")
    op.drop_column("test_questions", "category")

    op.drop_column("course_exams", "sampling")
