"""course exams (several practice exams per course)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_exams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", JSONB(), nullable=False),
        sa.Column("description", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("pass_score", sa.Float(), nullable=False, server_default="70"),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
        sa.UniqueConstraint("course_id", "slug", name="uq_exam_course_slug"),
    )
    op.create_index("ix_course_exams_course_id", "course_exams", ["course_id"])

    op.add_column("test_questions", sa.Column("exam_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_test_questions_exam_id",
        "test_questions",
        "course_exams",
        ["exam_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_test_questions_exam_id", "test_questions", ["exam_id"])

    op.add_column("test_attempts", sa.Column("exam_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_test_attempts_exam_id",
        "test_attempts",
        "course_exams",
        ["exam_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_test_attempts_exam_id", "test_attempts", ["exam_id"])


def downgrade() -> None:
    op.drop_index("ix_test_attempts_exam_id", table_name="test_attempts")
    op.drop_constraint("fk_test_attempts_exam_id", "test_attempts", type_="foreignkey")
    op.drop_column("test_attempts", "exam_id")

    op.drop_index("ix_test_questions_exam_id", table_name="test_questions")
    op.drop_constraint("fk_test_questions_exam_id", "test_questions", type_="foreignkey")
    op.drop_column("test_questions", "exam_id")

    op.drop_index("ix_course_exams_course_id", table_name="course_exams")
    op.drop_table("course_exams")
