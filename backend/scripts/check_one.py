"""Validate a single course seed file. Usage: python scripts/check_one.py seeds/courses/13-react.json"""
import json
import sys
from collections import Counter

from app.schemas import SeedCourse

path = sys.argv[1]
raw = json.load(open(path, encoding="utf-8"))
course = SeedCourse.model_validate(raw)

counts = Counter(len(lesson.exercises) for lesson in course.lessons)
mcq_correct = Counter()
for lesson in course.lessons:
    for ex in lesson.exercises:
        if ex.type == "multiple_choice":
            for i in ex.solution["correct"]:
                mcq_correct[i] += 1

print("VALID")
print(f"lessons={len(course.lessons)} test={len(course.test)}")
print(f"exercises-per-lesson counts: {dict(counts)}")
print(f"mcq correct-index distribution: {dict(sorted(mcq_correct.items()))}")
