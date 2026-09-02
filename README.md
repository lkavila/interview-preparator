# Interview Preparator

A digital course platform to prepare for software engineering interviews. Full-stack app with React + FastAPI + PostgreSQL + MongoDB + Ollama (local LLM).

## Features

- 20 seeded courses covering CS fundamentals, distributed systems, PostgreSQL, Redis, message brokers, Kubernetes, AWS, Python/Django, networking, observability, React, Node.js, TypeScript, Go, database selection, behavioural interviews, the AWS Solutions Architect Associate (SAA-C03) certification and Wonderlic test preparation.
- Each lesson answers a real interview question: short definition, real-world examples and 3 interactive exercises.
- Exercise types: multiple choice, matching (connect concepts), ordering/flow building, table builder, real SQL (executed in-browser with PGlite), code writing and open answers validated by a local LLM.
- Final test per course (10-15 questions, mostly multiple choice).
- Optional practice exams per course: several named, timed mock exams with their own length and pass mark (the AWS SAA-C03 course ships six, from 10 to 50 questions, 165 questions in total), with the explanation of each answer revealed on submit.
- Question-bank exams: an exam can declare `sampling` and draw a fresh, category-balanced subset from a larger bank on every attempt, so it stays repeatable (the Wonderlic mock draws 50 of 249, balanced 15 verbal / 20 numeric / 15 logic, so two attempts in a row share only about a fifth of their questions).
- Server-side exam clock: timed exams are started through `/start`, which records the deadline and the exact questions served. Reloading resumes the same attempt without refunding time, and a submission past the deadline (plus a 5-second grace for latency) is still graded but flagged `timed_out` and excluded from best scores and badges.
- Questions can carry an inline SVG figure (`svg_content`) for spatial reasoning; figures are validated when seeded and sanitised again against an allow-list before rendering. The Wonderlic bank ships thirteen figure families, including corner matching on a folded cube (derived from an actual folding model, not drawn by eye), trend graphs, piece assembly and four figure-sequence types: a rotating sector, a square travelling a route through a grid, a matrix whose third column is the first two overlaid, and a shape gaining a nested copy each step.
- Questions may have several correct answers (`data.multiple` with several indexes in `solution.correct`), which the exam UI renders as checkboxes — the real Wonderlic asks things like "which THREE of these words mean the same".
- User accounts (JWT) with progress tracking, per-day study timer and analytics (strengths/weaknesses by topic).
- Bilingual UI and content (English/Spanish), dark/light theme with CSS variable tokens + Tailwind.
- AI tutor and answer validation powered by Ollama (`qwen3-vl:8b-instruct` by default).
- LLM-enriched lessons: when a lesson is opened, the local LLM generates fun facts, real interview questions and a quick quiz for it (cached in MongoDB, with static fallback content if Ollama is offline).
- Gamified, DB-configurable lesson components (`lesson_components` table controls which components each lesson shows): `QuizCard` (score + streak), `InterviewQuestionCard`, `FunFactCarousel`, `ConceptDiagram` (Mermaid/Recharts), `ImageGallery` (Wikimedia images with attribution).
- Achievement system: badges awarded server-side for lessons, exercises, test scores and study streaks (`user_badges` table), with toast notifications and a badge grid on the Analytics page.

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React 18, TypeScript, Vite, Redux Toolkit + RTK Query, Tailwind CSS v4, react-i18next, recharts, CodeMirror 6, dnd-kit, PGlite |
| Backend   | FastAPI, SQLAlchemy 2, Alembic, PyJWT, bcrypt, pymongo, httpx |
| Databases | PostgreSQL 16 (structured), MongoDB 7 (LLM interactions / unstructured) |
| LLM       | Ollama running locally (`http://localhost:11434`) |

## Getting started

### 1. Databases

```bash
docker compose up -d
```

PostgreSQL listens on `localhost:5433`, MongoDB on `localhost:27018`.

### 2. Backend

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed        # loads all course content
uvicorn app.main:app --reload --port 8000

start server: .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### 4. Ollama

Install [Ollama](https://ollama.com) and pull the model:

```bash
ollama pull qwen3-vl:8b-instruct
```

The app works without Ollama, but LLM-validated exercises, the AI tutor and exercise generation will show a friendly "AI unavailable" message.

## Adding a new course (e.g. React, TypeScript)

Content is 100% data-driven. To add a course you only add a JSON file — no code changes needed:

1. Copy `backend/seeds/TEMPLATE.json` to `backend/seeds/courses/<order>-<slug>.json`.
2. Fill in course metadata, lessons and the final test. Every text field is bilingual (`{"en": ..., "es": ...}`). Each lesson needs 2-4 exercises (3 recommended) and multiple-choice answers should not always be the first option.
3. Supported exercise types:
   - `multiple_choice` — options + correct index(es). Static validation.
   - `matching` — pairs of concepts to connect. Static validation.
   - `ordering` — boxes to arrange in the right order (also used for architecture flows). Static validation.
   - `table_builder` — define table columns (name/type). Static validation.
   - `sql` — real SQL executed in the browser via PGlite; result rows are compared with the expected result. Static validation.
   - `code` — write code in CodeMirror; validated by the local LLM against criteria.
   - `open_text` — free text answer; validated by the local LLM against criteria.
4. (Optional) Add practice exams. Besides `test`, a course can define an `exams` array; each entry becomes a separate timed exam on the course page:

```json
"exams": [
  {
    "slug": "full-mock-50",
    "title": { "en": "Full mock exam · 50 questions", "es": "Simulacro completo · 50 preguntas" },
    "description": { "en": "50 questions in 100 minutes.", "es": "50 preguntas en 100 minutos." },
    "pass_score": 72,
    "time_limit_minutes": 100,
    "questions": [ /* same shape as `test` entries; put `explanation` inside `solution` so it is only revealed after submitting */ ]
  }
]
```

   A course needs either a `test` (10-15 questions) or at least one exam. Exams are served by `GET /api/courses/{slug}/exams`, `GET /api/courses/{slug}/exams/{exam_slug}` and `POST /api/courses/{slug}/exams/{exam_slug}/attempt`, and scores are tracked per exam.

   To turn an exam into a **question bank**, add `sampling` and give every question a `category`:

```json
"sampling": { "VERBAL": 15, "NUMERIC": 20, "LOGIC": 15 }
```

   Each attempt then draws that many questions per category at random, and the UI switches to one question at a time with a server-kept clock (`POST .../start`, resumable via `GET .../exams/sessions/{token}`). A category whose bank is thinner than its quota serves what it has and the seeder prints a warning, so a bank can grow in batches. Spatial questions may add `"svg_content": "<svg viewBox=...>...</svg>"` — use `currentColor` for strokes so the figure works in both themes, and no scripts, event handlers or external references (the seeder rejects them).

5. Run the seeder (idempotent — safe to re-run, upserts by slug):

```bash
cd backend
python -m app.seed
```

The new course appears automatically in the dashboard. The seeder validates the JSON with Pydantic and reports clear errors if the schema is wrong.

6. (Optional) Assign the interactive lesson components (quiz, interview questions, fun facts, image galleries, concept diagrams) to the new lessons:

```bash
python -m app.assign_components
```

You can also generate a draft course with the local LLM from the app (AI panel) or via `POST /api/ai/generate-course-draft`.

### Useful content scripts

```bash
python scripts/check_one.py seeds/courses/13-react.json   # validate a single seed file
python scripts/shuffle_mcq.py                             # rebalance multiple-choice correct indexes
python scripts/fetch_images.py                            # download illustrative images from Wikimedia Commons
python scripts/e2e_smoke.py                               # end-to-end API smoke test (backend must be running)
```

## Project structure

```
frontend/          React + TS (Vite)
backend/
  app/api/         routers: auth, courses, exercises, tests, study, analytics, ai, badges
  app/models.py    SQLAlchemy models (incl. lesson_components, user_badges)
  app/services/    ollama, validation, analytics, enrichment, badges
  app/assign_components.py  populate lesson_components per lesson
  scripts/         content utilities (validation, MCQ shuffle, image fetch, e2e smoke)
  seeds/courses/   one JSON file per course (bilingual content)
  seeds/TEMPLATE.json
  static/images/   illustrative images (Wikimedia Commons, with attribution manifest)
docker-compose.yml
```
