# Interview Preparator

A digital course platform to prepare for software engineering interviews. Full-stack app with React + FastAPI + PostgreSQL + MongoDB + Ollama (local LLM).

## Features

- 15 seeded courses covering CS fundamentals, distributed systems, PostgreSQL, Redis, message brokers, Kubernetes, AWS, Python/Django, networking, observability, React, Node.js and TypeScript.
- Each lesson answers a real interview question: short definition, real-world examples and 3 interactive exercises.
- Exercise types: multiple choice, matching (connect concepts), ordering/flow building, table builder, real SQL (executed in-browser with PGlite), code writing and open answers validated by a local LLM.
- Final test per course (10-15 questions, mostly multiple choice).
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
4. Run the seeder (idempotent — safe to re-run, upserts by slug):

```bash
cd backend
python -m app.seed
```

The new course appears automatically in the dashboard. The seeder validates the JSON with Pydantic and reports clear errors if the schema is wrong.

5. (Optional) Assign the interactive lesson components (quiz, interview questions, fun facts, image galleries, concept diagrams) to the new lessons:

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
