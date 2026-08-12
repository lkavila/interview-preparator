"""Deterministically shuffle multiple-choice options in all course seeds so the
correct answer is not biased toward index 0. Remaps solution.correct accordingly.

Skips exercises whose explanation references option positions (e.g. "option A",
"the first option"), since reordering would break the text.

Run from backend/:  python scripts/shuffle_mcq.py
"""

import json
import random
import re
from collections import Counter
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parents[1] / "seeds" / "courses"

POSITION_REF = re.compile(
    r"option [abcd]\b|opci\w?n [abcd]\b|first option|second option|third option|fourth option"
    r"|primera opci|segunda opci|tercera opci|cuarta opci|answer is [abcd]\b|respuesta es la [abcd]\b",
    re.IGNORECASE,
)


def references_positions(data: dict) -> bool:
    explanation = data.get("explanation") or {}
    text = " ".join(str(v) for v in explanation.values()) if isinstance(explanation, dict) else str(explanation)
    return bool(POSITION_REF.search(text))


def shuffle_mcq(data: dict, solution: dict, seed_key: str) -> bool:
    """Shuffle options in place; returns True if changed."""
    options = data.get("options")
    correct = solution.get("correct")
    if not options or not isinstance(correct, list) or len(options) < 2:
        return False
    if references_positions(data):
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

    for path in sorted(SEEDS_DIR.glob("*.json")):
        course = json.loads(path.read_text(encoding="utf-8"))
        changed = 0

        for lesson in course.get("lessons", []):
            for k, ex in enumerate(lesson.get("exercises", [])):
                if ex.get("type") != "multiple_choice":
                    continue
                for c in ex["solution"].get("correct", []):
                    before[c] += 1
                if references_positions(ex["data"]):
                    skipped += 1
                elif shuffle_mcq(ex["data"], ex["solution"], f"{course['slug']}:{lesson['slug']}:{k}"):
                    changed += 1
                for c in ex["solution"].get("correct", []):
                    after[c] += 1

        for k, q in enumerate(course.get("test", [])):
            if q.get("type") != "multiple_choice":
                continue
            for c in q["solution"].get("correct", []):
                before[c] += 1
            if references_positions(q["data"]):
                skipped += 1
            elif shuffle_mcq(q["data"], q["solution"], f"{course['slug']}:test:{k}"):
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
