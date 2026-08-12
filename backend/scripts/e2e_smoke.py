"""End-to-end API smoke test against a running backend on localhost:8000."""
import sys
import time

import httpx

BASE = "http://localhost:8000/api"
EMAIL = f"e2e_{int(time.time())}@example.com"
PASSWORD = "SuperSecret123!"

passed: list[str] = []
failed: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        passed.append(name)
        print(f"PASS {name}")
    else:
        failed.append(name)
        print(f"FAIL {name} {detail}")


client = httpx.Client(timeout=180)

# 1. Register
r = client.post(f"{BASE}/auth/register", json={
    "email": EMAIL, "password": PASSWORD, "name": "E2E User", "language": "es", "theme": "dark",
})
check("register", r.status_code == 200, r.text[:300])
token = r.json()["access_token"]
client.headers["Authorization"] = f"Bearer {token}"

# 2. Login
r = client.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
check("login", r.status_code == 200, r.text[:300])

# 3. Me + preferences
r = client.get(f"{BASE}/auth/me")
check("me", r.status_code == 200 and r.json()["language"] == "es", r.text[:300])
r = client.patch(f"{BASE}/auth/me", json={"theme": "light"})
check("update-preferences", r.status_code == 200 and r.json()["theme"] == "light", r.text[:300])

# 4. Courses
r = client.get(f"{BASE}/courses")
courses = r.json()
check("courses-list", r.status_code == 200 and len(courses) == 15, f"got {len(courses)}")

r = client.get(f"{BASE}/courses/cs-fundamentals")
detail = r.json()
check("course-detail", r.status_code == 200 and len(detail["lessons"]) == 14, r.text[:200])

# 5. Lesson detail
lesson_id = detail["lessons"][0]["id"]
r = client.get(f"{BASE}/lessons/{lesson_id}")
lesson = r.json()
check(
    "lesson-detail",
    r.status_code == 200 and len(lesson["exercises"]) == 3 and lesson["content"]["definition"]["es"],
    r.text[:200],
)

# 5b. DB-configured lesson components
components = lesson.get("components", [])
comp_types = {c["component_type"] for c in components}
check(
    "lesson-components",
    {"quiz_card", "interview_question_card", "fun_fact_carousel"}.issubset(comp_types),
    f"got {sorted(comp_types)}",
)

# 5c. Enrichment (LLM-generated, cached in Mongo; fallback if Ollama is down)
r = client.get(f"{BASE}/lessons/{lesson_id}/enrichment")
enr = r.json()
check(
    "enrichment",
    r.status_code == 200
    and enr.get("source") in ("llm", "fallback")
    and isinstance(enr.get("fun_facts"), list)
    and isinstance(enr.get("interview_questions"), list)
    and isinstance(enr.get("quiz"), list),
    r.text[:300],
)
if r.status_code == 200:
    print(
        f"  enrichment source={enr.get('source')} facts={len(enr.get('fun_facts', []))} "
        f"questions={len(enr.get('interview_questions', []))} quiz={len(enr.get('quiz', []))}"
    )

# 6. Static MCQ: submit an answer, learn the solution from the response, then submit it
mcq = None
open_ex = None
for ls in detail["lessons"]:
    lr = client.get(f"{BASE}/lessons/{ls['id']}").json()
    for ex in lr["exercises"]:
        if ex["type"] == "multiple_choice" and mcq is None:
            mcq = ex
        if ex["type"] == "open_text" and open_ex is None:
            open_ex = ex
assert mcq is not None
r = client.post(f"{BASE}/exercises/{mcq['id']}/attempt", json={"answer": {"selected": [0]}})
first = r.json()
correct_indexes = first["solution"]["correct"]
r2 = client.post(f"{BASE}/exercises/{mcq['id']}/attempt", json={"answer": {"selected": correct_indexes}})
second = r2.json()
wrong = [i for i in range(4) if i not in correct_indexes][:1]
r3 = client.post(f"{BASE}/exercises/{mcq['id']}/attempt", json={"answer": {"selected": wrong}})
third = r3.json()
check(
    "mcq-attempts",
    second["correct"] is True and third["correct"] is False,
    f"correct-answer={second} wrong-answer={third}",
)

# 7. Mark lesson complete (should award the first_lesson badge)
r = client.post(f"{BASE}/lessons/{lesson_id}/complete")
check(
    "lesson-complete",
    r.status_code == 200 and "first_lesson" in r.json().get("new_badges", []),
    r.text[:200],
)

# 7b. Badges endpoint reflects the earned badge
r = client.get(f"{BASE}/badges")
badges = r.json()
check(
    "badges-list",
    r.status_code == 200
    and any(b["key"] == "first_lesson" and b["earned"] for b in badges)
    and any(not b["earned"] for b in badges),
    r.text[:300],
)

# 8. LLM validation via open_text exercise (requires Ollama)
if open_ex:
    print(f"  open_text prompt: {open_ex['data']['prompt']['en'][:120]}")
    r = client.post(
        f"{BASE}/exercises/{open_ex['id']}/attempt",
        json={"answer": {"text": (
            "A hash map stores key-value pairs using a hash function to map keys to bucket "
            "indexes, giving O(1) average lookups; collisions are handled with chaining or "
            "open addressing, and the table resizes when the load factor grows."
        )}},
    )
    ok = r.status_code == 200 and "correct" in r.json()
    check("llm-validation", ok, r.text[:300])
    if ok:
        print(f"  llm correct={r.json()['correct']} feedback: {str(r.json().get('feedback'))[:200]}")
else:
    check("llm-validation", False, "no open_text exercise found in course")

# 9. Study heartbeat + today
r = client.post(f"{BASE}/study/heartbeat", json={"seconds": 60})
check("study-heartbeat", r.status_code == 200, r.text[:200])
r = client.get(f"{BASE}/study/today")
check("study-today", r.status_code == 200 and r.json()["seconds"] >= 60, r.text[:200])

# 10. Course test: answer MCQs (half deliberately with option 0) and open questions
r = client.get(f"{BASE}/courses/cs-fundamentals/test")
questions = r.json()
check("test-questions", r.status_code == 200 and len(questions) >= 10, f"got {len(questions)}")
answers = {}
for q in questions:
    if q["type"] == "multiple_choice":
        answers[str(q["id"])] = {"selected": [0]}
    else:
        answers[str(q["id"])] = {"text": (
            "Big-O notation describes the asymptotic growth of time or space as input size "
            "grows: O(1) constant, O(log n) logarithmic, O(n) linear, O(n^2) quadratic. It "
            "lets engineers compare algorithms independently of hardware."
        )}
r = client.post(f"{BASE}/courses/cs-fundamentals/test/attempt", json={"answers": answers})
res = r.json()
check(
    "test-submit",
    r.status_code == 200 and "score" in res and res["total"] == len(questions),
    r.text[:300],
)
if r.status_code == 200:
    print(f"  test score: {res['score']}% ({res['correct']}/{res['total']})")

# 11. Analytics
r = client.get(f"{BASE}/analytics/summary")
summary = r.json()
check(
    "analytics",
    r.status_code == 200
    and summary["total_attempts"] >= 3
    and summary["total_study_seconds"] >= 60
    and any(c["attempts"] > 0 for c in summary["by_course"]),
    r.text[:400],
)

# 12. AI status + tutor
r = client.get(f"{BASE}/ai/status")
check("ai-status", r.status_code == 200, r.text[:200])
if r.json().get("available"):
    r = client.post(f"{BASE}/ai/tutor", json={
        "question": "Explain briefly what a hash map is.",
        "lesson_id": lesson_id,
    })
    check("ai-tutor", r.status_code == 200 and r.json().get("answer"), r.text[:300])
    if r.status_code == 200:
        print(f"  tutor reply: {str(r.json().get('answer'))[:150]}")
else:
    print("  Ollama not available, skipping tutor test")

print()
print(f"{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
