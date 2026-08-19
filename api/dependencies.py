from typing import Generator
from functools import lru_cache
from sqlalchemy.orm import Session, sessionmaker
from config.settings import Settings
from config.database import get_engine
from storage.vector_store import get_lancedb_connection

@lru_cache(maxsize=8)
def _get_sessionmaker(db_path: str):
    engine = get_engine(f"sqlite:///{db_path}")
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_settings() -> Settings:
    return Settings()

def get_db() -> Generator[Session, None, None]:
    settings = get_settings()
    SessionLocal = _get_sessionmaker(settings.db_path)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_vector_db():
    settings = get_settings()
    return get_lancedb_connection(settings.vector_db_path)
