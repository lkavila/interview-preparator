import re
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------------------------------------------------------------------------
# Auth / users
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    language: Literal["en", "es"] = "es"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    language: str
    theme: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PreferencesUpdate(BaseModel):
    language: Literal["en", "es"] | None = None
    theme: Literal["dark", "light"] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Courses / lessons / exercises (API output)
# ---------------------------------------------------------------------------


class ExerciseOut(BaseModel):
    id: int
    order_index: int
    type: str
    validation_mode: str
    data: dict[str, Any]

    model_config = {"from_attributes": True}


class LessonSummary(BaseModel):
    id: int
    slug: str
    order_index: int
    question: dict[str, Any]
    completed: bool = False


class LessonComponentOut(BaseModel):
    id: int
    component_type: str
    order_index: int
    config: dict[str, Any]

    model_config = {"from_attributes": True}


class LessonOut(BaseModel):
    id: int
    slug: str
    order_index: int
    course_slug: str
    course_title: dict[str, Any]
    content: dict[str, Any]
    exercises: list[ExerciseOut]
    components: list[LessonComponentOut] = []
    completed: bool
    prev_lesson_id: int | None = None
    next_lesson_id: int | None = None


class EnrichmentInterviewQuestion(BaseModel):
    question: str
    suggested_answer: str


class EnrichmentQuizItem(BaseModel):
    question: str
    options: list[str]
    correct_index: int


class EnrichmentResponse(BaseModel):
    source: str  # "llm" | "fallback"
    fun_facts: list[str]
    interview_questions: list[EnrichmentInterviewQuestion]
    quiz: list[EnrichmentQuizItem]


class BadgeOut(BaseModel):
    key: str
    icon: str
    name: dict[str, Any]
    description: dict[str, Any]
    earned: bool
    earned_at: datetime | None = None


class CourseSummary(BaseModel):
    id: int
    slug: str
    order_index: int
    icon: str
    title: dict[str, Any]
    description: dict[str, Any]
    lesson_count: int
    completed_lessons: int
    best_test_score: float | None = None


class ExamSummary(BaseModel):
    slug: str
    order_index: int
    title: dict[str, Any]
    description: dict[str, Any]
    # For a sampled exam this is the size of the draw, not the size of the bank.
    question_count: int
    pass_score: float
    time_limit_minutes: int | None = None
    best_score: float | None = None
    attempts: int = 0
    # Set only on question-bank exams: the per-category quotas and the pool size.
    sampling: dict[str, int] | None = None
    bank_size: int | None = None


class CourseDetail(CourseSummary):
    lessons: list[LessonSummary]
    test_question_count: int
    exams: list[ExamSummary] = []


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------


class AttemptRequest(BaseModel):
    answer: dict[str, Any]


class AttemptResponse(BaseModel):
    correct: bool
    feedback: str | None = None
    solution: dict[str, Any] | None = None
    new_badges: list[str] = []


class SolutionRevealResponse(BaseModel):
    answer: str
    source: str  # "llm" | "reference"


class TestQuestionOut(BaseModel):
    id: int
    order_index: int
    type: str
    category: str | None = None
    data: dict[str, Any]
    svg_content: str | None = None

    model_config = {"from_attributes": True}


class TestSubmission(BaseModel):
    answers: dict[int, dict[str, Any]]  # question_id -> answer payload
    # Present for timed exams started through /start; omitted by the untimed
    # flows, which keep grading the exam's full question set.
    session_token: str | None = None


class TestQuestionResult(BaseModel):
    question_id: int
    correct: bool
    feedback: str | None = None
    solution: dict[str, Any] | None = None


class TestResult(BaseModel):
    score: float
    correct: int
    total: int
    pass_score: float = 70.0
    results: list[TestQuestionResult]
    new_badges: list[str] = []
    # Submitted past the deadline: graded and stored, but it does not count.
    timed_out: bool = False


class ExamSessionOut(BaseModel):
    """A started timed attempt: the questions drawn and the server's deadline."""

    session_token: str
    # The client syncs its countdown to these instead of trusting its own clock.
    server_time: datetime
    expires_at: datetime
    seconds_remaining: int
    time_limit_minutes: int | None = None
    pass_score: float = 70.0
    questions: list[TestQuestionOut]


# ---------------------------------------------------------------------------
# Study / analytics
# ---------------------------------------------------------------------------


class HeartbeatRequest(BaseModel):
    seconds: int = Field(gt=0, le=300)


class StudyDay(BaseModel):
    day: date
    seconds: int
    new_badges: list[str] = []


class CourseAccuracy(BaseModel):
    course_slug: str
    course_title: dict[str, Any]
    attempts: int
    correct: int
    accuracy: float


class LessonAccuracy(BaseModel):
    lesson_id: int
    lesson_slug: str
    question: dict[str, Any]
    course_slug: str
    attempts: int
    correct: int
    accuracy: float


class AnalyticsSummary(BaseModel):
    total_attempts: int
    total_correct: int
    overall_accuracy: float
    total_study_seconds: int
    study_days: list[StudyDay]
    by_course: list[CourseAccuracy]
    weakest_lessons: list[LessonAccuracy]
    strongest_lessons: list[LessonAccuracy]


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


class TutorRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    lesson_id: int | None = None


class TutorResponse(BaseModel):
    answer: str


class GenerateExerciseRequest(BaseModel):
    course_slug: str
    topic: str | None = None


# ---------------------------------------------------------------------------
# Seed content schema (validates seeds/courses/*.json)
# ---------------------------------------------------------------------------

Bilingual = dict[Literal["en", "es"], str]

EXERCISE_TYPES = {
    "multiple_choice",
    "matching",
    "ordering",
    "table_builder",
    "sql",
    "code",
    "open_text",
}


def _require_bilingual(value: dict, where: str) -> dict:
    if not isinstance(value, dict) or "en" not in value or "es" not in value:
        raise ValueError(f"{where}: expected bilingual object with 'en' and 'es' keys")
    return value


QUESTION_CATEGORIES = ("VERBAL", "NUMERIC", "LOGIC")

# Figures are first-party content, but they end up in the DOM, so the dangerous
# constructs are rejected at authoring time — the cheapest place to catch them.
# The client sanitises again on the way in.
_SVG_FORBIDDEN = (
    (re.compile(r"<\s*script", re.I), "<script> is not allowed in svg_content"),
    (re.compile(r"<\s*foreignObject", re.I), "<foreignObject> is not allowed in svg_content"),
    (re.compile(r"\son\w+\s*=", re.I), "inline event handlers are not allowed in svg_content"),
    (re.compile(r"javascript\s*:", re.I), "javascript: URLs are not allowed in svg_content"),
    (re.compile(r"(href|src)\s*=\s*[\"']\s*(https?:)?//", re.I),
     "external references are not allowed in svg_content"),
)


def _check_svg(value: str) -> str:
    if "<svg" not in value.lower():
        raise ValueError("svg_content must contain an <svg> root element")
    if "viewBox" not in value:
        raise ValueError("svg_content needs a viewBox so the figure scales on mobile")
    for pattern, message in _SVG_FORBIDDEN:
        if pattern.search(value):
            raise ValueError(message)
    return value


class SeedExercise(BaseModel):
    type: str
    validation_mode: Literal["static", "llm"] = "static"
    data: dict[str, Any]
    solution: dict[str, Any]

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        if v not in EXERCISE_TYPES:
            raise ValueError(f"unknown exercise type '{v}'. Supported: {sorted(EXERCISE_TYPES)}")
        return v

    @field_validator("data")
    @classmethod
    def check_prompt(cls, v: dict) -> dict:
        if "prompt" not in v:
            raise ValueError("exercise data must include a 'prompt'")
        _require_bilingual(v["prompt"], "exercise prompt")
        return v

    def model_post_init(self, __context: Any) -> None:
        t = self.type
        sol = self.solution
        if t == "multiple_choice":
            if "options" not in self.data or len(self.data["options"]) < 2:
                raise ValueError("multiple_choice needs data.options with >= 2 options")
            if "correct" not in sol or not isinstance(sol["correct"], list) or not sol["correct"]:
                raise ValueError("multiple_choice needs solution.correct as a non-empty list of indexes")
            n = len(self.data["options"])
            for idx in sol["correct"]:
                if not isinstance(idx, int) or idx < 0 or idx >= n:
                    raise ValueError(f"multiple_choice solution.correct index {idx} out of range (0..{n - 1})")
            if len(sol["correct"]) > 1 and not self.data.get("multiple"):
                raise ValueError("multiple_choice with several correct answers must set data.multiple = true")
        elif t == "matching":
            if "left" not in self.data or "right" not in self.data:
                raise ValueError("matching needs data.left and data.right")
            if "pairs" not in sol:
                raise ValueError("matching needs solution.pairs")
            left_ids = {str(i["id"]) for i in self.data["left"]}
            right_ids = {str(i["id"]) for i in self.data["right"]}
            pairs = {str(k): str(v) for k, v in sol["pairs"].items()}
            if set(pairs.keys()) != left_ids:
                raise ValueError("matching solution.pairs keys must match data.left ids exactly")
            if not set(pairs.values()).issubset(right_ids):
                raise ValueError("matching solution.pairs values must be data.right ids")
            if len(set(pairs.values())) != len(pairs):
                raise ValueError("matching solution.pairs must not reuse a right id")
        elif t == "ordering":
            if "items" not in self.data or len(self.data["items"]) < 2:
                raise ValueError("ordering needs data.items with >= 2 items")
            if "order" not in sol:
                raise ValueError("ordering needs solution.order")
            item_ids = sorted(str(i["id"]) for i in self.data["items"])
            order_ids = sorted(str(i) for i in sol["order"])
            if item_ids != order_ids:
                raise ValueError("ordering solution.order must contain exactly the ids in data.items")
        elif t == "table_builder":
            if "columns" not in sol or not sol["columns"]:
                raise ValueError("table_builder needs solution.columns")
            for col in sol["columns"]:
                if "name" not in col or "type" not in col:
                    raise ValueError("table_builder solution.columns entries need 'name' and 'type'")
        elif t == "sql":
            if "verification_query" not in self.data:
                raise ValueError("sql needs data.verification_query")
            if "expected_rows" not in sol or not isinstance(sol["expected_rows"], list):
                raise ValueError("sql needs solution.expected_rows as a list of rows")
        elif t in ("code", "open_text"):
            if self.validation_mode != "llm":
                raise ValueError(f"{t} exercises must use validation_mode 'llm'")
            if "criteria" not in sol:
                raise ValueError(f"{t} needs solution.criteria (bilingual grading criteria)")


class SeedLesson(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    question: dict[str, Any]
    definition: dict[str, Any]
    examples: list[dict[str, Any]] = Field(min_length=1)
    exercises: list[SeedExercise] = Field(min_length=2, max_length=4)

    @field_validator("question", "definition")
    @classmethod
    def check_bilingual(cls, v: dict) -> dict:
        return _require_bilingual(v, "lesson field")


class SeedTestQuestion(BaseModel):
    type: Literal["multiple_choice", "open_text"]
    validation_mode: Literal["static", "llm"] = "static"
    # Required on the questions of a sampled exam; ignored elsewhere.
    category: Literal["VERBAL", "NUMERIC", "LOGIC"] | None = None
    data: dict[str, Any]
    solution: dict[str, Any]
    svg_content: str | None = None

    @field_validator("svg_content")
    @classmethod
    def check_svg(cls, v: str | None) -> str | None:
        return None if v is None else _check_svg(v)

    def model_post_init(self, __context: Any) -> None:
        _require_bilingual(self.data.get("prompt", {}), "test question prompt")
        if self.type == "multiple_choice":
            if "options" not in self.data or "correct" not in self.solution:
                raise ValueError("multiple_choice test question needs options and solution.correct")
            n = len(self.data["options"])
            correct = self.solution["correct"]
            if not isinstance(correct, list) or not correct:
                raise ValueError("test question solution.correct must be a non-empty list")
            for idx in correct:
                if not isinstance(idx, int) or idx < 0 or idx >= n:
                    raise ValueError(f"test question solution.correct index {idx} out of range (0..{n - 1})")
            if len(correct) > 1 and not self.data.get("multiple"):
                raise ValueError("test question with several correct answers must set data.multiple = true")
        else:
            self.validation_mode = "llm"
            if "criteria" not in self.solution:
                raise ValueError("open_text test question needs solution.criteria")


class SeedExam(BaseModel):
    """An extra practice exam: its own name, length and pass mark.

    With ``sampling`` set, ``questions`` is a bank and each attempt draws a
    fresh balanced subset from it instead of serving every question."""

    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    title: dict[str, Any]
    description: dict[str, Any] = Field(default_factory=lambda: {"en": "", "es": ""})
    pass_score: float = Field(default=70.0, ge=0, le=100)
    time_limit_minutes: int | None = Field(default=None, gt=0)
    # {"VERBAL": 15, "NUMERIC": 20, "LOGIC": 15} — omit for a fixed exam.
    sampling: dict[str, int] | None = None
    questions: list[SeedTestQuestion] = Field(min_length=5)

    @field_validator("title", "description")
    @classmethod
    def check_bilingual(cls, v: dict) -> dict:
        return _require_bilingual(v, "exam field")

    @field_validator("sampling")
    @classmethod
    def check_sampling(cls, v: dict[str, int] | None) -> dict[str, int] | None:
        if v is None:
            return None
        if not v:
            raise ValueError("exam sampling must name at least one category")
        for category, quota in v.items():
            if category not in QUESTION_CATEGORIES:
                raise ValueError(
                    f"unknown sampling category '{category}'. Supported: {list(QUESTION_CATEGORIES)}"
                )
            if not isinstance(quota, int) or quota <= 0:
                raise ValueError(f"sampling quota for '{category}' must be a positive integer")
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.sampling is None:
            return
        missing = [i for i, q in enumerate(self.questions) if q.category is None]
        if missing:
            raise ValueError(
                f"exam '{self.slug}' samples its bank, so every question needs a "
                f"'category' (missing at indexes {missing[:5]})"
            )
        present = {q.category for q in self.questions}
        unknown = sorted(set(self.sampling) - present)
        if unknown:
            raise ValueError(
                f"exam '{self.slug}' samples categories not present in its bank: {unknown}"
            )

    def thin_categories(self) -> list[str]:
        """Categories whose bank is smaller than the quota asked of it.

        Reported as a warning rather than an error so a bank can grow in
        batches; at runtime the draw falls back to what is available."""
        if not self.sampling:
            return []
        counts: dict[str, int] = {}
        for q in self.questions:
            if q.category is not None:
                counts[q.category] = counts.get(q.category, 0) + 1
        return [c for c, quota in self.sampling.items() if counts.get(c, 0) < quota]


class SeedCourse(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    order: int
    icon: str = "book"
    title: dict[str, Any]
    description: dict[str, Any]
    lessons: list[SeedLesson] = Field(min_length=1)
    # The classic final test. Optional only for courses that ship `exams` instead.
    test: list[SeedTestQuestion] = Field(default_factory=list)
    exams: list[SeedExam] = Field(default_factory=list)

    @field_validator("title", "description")
    @classmethod
    def check_bilingual(cls, v: dict) -> dict:
        return _require_bilingual(v, "course field")

    def model_post_init(self, __context: Any) -> None:
        if not self.test and not self.exams:
            raise ValueError("a course needs a 'test' (10-15 questions) or at least one entry in 'exams'")
        if self.test and not (10 <= len(self.test) <= 15):
            raise ValueError(f"'test' must have 10-15 questions (got {len(self.test)})")
        slugs = [e.slug for e in self.exams]
        if len(slugs) != len(set(slugs)):
            raise ValueError("duplicate exam slugs")
