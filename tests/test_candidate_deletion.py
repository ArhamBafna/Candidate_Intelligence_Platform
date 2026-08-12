import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db, get_vector_db
from storage.db_models import Base, Candidate, ResumeVersion, CandidateTimelineEvent, CandidateClaim

class MockVectorStore:
    def __init__(self) -> None:
        self.deleted_candidate_ids = []

    def delete_candidate_vectors(self, candidate_id: str) -> None:
        self.deleted_candidate_ids.append(candidate_id)

@pytest.fixture
def mock_vector_db() -> MockVectorStore:
    return MockVectorStore()

@pytest.fixture
def db_engine():
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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def client(db_engine, mock_vector_db):
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

def test_delete_candidate_success(client: TestClient, db_session: Session, mock_vector_db: MockVectorStore) -> None:
    c_id = str(uuid.uuid4())
    candidate = Candidate(
        id=c_id,
        first_name="Delete",
        last_name="Me",
        primary_email="delete.me@example.com"
    )
    db_session.add(candidate)
    
    timeline = CandidateTimelineEvent(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        event_type="PROFILE_CREATED",
        title="Created",
        created_by="System"
    )
    db_session.add(timeline)
    
    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash="hash123",
        original_filename="resume.pdf",
        file_type="pdf",
        raw_text="Sample text",
        layout_metadata={}
    )
    db_session.add(rv)
    db_session.commit()

    # Populate FTS
    db_session.execute(
        text("INSERT INTO candidate_fts (candidate_id, full_name) VALUES (:cid, :fname)"),
        {"cid": c_id, "fname": "Delete Me"}
    )
    db_session.commit()

    response = client.delete(f"/candidates/{c_id}")
    assert response.status_code == 204

    # Verify candidate and related items deleted in DB
    deleted_c = db_session.query(Candidate).filter(Candidate.id == c_id).first()
    assert deleted_c is None

    deleted_rv = db_session.query(ResumeVersion).filter(ResumeVersion.candidate_id == c_id).all()
    assert len(deleted_rv) == 0

    deleted_timeline = db_session.query(CandidateTimelineEvent).filter(CandidateTimelineEvent.candidate_id == c_id).all()
    assert len(deleted_timeline) == 0

    # Verify FTS deleted
    fts_rows = db_session.execute(
        text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": c_id}
    ).fetchall()
    assert len(fts_rows) == 0

    # Verify vector store delete called
    assert c_id in mock_vector_db.deleted_candidate_ids

def test_delete_candidate_not_found(client: TestClient) -> None:
    response = client.delete("/candidates/non-existent-id")
    assert response.status_code == 404
