"""lesson components and user badges

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("component_type", sa.String(length=40), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_lesson_components_lesson_id", "lesson_components", ["lesson_id"])

    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("badge_key", sa.String(length=60), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "badge_key", name="uq_badge_user_key"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_badges")
    op.drop_table("lesson_components")
