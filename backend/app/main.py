from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, analytics, auth, badges, courses, exercises, study, tests
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Interview Preparator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(exercises.router)
app.include_router(tests.router)
app.include_router(tests.exams_router)
app.include_router(study.router)
app.include_router(analytics.router)
app.include_router(ai.router)
app.include_router(badges.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
