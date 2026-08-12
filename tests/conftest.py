import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db, get_vector_db
from storage.db_models import Base

class MockVectorStore:
    """Mock LanceDB vector store connection for isolated test runs."""
    def __init__(self) -> None:
        self.deleted_candidate_ids = []

    def delete_candidate_vectors(self, candidate_id: str) -> None:
        self.deleted_candidate_ids.append(candidate_id)

@pytest.fixture
def mock_vector_db() -> MockVectorStore:
    return MockVectorStore()

@pytest.fixture
def db_engine():
    """Provides an isolated SQLite in-memory database engine configured with FTS5 tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS candidate_fts USING fts5(
                candidate_id UNINDEXED,
                full_name,
                current_title,
                current_company,
                resume_content,
                tokenize = 'porter unicode61'
            );
        """))
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
                claim_id UNINDEXED,
                candidate_id UNINDEXED,
                claim_category,
                claim_key,
                claim_value,
                tokenize = 'porter unicode61'
            );
        """))
    yield engine

@pytest.fixture
def db_session(db_engine):
    """Provides a clean database session for tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def client(db_engine, mock_vector_db):
    """Provides a FastAPI TestClient configured with overridden database and vector dependencies."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_vector_db():
        return mock_vector_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_vector_db] = override_get_vector_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
