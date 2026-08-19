import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db, get_vector_db, get_settings
from config.settings import Settings
from storage.db_models import Base

@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment(tmp_path_factory):
    """Ensure all tests run with isolated storage directories by default."""
    test_dir = tmp_path_factory.mktemp("cip_test_storage")
    test_db = str(test_dir / "cip_test.db")
    test_cas = str(test_dir / "documents")
    test_vector = str(test_dir / "lancedb")

    os.environ["CIP_DB_PATH"] = test_db
    os.environ["CIP_CAS_ROOT_DIR"] = test_cas
    os.environ["CIP_VECTOR_DB_PATH"] = test_vector

    yield

    os.environ.pop("CIP_DB_PATH", None)
    os.environ.pop("CIP_CAS_ROOT_DIR", None)
    os.environ.pop("CIP_VECTOR_DB_PATH", None)

class MockVectorStore:
    """Mock LanceDB vector store connection for isolated test runs."""
    def __init__(self) -> None:
        self.deleted_candidate_ids = []
        self.tables = {}

    def delete_candidate_vectors(self, candidate_id: str) -> None:
        self.deleted_candidate_ids.append(candidate_id)

    def list_tables(self):
        return list(self.tables.keys())

    def table_names(self):
        return list(self.tables.keys())

    def open_table(self, name: str):
        return self.tables.get(name, self._create_mock_table(name))

    def create_table(self, name: str, *args, **kwargs):
        return self.tables.setdefault(name, self._create_mock_table(name))

    def _create_mock_table(self, name: str):
        class MockTable:
            def __init__(self):
                self.records = []
            def add(self, records):
                self.records.extend(records)
            def delete(self, *args, **kwargs):
                pass
            def search(self, *args, **kwargs):
                class MockSearch:
                    def limit(self, n):
                        return self
                    def where(self, cond):
                        return self
                    def to_list(self):
                        return []
                return MockSearch()
        return MockTable()

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
def test_settings(tmp_path):
    """Provides isolated settings for tests."""
    return Settings(
        db_path=":memory:",
        cas_root_dir=str(tmp_path / "cas"),
        vector_db_path=str(tmp_path / "vector")
    )

@pytest.fixture
def client(db_engine, mock_vector_db, test_settings):
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

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_vector_db] = override_get_vector_db
    app.dependency_overrides[get_settings] = override_get_settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
