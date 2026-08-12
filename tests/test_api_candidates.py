import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db
from storage.db_models import Base, Candidate, CandidateTimelineEvent, ResumeVersion
import uuid

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
    yield engine

@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_list_candidates(client, db_session: Session):
    c = Candidate(id=str(uuid.uuid4()), first_name="John", last_name="Doe", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    response = client.get("/candidates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["first_name"] == "John"
    assert data[0]["last_name"] == "Doe"

def test_get_candidate(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Jane", last_name="Smith", availability_status="PLACED")
    db_session.add(c)
    db_session.commit()

    response = client.get(f"/candidates/{c_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == c_id
    assert data["first_name"] == "Jane"
    assert data["availability_status"] == "PLACED"

def test_get_candidate_not_found(client):
    response = client.get("/candidates/unknown-id")
    assert response.status_code == 404

def test_update_candidate_status(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Alice", last_name="Wonder", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    response = client.patch(
        f"/candidates/{c_id}/status", 
        json={"new_status": "PLACED", "recruiter_name": "Bob", "reason": "Hired!"}
    )
    assert response.status_code == 200
    
    # Check if DB was updated
    db_session.refresh(c)
    assert c.availability_status == "PLACED"

def test_get_candidate_timeline(client, db_session: Session):
    # Setup candidate and trigger a status update to create a timeline event
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Timeline", last_name="Test", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    client.patch(
        f"/candidates/{c_id}/status", 
        json={"new_status": "PLACED", "recruiter_name": "Bob"}
    )

    response = client.get(f"/candidates/{c_id}/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["event_type"] == "STAGE_CHANGED"
    assert data[0]["created_by"] == "Bob"

def test_update_candidate(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="OldName", last_name="OldLast", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()
    
    response = client.put(
        f"/candidates/{c_id}",
        json={"first_name": "NewName", "primary_email": "new@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "NewName"
    assert data["primary_email"] == "new@example.com"
    assert data["last_name"] == "OldLast"
    
    # Check if a timeline event was logged
    response_timeline = client.get(f"/candidates/{c_id}/timeline")
    assert response_timeline.status_code == 200
    timeline_data = response_timeline.json()
    assert len(timeline_data) == 1
    assert timeline_data[0]["event_type"] == "PROFILE_UPDATED"

def test_get_candidate_file(client, db_session: Session, tmp_path, monkeypatch):
    from storage.db_models import ResumeVersion
    from storage.cas import CASManager
    from config import settings
    
    original_settings = settings.Settings
    def mock_settings(*args, **kwargs):
        s = original_settings(*args, **kwargs)
        s.cas_root_dir = str(tmp_path)
        return s
    monkeypatch.setattr(settings, "Settings", mock_settings)
    
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Jane", last_name="Doe", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()
    
    content = b"PDF dummy content"
    cas_mgr = CASManager(tmp_path)
    file_hash, cas_path = cas_mgr.store(content, extension=".pdf")
    
    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash=file_hash,
        original_filename="jane_resume.pdf",
        file_type="PDF",
        raw_text="Jane Resume Content",
        layout_metadata={},
        is_primary=True
    )
    db_session.add(rv)
    db_session.commit()
    
    response = client.get(f"/candidates/{c_id}/file")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"

def test_reprocess_candidate(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Reprocess", last_name="Test", availability_status="ACTIVE", current_title="Software Engineer")
    db_session.add(c)
    
    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash="reprocess_hash",
        original_filename="reprocess.pdf",
        file_type="PDF",
        raw_text="Reprocess Test Resume Content with skills Python SQL",
        layout_metadata={},
        is_primary=True
    )
    db_session.add(rv)
    db_session.commit()
    
    response = client.post(f"/candidates/{c_id}/reprocess")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Check if FTS was populated/updated
    fts_rows = db_session.execute(
        text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": c_id}
    ).fetchall()
    assert len(fts_rows) == 1
    
    # Check if timeline event was logged
    response_timeline = client.get(f"/candidates/{c_id}/timeline")
    assert response_timeline.status_code == 200
    timeline_data = response_timeline.json()
    assert len(timeline_data) >= 1
    assert any(e["event_type"] == "REPROCESS_TRIGGERED" for e in timeline_data)

def test_reprocess_candidate_stream(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Stream", last_name="Reprocess", availability_status="ACTIVE", current_title="Data Scientist")
    db_session.add(c)
    
    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash="stream_hash",
        original_filename="stream.pdf",
        file_type="PDF",
        raw_text="Stream Reprocess Resume Content with PyTorch and Machine Learning",
        layout_metadata={},
        is_primary=True
    )
    db_session.add(rv)
    db_session.commit()
    
    response = client.post(f"/candidates/{c_id}/reprocess-stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text_content = response.text
    assert "FETCHING_RESUME" in text_content
    assert "UPDATING_FTS" in text_content
    assert "GENERATING_VECTORS" in text_content
    assert "LOGGING_TIMELINE" in text_content
    assert "COMPLETED" in text_content

