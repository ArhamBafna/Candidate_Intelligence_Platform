from typing import Generator
from sqlalchemy.orm import Session, sessionmaker
from config.settings import Settings
from config.database import get_engine
from storage.vector_store import get_lancedb_connection

_settings = Settings()
_engine = get_engine(f"sqlite:///{_settings.db_path}")
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

def get_settings() -> Settings:
    return _settings

def get_db() -> Generator[Session, None, None]:
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_vector_db():
    return get_lancedb_connection(_settings.vector_db_path)
