from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://interview:interview@localhost:5433/interview_prep"
    mongo_url: str = "mongodb://localhost:27018"
    mongo_db: str = "interview_prep"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3-vl:8b-instruct"
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
