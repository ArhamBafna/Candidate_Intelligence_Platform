import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from storage.db_models import Candidate, CandidateTimelineEvent, ResumeVersion
from storage.cas import CASManager
from config import settings
from conftest import MockVectorStore

def test_list_candidates(client: TestClient, db_session: Session):
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

def test_get_candidate(client: TestClient, db_session: Session):
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

def test_get_candidate_not_found(client: TestClient):
    response = client.get("/candidates/unknown-id")
    assert response.status_code == 404

def test_update_candidate_status(client: TestClient, db_session: Session):
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

def test_get_candidate_timeline(client: TestClient, db_session: Session):
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

def test_update_candidate(client: TestClient, db_session: Session):
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

    response_timeline = client.get(f"/candidates/{c_id}/timeline")
    assert response_timeline.status_code == 200
    timeline_data = response_timeline.json()
    assert len(timeline_data) == 1
    assert timeline_data[0]["event_type"] == "PROFILE_UPDATED"

def test_get_candidate_file(client: TestClient, db_session: Session, tmp_path, monkeypatch):
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

def test_reprocess_candidate(client: TestClient, db_session: Session):
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

    fts_rows = db_session.execute(
        text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": c_id}
    ).fetchall()
    assert len(fts_rows) == 1

    response_timeline = client.get(f"/candidates/{c_id}/timeline")
    assert response_timeline.status_code == 200
    timeline_data = response_timeline.json()
    assert len(timeline_data) >= 1
    assert any(e["event_type"] == "REPROCESS_TRIGGERED" for e in timeline_data)

def test_reprocess_candidate_stream(client: TestClient, db_session: Session):
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

    db_session.execute(
        text("INSERT INTO candidate_fts (candidate_id, full_name) VALUES (:cid, :fname)"),
        {"cid": c_id, "fname": "Delete Me"}
    )
    db_session.commit()

    response = client.delete(f"/candidates/{c_id}")
    assert response.status_code == 204

    deleted_c = db_session.query(Candidate).filter(Candidate.id == c_id).first()
    assert deleted_c is None

    deleted_rv = db_session.query(ResumeVersion).filter(ResumeVersion.candidate_id == c_id).all()
    assert len(deleted_rv) == 0

    deleted_timeline = db_session.query(CandidateTimelineEvent).filter(CandidateTimelineEvent.candidate_id == c_id).all()
    assert len(deleted_timeline) == 0

    fts_rows = db_session.execute(
        text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": c_id}
    ).fetchall()
    assert len(fts_rows) == 0

    assert c_id in mock_vector_db.deleted_candidate_ids

def test_delete_candidate_not_found(client: TestClient) -> None:
    response = client.delete("/candidates/non-existent-id")
    assert response.status_code == 404

def test_batch_delete_candidates(client: TestClient, db_session: Session, monkeypatch) -> None:
    mock_vector_db = MockVectorStore()
    from api.dependencies import get_vector_db
    monkeypatch.setattr("api.routes.candidates.get_vector_db", lambda: mock_vector_db)

    c1_id = str(uuid.uuid4())
    c2_id = str(uuid.uuid4())
    c1 = Candidate(id=c1_id, first_name="Batch1", last_name="Delete")
    c2 = Candidate(id=c2_id, first_name="Batch2", last_name="Delete")
    db_session.add_all([c1, c2])
    db_session.commit()

    response = client.post("/candidates/batch-delete", json={"candidate_ids": [c1_id, c2_id]})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["deleted_count"] == 2
    assert c1_id in data["candidate_ids"]
    assert c2_id in data["candidate_ids"]

    assert db_session.query(Candidate).filter(Candidate.id == c1_id).first() is None
    assert db_session.query(Candidate).filter(Candidate.id == c2_id).first() is None

def test_batch_reprocess_stream(client: TestClient, db_session: Session, monkeypatch) -> None:
    mock_vector_db = MockVectorStore()
    monkeypatch.setattr("api.routes.candidates.get_vector_db", lambda: mock_vector_db)

    c_id = str(uuid.uuid4())
    candidate = Candidate(id=c_id, first_name="Stream", last_name="Tester")
    db_session.add(candidate)
    
    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash="hash_stream_123",
        original_filename="resume_stream.pdf",
        file_type="pdf",
        is_primary=True,
        raw_text="Experienced Software Engineer skilled in Python, FastAPI and React.",
        layout_metadata={}
    )
    db_session.add(rv)
    db_session.commit()

    response = client.post("/candidates/batch-reprocess-stream", json={"candidate_ids": [c_id]})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "COMPLETED" in response.text

