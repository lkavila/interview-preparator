"""Deterministically shuffle multiple-choice options in all course seeds so the
correct answer is not biased toward index 0. Remaps solution.correct accordingly.

Skips exercises whose explanation references option positions (e.g. "option A",
"the first option"), since reordering would break the text.

Shuffling is deterministic per exercise, so re-running reshuffles rather than
being idempotent. Pass course-file name fragments to limit it to those files —
use this when adding a course, so the untouched ones are not churned:

    python scripts/shuffle_mcq.py                       # every course
    python scripts/shuffle_mcq.py 16-database 17-behav  # only those files
    python scripts/shuffle_mcq.py 05-post --lesson=window   # only those lessons

--lesson= narrows to lessons whose slug contains the fragment, and skips the
course test block and practice exams, so newly added lessons can be shuffled
without touching the rest of an existing course.
"""

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parents[1] / "seeds" / "courses"

POSITION_REF = re.compile(
    r"option [abcd]\b|opci\w?n [abcd]\b|first option|second option|third option|fourth option"
    r"|primera opci|segunda opci|tercera opci|cuarta opci|answer is [abcd]\b|respuesta es la [abcd]\b",
    re.IGNORECASE,
)


def references_positions(*sources: dict) -> bool:
    """True when an explanation refers to an option by position, which reordering
    would break. Lesson exercises keep it in data, exam questions in solution."""
    text = []
    for src in sources:
        explanation = (src or {}).get("explanation") or {}
        if isinstance(explanation, dict):
            text.extend(str(v) for v in explanation.values())
        else:
            text.append(str(explanation))
    return bool(POSITION_REF.search(" ".join(text)))


def shuffle_mcq(data: dict, solution: dict, seed_key: str) -> bool:
    """Shuffle options in place; returns True if changed."""
    options = data.get("options")
    correct = solution.get("correct")
    if not options or not isinstance(correct, list) or len(options) < 2:
        return False
    if references_positions(data, solution):
        return False
    rng = random.Random(seed_key)
    perm = list(range(len(options)))
    rng.shuffle(perm)
    if perm == list(range(len(options))):
        return False
    data["options"] = [options[i] for i in perm]
    solution["correct"] = sorted(perm.index(c) for c in correct)
    return True


def main() -> None:
    before: Counter = Counter()
    after: Counter = Counter()
    changed_total = 0
    skipped = 0

    args = sys.argv[1:]
    lessons_only = [a.split("=", 1)[1] for a in args if a.startswith("--lesson=")]
    only = [a for a in args if not a.startswith("--")]

    paths = [p for p in sorted(SEEDS_DIR.glob("*.json"))
             if not only or any(frag in p.name for frag in only)]
    if only and not paths:
        raise SystemExit(f"no course files matched {only}")

    for path in paths:
        course = json.loads(path.read_text(encoding="utf-8"))
        changed = 0

        for lesson in course.get("lessons", []):
            if lessons_only and not any(f in lesson["slug"] for f in lessons_only):
                continue
            for k, ex in enumerate(lesson.get("exercises", [])):
                if ex.get("type") != "multiple_choice":
                    continue
                for c in ex["solution"].get("correct", []):
                    before[c] += 1
                if references_positions(ex["data"], ex["solution"]):
                    skipped += 1
                elif shuffle_mcq(ex["data"], ex["solution"], f"{course['slug']}:{lesson['slug']}:{k}"):
                    changed += 1
                for c in ex["solution"].get("correct", []):
                    after[c] += 1

        # --lesson= narrows to specific lessons, so leave the test block alone.
        for k, q in enumerate([] if lessons_only else course.get("test", [])):
            if q.get("type") != "multiple_choice":
                continue
            for c in q["solution"].get("correct", []):
                before[c] += 1
            if references_positions(q["data"], q["solution"]):
                skipped += 1
            elif shuffle_mcq(q["data"], q["solution"], f"{course['slug']}:test:{k}"):
                changed += 1
            for c in q["solution"].get("correct", []):
                after[c] += 1

        # Practice exams: courses can ship an `exams` array besides (or instead of) `test`.
        for exam in [] if lessons_only else course.get("exams", []):
            for k, q in enumerate(exam.get("questions", [])):
                if q.get("type") != "multiple_choice":
                    continue
                for c in q["solution"].get("correct", []):
                    before[c] += 1
                if references_positions(q["data"], q["solution"]):
                    skipped += 1
                elif shuffle_mcq(q["data"], q["solution"], f"{course['slug']}:{exam['slug']}:{k}"):
                    changed += 1
                for c in q["solution"].get("correct", []):
                    after[c] += 1

        if changed:
            path.write_text(json.dumps(course, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed_total += changed
        print(f"{path.name}: shuffled {changed} MCQs")

    print(f"\nTotal shuffled: {changed_total}, skipped (position-referencing): {skipped}")
    print(f"correct-index distribution before: {dict(sorted(before.items()))}")
    print(f"correct-index distribution after:  {dict(sorted(after.items()))}")


if __name__ == "__main__":
    main()
