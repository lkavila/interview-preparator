"""Idempotent seeder: loads seeds/courses/*.json, validates with Pydantic and
upserts courses/lessons/exercises/test questions by slug.

Usage:
    python -m app.seed             # validate + seed
    python -m app.seed --check     # validate only (dry run)
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Course, CourseExam, ExamSession, Exercise, Lesson, TestQuestion
from app.schemas import SeedCourse

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds" / "courses"


def load_seed_files() -> list[tuple[Path, SeedCourse]]:
    files = sorted(SEEDS_DIR.glob("*.json"))
    if not files:
        print(f"No seed files found in {SEEDS_DIR}")
        sys.exit(1)
    courses: list[tuple[Path, SeedCourse]] = []
    errors: list[str] = []
    for f in files:
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            courses.append((f, SeedCourse.model_validate(raw)))
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON — {e}")
        except ValidationError as e:
            errors.append(f"{f.name}: schema errors —\n{e}")
    if errors:
        print("Seed validation FAILED:\n")
        for err in errors:
            print(f"  - {err}\n")
        sys.exit(1)
    slugs = [c.slug for _, c in courses]
    if len(slugs) != len(set(slugs)):
        print("Seed validation FAILED: duplicate course slugs")
        sys.exit(1)
    return courses


def _upsert_questions(db: Session, course: Course, exam_id: int | None, seed_questions: list) -> None:
    """Sync one question set (the final test when exam_id is None, else an exam).

    Updated in place when the count matches so attempt history keeps pointing at
    the same rows; replaced wholesale otherwise."""
    query = db.query(TestQuestion).filter(TestQuestion.course_id == course.id)
    query = query.filter(
        TestQuestion.exam_id.is_(None) if exam_id is None else TestQuestion.exam_id == exam_id
    )
    existing = query.order_by(TestQuestion.order_index).all()
    if len(existing) == len(seed_questions):
        for j, (q_model, q_seed) in enumerate(zip(existing, seed_questions)):
            q_model.order_index = j
            q_model.type = q_seed.type
            q_model.category = q_seed.category
            q_model.data = q_seed.data
            q_model.solution = q_seed.solution
            q_model.svg_content = q_seed.svg_content
        return
    # Replacing the rows orphans any attempt still holding their ids, so those
    # sessions are dropped here and the candidate is given a fresh draw instead
    # of an exam that cannot be graded.
    for q_model in existing:
        db.delete(q_model)
    open_sessions = (
        db.query(ExamSession)
        .filter(
            ExamSession.course_id == course.id,
            ExamSession.exam_id.is_(None) if exam_id is None else ExamSession.exam_id == exam_id,
            ExamSession.submitted_at.is_(None),
        )
        .all()
    )
    for session in open_sessions:
        db.delete(session)
    if open_sessions:
        print(
            f"    dropped {len(open_sessions)} in-flight session(s) whose questions were replaced"
        )
    db.flush()
    for j, q_seed in enumerate(seed_questions):
        db.add(
            TestQuestion(
                course_id=course.id,
                exam_id=exam_id,
                order_index=j,
                type=q_seed.type,
                category=q_seed.category,
                data=q_seed.data,
                solution=q_seed.solution,
                svg_content=q_seed.svg_content,
            )
        )


def upsert_course(db: Session, seed: SeedCourse) -> None:
    course = db.query(Course).filter(Course.slug == seed.slug).one_or_none()
    if course is None:
        course = Course(slug=seed.slug)
        db.add(course)
    course.order_index = seed.order
    course.icon = seed.icon
    course.title = seed.title
    course.description = seed.description
    db.flush()

    seen_lesson_slugs = set()
    for i, seed_lesson in enumerate(seed.lessons):
        seen_lesson_slugs.add(seed_lesson.slug)
        lesson = (
            db.query(Lesson)
            .filter(Lesson.course_id == course.id, Lesson.slug == seed_lesson.slug)
            .one_or_none()
        )
        if lesson is None:
            lesson = Lesson(course_id=course.id, slug=seed_lesson.slug)
            db.add(lesson)
        lesson.order_index = i
        lesson.content = {
            "question": seed_lesson.question,
            "definition": seed_lesson.definition,
            "examples": seed_lesson.examples,
        }
        db.flush()

        # Exercises are replaced wholesale (attempts reference exercises by id,
        # so we update in place when counts match to preserve attempt history).
        existing = (
            db.query(Exercise)
            .filter(Exercise.lesson_id == lesson.id)
            .order_by(Exercise.order_index)
            .all()
        )
        if len(existing) == len(seed_lesson.exercises):
            for j, (ex_model, ex_seed) in enumerate(zip(existing, seed_lesson.exercises)):
                ex_model.order_index = j
                ex_model.type = ex_seed.type
                ex_model.validation_mode = ex_seed.validation_mode
                ex_model.data = ex_seed.data
                ex_model.solution = ex_seed.solution
        else:
            for ex_model in existing:
                db.delete(ex_model)
            db.flush()
            for j, ex_seed in enumerate(seed_lesson.exercises):
                db.add(
                    Exercise(
                        lesson_id=lesson.id,
                        order_index=j,
                        type=ex_seed.type,
                        validation_mode=ex_seed.validation_mode,
                        data=ex_seed.data,
                        solution=ex_seed.solution,
                    )
                )

    # Remove lessons no longer present in the seed
    for lesson in list(course.lessons):
        if lesson.slug not in seen_lesson_slugs and lesson.id is not None:
            db.delete(lesson)

    # Final test (exam_id IS NULL) and, if the course ships them, extra exams
    _upsert_questions(db, course, None, seed.test)

    seen_exam_slugs = set()
    for i, seed_exam in enumerate(seed.exams):
        seen_exam_slugs.add(seed_exam.slug)
        exam = (
            db.query(CourseExam)
            .filter(CourseExam.course_id == course.id, CourseExam.slug == seed_exam.slug)
            .one_or_none()
        )
        if exam is None:
            exam = CourseExam(course_id=course.id, slug=seed_exam.slug)
            db.add(exam)
        exam.order_index = i
        exam.title = seed_exam.title
        exam.description = seed_exam.description
        exam.pass_score = seed_exam.pass_score
        exam.time_limit_minutes = seed_exam.time_limit_minutes
        exam.sampling = seed_exam.sampling
        db.flush()
        _upsert_questions(db, course, exam.id, seed_exam.questions)

    for exam in list(course.exams):
        if exam.slug not in seen_exam_slugs and exam.id is not None:
            db.delete(exam)


def main() -> None:
    check_only = "--check" in sys.argv
    courses = load_seed_files()
    total_lessons = sum(len(c.lessons) for _, c in courses)
    total_tests = sum(len(c.test) for _, c in courses)
    total_exams = sum(len(c.exams) for _, c in courses)
    total_exam_q = sum(len(e.questions) for _, c in courses for e in c.exams)
    print(
        f"Validated {len(courses)} courses, {total_lessons} lessons, {total_tests} test questions, "
        f"{total_exams} extra exams ({total_exam_q} questions)."
    )
    for _, course in courses:
        for exam in course.exams:
            thin = exam.thin_categories()
            if thin:
                print(
                    f"  warning: {course.slug}/{exam.slug} draws {sorted(thin)} from a bank "
                    "smaller than the quota — attempts will serve what is available."
                )
    if check_only:
        print("Dry run (--check): nothing written.")
        return

    db = SessionLocal()
    try:
        for path, seed in courses:
            upsert_course(db, seed)
            extra = f" + {len(seed.exams)} exams" if seed.exams else ""
            print(f"  seeded {seed.slug} ({len(seed.lessons)} lessons{extra}) from {path.name}")
        db.commit()
        print("Done.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
