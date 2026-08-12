from functools import lru_cache

from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@lru_cache
def get_mongo():
    client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=3000)
    return client[settings.mongo_db]
