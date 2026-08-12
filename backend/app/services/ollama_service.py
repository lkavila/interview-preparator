"""Client for the local Ollama REST API.

Used for: validating open/code answers, generating practice exercises and the
per-lesson AI tutor. All interactions are logged to MongoDB.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.database import get_mongo

settings = get_settings()


class OllamaUnavailable(Exception):
    pass


def _log_interaction(kind: str, prompt: str, response: str | None, user_id: int | None) -> None:
    try:
        get_mongo()["llm_interactions"].insert_one(
            {
                "kind": kind,
                "model": settings.ollama_model,
                "prompt": prompt,
                "response": response,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception:
        # Mongo being down should never break the request path
        pass


def _chat(system: str, user: str, kind: str, user_id: int | None = None) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{settings.ollama_url}/api/chat", json=payload)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
    except (httpx.HTTPError, KeyError) as e:
        _log_interaction(kind, user, f"ERROR: {e}", user_id)
        raise OllamaUnavailable(str(e))
    _log_interaction(kind, user, content, user_id)
    return content


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from an LLM response."""
    # Strip <think> blocks and markdown fences
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    for candidate in (match.group(0),):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def is_available() -> bool:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{settings.ollama_url}/api/tags")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def validate_answer(
    prompt: str,
    answer: str,
    criteria: str,
    reference: str | None,
    language: str,
    user_id: int | None = None,
) -> tuple[bool, str]:
    """Grade an open-text or code answer against grading criteria."""
    lang_name = "Spanish" if language == "es" else "English"
    system = (
        "You are a strict but fair software engineering interview grader. "
        "You evaluate a candidate's answer against grading criteria. "
        'Respond ONLY with a JSON object: {"correct": true|false, "feedback": "..."}. '
        f"Write the feedback in {lang_name}, 2-3 sentences max: say what was right, "
        "what was missing or wrong, and one concrete improvement. "
        "Mark correct=true if the answer covers the essential points of the criteria, "
        "even if wording differs or it has minor omissions."
    )
    user = f"QUESTION:\n{prompt}\n\nGRADING CRITERIA:\n{criteria}\n"
    if reference:
        user += f"\nREFERENCE ANSWER (for your eyes only):\n{reference}\n"
    user += f"\nCANDIDATE ANSWER:\n{answer}"

    content = _chat(system, user, kind="validate_answer", user_id=user_id)
    parsed = _extract_json(content)
    if parsed is None or "correct" not in parsed:
        raise OllamaUnavailable("model returned unparseable grading response")
    return bool(parsed["correct"]), str(parsed.get("feedback", ""))


def generate_model_answer(
    prompt: str,
    criteria: str,
    reference: str | None,
    exercise_type: str,
    code_language: str | None,
    language: str,
    user_id: int | None = None,
) -> str:
    """Produce a model correct answer for an LLM-validated exercise (code/open_text)."""
    lang_name = "Spanish" if language == "es" else "English"
    if exercise_type == "code":
        style = (
            f"Provide a complete, idiomatic solution in {code_language or 'the requested language'} "
            "inside a fenced markdown code block, followed by a brief 2-3 sentence explanation."
        )
    else:
        style = (
            "Provide a model answer of 3-6 sentences — the kind of answer that would "
            "impress an interviewer. Cover every point in the grading criteria."
        )
    system = (
        "You are a senior software engineering interview coach. A student asked to see "
        f"the correct answer to a practice exercise. {style} "
        f"Write in {lang_name}; keep code identifiers and technology names in English. "
        "Use markdown. Respond with the answer only, no preamble."
    )
    user = f"EXERCISE:\n{prompt}\n\nGRADING CRITERIA (what a correct answer must cover):\n{criteria}\n"
    if reference:
        user += f"\nREFERENCE NOTES:\n{reference}\n"
    content = _chat(system, user, kind="model_answer", user_id=user_id)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not content:
        raise OllamaUnavailable("model returned an empty answer")
    return content


def tutor_answer(question: str, context: str, language: str, user_id: int | None = None) -> str:
    lang_name = "Spanish" if language == "es" else "English"
    system = (
        "You are a concise senior software engineering interview coach. "
        f"Answer in {lang_name}. Be practical and interview-oriented: explain the concept "
        "briefly, give a short real-world example, and mention what interviewers look for. "
        "Keep answers under 250 words. Use markdown."
    )
    user = question if not context else f"LESSON CONTEXT:\n{context}\n\nSTUDENT QUESTION:\n{question}"
    return _chat(system, user, kind="tutor", user_id=user_id)


def generate_exercise(topic: str, language: str, user_id: int | None = None) -> dict[str, Any]:
    """Generate an extra multiple-choice practice question for a topic."""
    system = (
        "You generate software engineering interview practice questions. "
        "Respond ONLY with a JSON object with this exact shape: "
        '{"prompt": {"en": "...", "es": "..."}, '
        '"options": [{"en": "...", "es": "..."}, ... 4 options], '
        '"correct": 0, "explanation": {"en": "...", "es": "..."}}. '
        "The question must be realistic for a senior software engineering interview."
    )
    user = f"Topic: {topic}. Generate one multiple-choice question with exactly 4 options."
    content = _chat(system, user, kind="generate_exercise", user_id=user_id)
    parsed = _extract_json(content)
    if not parsed or "prompt" not in parsed or "options" not in parsed or "correct" not in parsed:
        raise OllamaUnavailable("model returned unparseable exercise")
    generated = {
        "prompt": parsed["prompt"],
        "options": parsed["options"],
        "correct": int(parsed["correct"]),
        "explanation": parsed.get("explanation", {"en": "", "es": ""}),
    }
    try:
        get_mongo()["generated_exercises"].insert_one(
            {**json.loads(json.dumps(generated)), "topic": topic, "user_id": user_id,
             "created_at": datetime.now(timezone.utc)}
        )
    except Exception:
        pass
    return generated


def generate_lesson_enrichment(
    topic: str,
    definition: str,
    language: str,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Generate dynamic lesson enrichment: fun facts, real interview questions and a
    trivia quiz. Returns JSON with the exact schema used by the lesson components."""
    lang_name = "Spanish" if language == "es" else "English"
    system = (
        "You create engaging supplementary content for a software engineering "
        "interview prep lesson. Respond ONLY with valid JSON, no markdown fences, "
        "matching EXACTLY this schema: "
        '{"fun_facts": ["...", "...", "..."], '
        '"interview_questions": [{"question": "...", "suggested_answer": "..."}, ...], '
        '"quiz": [{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0}, ...]}. '
        "Rules: 3 fun_facts (surprising, true, concrete facts with numbers or history when possible); "
        "2 interview_questions asked at real companies about this topic, each with a strong "
        "suggested_answer of 3-5 sentences; 3 quiz questions, each with exactly 4 options and "
        "one correct answer whose correct_index you MUST vary (not always 0). "
        f"Write ALL text in {lang_name}. Keep code identifiers and technology names in English."
    )
    user = f"LESSON TOPIC: {topic}\n\nLESSON CONTENT (for grounding):\n{definition[:3000]}"
    content = _chat(system, user, kind="lesson_enrichment", user_id=user_id)
    parsed = _extract_json(content)
    if not parsed:
        raise OllamaUnavailable("model returned unparseable enrichment")

    fun_facts = [str(f) for f in parsed.get("fun_facts", []) if str(f).strip()][:5]
    interview_questions = [
        {"question": str(q.get("question", "")), "suggested_answer": str(q.get("suggested_answer", ""))}
        for q in parsed.get("interview_questions", [])
        if isinstance(q, dict) and q.get("question") and q.get("suggested_answer")
    ][:3]
    quiz = []
    for item in parsed.get("quiz", []):
        if not isinstance(item, dict):
            continue
        options = [str(o) for o in item.get("options", [])]
        try:
            idx = int(item.get("correct_index", -1))
        except (TypeError, ValueError):
            continue
        if item.get("question") and len(options) == 4 and 0 <= idx < 4:
            quiz.append({"question": str(item["question"]), "options": options, "correct_index": idx})
    quiz = quiz[:4]

    if not fun_facts and not interview_questions and not quiz:
        raise OllamaUnavailable("enrichment response had no usable content")
    return {"fun_facts": fun_facts, "interview_questions": interview_questions, "quiz": quiz}


def generate_course_draft(topic: str, questions: list[str], user_id: int | None = None) -> dict[str, Any]:
    """Generate a draft course JSON (seed schema) for a new topic. The draft is
    meant to be reviewed by a human, saved into seeds/courses/ and seeded."""
    system = (
        "You generate draft course content for a software engineering interview prep app. "
        "Respond ONLY with a JSON object following this schema: "
        '{"slug": "kebab-case", "order": 99, "icon": "book", '
        '"title": {"en": "...", "es": "..."}, "description": {"en": "...", "es": "..."}, '
        '"lessons": [{"slug": "kebab-case", "question": {"en","es"}, "definition": {"en","es"}, '
        '"examples": [{"en","es"}], "exercises": [ 2 exercises: multiple_choice with '
        '{"data": {"prompt": {en,es}, "options": [4 x {en,es}]}, "solution": {"correct": [i]}, '
        '"type": "multiple_choice", "validation_mode": "static"} or open_text with '
        '{"type": "open_text", "validation_mode": "llm", "data": {"prompt": {en,es}}, '
        '"solution": {"criteria": {en,es}, "reference": "..."}} ]}]}. '
        "All texts bilingual English/Spanish. Definitions short (2-3 paragraphs of markdown)."
    )
    q_list = "\n".join(f"- {q}" for q in questions[:6])
    user = (
        f"Topic: {topic}\nCreate a draft with {min(len(questions), 6) or 3} short lessons "
        f"answering these interview questions:\n{q_list or '(choose 3 typical questions)'}"
    )
    content = _chat(system, user, kind="generate_course_draft", user_id=user_id)
    parsed = _extract_json(content)
    if not parsed or "lessons" not in parsed:
        raise OllamaUnavailable("model returned unparseable course draft")
    return parsed
