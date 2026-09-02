"""Draws a fresh, category-balanced subset of questions for a sampled exam.

An exam whose ``sampling`` is set (e.g. ``{"VERBAL": 15, "NUMERIC": 20,
"LOGIC": 15}``) keeps its questions as a bank; every attempt gets a different
draw, so the exam stays repeatable.
"""

import random

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CourseExam, TestQuestion


def bank_counts(db: Session, exam: CourseExam) -> dict[str, int]:
    """How many questions the bank actually holds per category."""
    rows = (
        db.query(TestQuestion.category, func.count(TestQuestion.id))
        .filter(TestQuestion.exam_id == exam.id)
        .group_by(TestQuestion.category)
        .all()
    )
    return {category: count for category, count in rows if category is not None}


def effective_quotas(db: Session, exam: CourseExam) -> dict[str, int]:
    """The quotas that can really be served, capped by what the bank holds.

    A bank thinner than its quota serves what it has instead of failing, so a
    course can grow its bank in batches without breaking the exam."""
    sampling: dict[str, int] = exam.sampling or {}
    available = bank_counts(db, exam)
    return {
        category: min(int(quota), available.get(category, 0))
        for category, quota in sampling.items()
    }


def sample_question_ids(db: Session, exam: CourseExam) -> list[int]:
    """Pick the ids for one attempt: balanced by category, shuffled together.

    One round trip: a window function ranks each category's questions in random
    order and the outer filter keeps the first N of each. ``random()`` sorts the
    whole bank, which is irrelevant at these sizes (and stays cheap into the
    thousands); ``TABLESAMPLE`` is not usable here because it cannot honour
    per-category quotas."""
    quotas = {c: n for c, n in effective_quotas(db, exam).items() if n > 0}
    if not quotas:
        return []

    ranked = (
        select(
            TestQuestion.id.label("id"),
            TestQuestion.category.label("category"),
            func.row_number()
            .over(partition_by=TestQuestion.category, order_by=func.random())
            .label("rn"),
        )
        .where(TestQuestion.exam_id == exam.id, TestQuestion.category.isnot(None))
        .cte("ranked")
    )
    stmt = select(ranked.c.id).where(
        or_(*[(ranked.c.category == c) & (ranked.c.rn <= n) for c, n in quotas.items()])
    )

    ids = [row[0] for row in db.execute(stmt).all()]
    # The query returns the draw grouped by category; interleave it so the
    # candidate does not get 15 verbal questions in a row.
    random.shuffle(ids)
    return ids


def served_and_bank(
    exam: CourseExam, per_category: dict[str | None, int], total: int
) -> tuple[int, int | None]:
    """How many questions an attempt serves, and how big the pool behind it is.

    Takes counts already grouped in the caller's query so the exam list stays a
    single round trip. A fixed exam serves everything it has and has no bank."""
    if not exam.sampling:
        return total, None
    served = sum(min(int(quota), per_category.get(c, 0)) for c, quota in exam.sampling.items())
    return served, total
