"""Consolidated test suite for all Candidate Intelligence Platform API endpoints.

Covers:
- System & middleware (health, cors, 404, unhandled exceptions, recent logs)
- Core dependencies (settings, db session generator, vector db connection)
- Candidate management CRUD & file retrieval
- Reprocessing (single, batch, streaming SSE)
- File upload & upload streaming (batch, duplicates, non-resume rejection, size limits)
- Search & search streaming (filters, exact title, job ad distillation, scorecards)
- Candidate AI match insights & streaming fallbacks
"""
import json
import uuid
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_settings, get_vector_db
from api.main import app
from api.routes.search import _build_search_query
from api.schemas.search import SearchQueryRequest
from config.settings import Settings
from conftest import MockVectorStore
from storage.cas import CASManager
from storage.db_models import Candidate, CandidateTimelineEvent, ResumeVersion


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

LONG_JOHN = b"John Doe\nSoftware Engineer\nEmail: john@example.com\nSkills: Python, React, cloud platforms"
LONG_JANE = b"Jane Smith\nData Scientist\nEmail: jane@example.com\nSkills: Python, SQL, machine learning"

JOB_AD = (
    "Data Engineer\n\n"
    "We are hiring a Data Engineer to join our analytics platform team.\n\n"
    "Responsibilities:\n"
    "- Build pipelines on kubernetes clusters\n"
    "- Model data in postgres warehouses\n\n"
    "Requirements:\n"
    "- At least 5+ years of experience building data platforms\n"
    "- Deep knowledge of python and sql\n\n"
    "Location: NYC\n"
    "We offer a competitive salary and great benefits.\n"
)


def _patch_extractor(monkeypatch: pytest.MonkeyPatch, mock_extract: Any) -> None:
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        mock_extract,
    )


def _mock_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "generate_single_embedding", lambda text: [0.0] * 384)


def _parse_sse_events(body: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


@pytest.fixture
def candidate_id(db_session: Session) -> str:
    cid = str(uuid.uuid4())
    db_session.add(Candidate(id=cid, first_name="Insight", last_name="Test", availability_status="ACTIVE"))
    db_session.commit()
    return cid


# ---------------------------------------------------------------------------
# System, Middleware, and Dependencies
# ---------------------------------------------------------------------------

def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_headers(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_404_handler(client: TestClient) -> None:
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_unhandled_exception_still_logs_http_request(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class StubLogger:
        def __init__(self) -> None:
            self.events: List[Any] = []

        def info(self, event: str, **kwargs: object) -> None:
            self.events.append((event, kwargs))

        def error(self, event: str, **kwargs: object) -> None:
            self.events.append((event, kwargs))

    stub = StubLogger()
    monkeypatch.setattr("api.main.logger", stub)

    def explode() -> None:
        raise RuntimeError("db gone")

    client.app.dependency_overrides[get_db] = explode
    try:
        with pytest.raises(RuntimeError):
            client.post("/search", json={"query_text": "python"})
    finally:
        client.app.dependency_overrides.pop(get_db, None)

    failed = [kw for event, kw in stub.events if event == "http_request"]
    assert any(
        kw.get("status_code") == 500 and kw.get("path") == "/search" and "duration_s" in kw
        for kw in failed
    )


def test_get_logs_endpoint_returns_recent_events(client: TestClient) -> None:
    import structlog
    logger = structlog.get_logger()
    logger.info("test_system_event", detail="unit test log")

    response = client.get("/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "status" in data

    events = [log for log in data["logs"] if log.get("event") == "test_system_event"]
    assert len(events) >= 1
    assert events[0]["detail"] == "unit test log"


def test_get_settings() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_db() -> None:
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    try:
        next(db_gen)
    except StopIteration:
        pass
    else:
        pytest.fail("Generator did not stop")


def test_get_vector_db() -> None:
    import lancedb
    vector_db = get_vector_db()
    assert isinstance(vector_db, lancedb.DBConnection)


# ---------------------------------------------------------------------------
# Candidate CRUD & Management
# ---------------------------------------------------------------------------

def test_list_candidates(client: TestClient, db_session: Session) -> None:
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


@pytest.mark.parametrize("scenario", ["found", "not_found"])
def test_get_candidate_scenarios(client: TestClient, db_session: Session, scenario: str) -> None:
    if scenario == "found":
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
    else:
        response = client.get("/candidates/unknown-id")
        assert response.status_code == 404


def test_update_candidate_status(client: TestClient, db_session: Session) -> None:
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Alice", last_name="Wonder", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    response = client.patch(
        f"/candidates/{c_id}/status",
        json={"new_status": "PLACED", "recruiter_name": "Bob", "reason": "Hired!"},
    )
    assert response.status_code == 200
    db_session.refresh(c)
    assert c.availability_status == "PLACED"


def test_get_candidate_timeline(client: TestClient, db_session: Session) -> None:
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Timeline", last_name="Test", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    client.patch(
        f"/candidates/{c_id}/status",
        json={"new_status": "PLACED", "recruiter_name": "Bob"},
    )

    response = client.get(f"/candidates/{c_id}/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["event_type"] == "STAGE_CHANGED"
    assert data[0]["created_by"] == "Bob"


def test_update_candidate(client: TestClient, db_session: Session) -> None:
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="OldName", last_name="OldLast", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    response = client.put(
        f"/candidates/{c_id}",
        json={"first_name": "NewName", "primary_email": "new@example.com"},
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


def test_get_candidate_file(client: TestClient, db_session: Session, test_settings: Settings) -> None:
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Jane", last_name="Doe", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    content = b"PDF dummy content"
    cas_mgr = CASManager(test_settings.cas_root_dir)
    file_hash, cas_path = cas_mgr.store(content, extension=".pdf")

    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash=file_hash,
        original_filename="jane_resume.pdf",
        file_type="PDF",
        raw_text="Jane Resume Content",
        layout_metadata={},
        is_primary=True,
    )
    db_session.add(rv)
    db_session.commit()

    response = client.get(f"/candidates/{c_id}/file")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"


def test_delete_candidate_success(client: TestClient, db_session: Session, mock_vector_db: MockVectorStore) -> None:
    c_id = str(uuid.uuid4())
    candidate = Candidate(id=c_id, first_name="Delete", last_name="Me", primary_email="delete.me@example.com")
    db_session.add(candidate)

    timeline = CandidateTimelineEvent(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        event_type="PROFILE_CREATED",
        title="Created",
        created_by="System",
    )
    db_session.add(timeline)

    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash="hash123",
        original_filename="resume.pdf",
        file_type="pdf",
        raw_text="Sample text",
        layout_metadata={},
    )
    db_session.add(rv)
    db_session.commit()

    db_session.execute(
        text("INSERT INTO candidate_fts (candidate_id, full_name) VALUES (:cid, :fname)"),
        {"cid": c_id, "fname": "Delete Me"},
    )
    db_session.commit()

    response = client.delete(f"/candidates/{c_id}")
    assert response.status_code == 204
    assert db_session.query(Candidate).filter(Candidate.id == c_id).first() is None
    assert len(db_session.query(ResumeVersion).filter(ResumeVersion.candidate_id == c_id).all()) == 0
    assert len(db_session.query(CandidateTimelineEvent).filter(CandidateTimelineEvent.candidate_id == c_id).all()) == 0

    fts_rows = db_session.execute(
        text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": c_id},
    ).fetchall()
    assert len(fts_rows) == 0
    assert c_id in mock_vector_db.deleted_candidate_ids


def test_delete_candidate_not_found(client: TestClient) -> None:
    response = client.delete("/candidates/non-existent-id")
    assert response.status_code == 404


def test_batch_delete_candidates(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_vector_db = MockVectorStore()
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


# ---------------------------------------------------------------------------
# Reprocessing
# ---------------------------------------------------------------------------

def test_reprocess_candidate(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from storage.index_writer import StorageIndexWriter
    monkeypatch.setattr(StorageIndexWriter, "_update_vectors_with_precomputed", lambda *args, **kwargs: None)
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0] * 4 for _ in texts])
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Reprocess", "last_name": "Test", "primary_email": "",
            "primary_phone": "", "current_title": "Software Engineer", "warnings": []
        },
    )
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
        is_primary=True,
    )
    db_session.add(rv)
    db_session.commit()

    response = client.post(f"/candidates/{c_id}/reprocess")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    fts_rows = db_session.execute(
        text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": c_id},
    ).fetchall()
    assert len(fts_rows) == 1

    response_timeline = client.get(f"/candidates/{c_id}/timeline")
    assert response_timeline.status_code == 200
    timeline_data = response_timeline.json()
    assert len(timeline_data) >= 1
    assert any(e["event_type"] == "REPROCESS_TRIGGERED" for e in timeline_data)


def test_reprocess_candidate_stream(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from storage.index_writer import StorageIndexWriter
    monkeypatch.setattr(StorageIndexWriter, "_update_vectors_with_precomputed", lambda *args, **kwargs: None)
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0] * 4 for _ in texts])
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Stream", "last_name": "Reprocess", "primary_email": "",
            "primary_phone": "", "current_title": "Data Scientist", "warnings": []
        },
    )

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
        is_primary=True,
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


def test_batch_reprocess_stream(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from storage.index_writer import StorageIndexWriter
    monkeypatch.setattr(StorageIndexWriter, "_update_vectors_with_precomputed", lambda *args, **kwargs: None)
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0] * 4 for _ in texts])
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Stream", "last_name": "Tester", "primary_email": "",
            "primary_phone": "", "current_title": "Engineer", "warnings": []
        },
    )

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
        layout_metadata={},
    )
    db_session.add(rv)
    db_session.commit()

    response = client.post("/candidates/batch-reprocess-stream", json={"candidate_ids": [c_id]})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "COMPLETED" in response.text


# ---------------------------------------------------------------------------
# Upload & Upload Streaming
# ---------------------------------------------------------------------------

def test_upload_rejects_oversized_file(client: TestClient, test_settings: Settings) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        db_path=test_settings.db_path,
        cas_root_dir=test_settings.cas_root_dir,
        vector_db_path=test_settings.vector_db_path,
        max_upload_size_mb=0,
    )
    try:
        response = client.post(
            "/candidates/upload",
            files={"file": ("big.pdf", b"some content", "application/pdf")},
        )
        assert response.status_code == 413
        assert "exceeds" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_upload_accepts_file_within_size_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"Alice Smith\nSoftware Engineer\nEmail: alice@example.com"
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Alice", "last_name": "Smith",
            "primary_email": "alice@example.com", "primary_phone": "",
            "current_title": "Software Engineer", "warnings": []
        },
    )
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0] * 4 for _ in texts])
    response = client.post(
        "/candidates/upload",
        files={"file": ("alice.txt", content, "text/plain")},
    )
    assert response.status_code != 413


def test_upload_stream_multi_resume(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0] * 4 for _ in texts])

    def mock_extract(text: str, **kwargs: Any) -> Dict[str, Any]:
        if "Jane" in text:
            return {"first_name": "Jane", "last_name": "Smith", "primary_email": "jane@example.com", "primary_phone": "", "current_title": "Data Scientist", "warnings": []}
        return {"first_name": "John", "last_name": "Doe", "primary_email": "john@example.com", "primary_phone": "", "current_title": "Software Engineer", "warnings": []}

    _patch_extractor(monkeypatch, mock_extract)
    files = [
        ("files", ("resume1.txt", LONG_JOHN, "text/plain")),
        ("files", ("resume2.txt", LONG_JANE, "text/plain")),
    ]

    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [json.loads(line[6:]) for line in response.iter_lines() if line and line.startswith("data: ")]
    assert len(events) > 0

    completed_events = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed_events) == 2
    for e in completed_events:
        assert "warnings" in e

    names = {e.get("candidate_name") for e in completed_events}
    assert "John Doe" in names
    assert "Jane Smith" in names


def test_upload_stream_duplicate_resume(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_extractor(monkeypatch, lambda text, **kwargs: {
        "first_name": "John", "last_name": "Doe", "primary_email": "john@example.com",
        "primary_phone": "", "current_title": "Software Engineer", "warnings": []
    })
    files = [("files", ("resume1.txt", LONG_JOHN, "text/plain"))]
    client.post("/candidates/upload-stream", files=files)

    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = [json.loads(line[6:]) for line in response.iter_lines() if line and line.startswith("data: ")]
    skipped_events = [e for e in events if e.get("status") == "SKIPPED_DUPLICATE"]
    assert len(skipped_events) == 1
    assert skipped_events[0].get("file_name") == "resume1.txt"


def test_upload_stream_non_resume_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_extractor(monkeypatch, lambda text, **kwargs: {
        "first_name": "Uploaded", "last_name": "Candidate", "primary_email": "",
        "primary_phone": "", "current_title": "", "warnings": []
    })
    files = [("files", ("contract.pdf", b"This Referral Agreement is entered into by and between the parties hereto. Governing law and indemnification terms apply.", "application/pdf"))]
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = [json.loads(line[6:]) for line in response.iter_lines() if line and line.startswith("data: ")]
    rejected = [e for e in events if e.get("status") == "SKIPPED_NON_RESUME"]
    assert len(rejected) == 1
    assert rejected[0]["classified_as"] == "NON_RESUME_LEGAL_CONTRACT"
    assert "legal contract" in rejected[0]["message"]


def test_upload_stream_review_exposes_duplicate_hint_fields(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    db_session.add(Candidate(id="lookalike-id", first_name="Jon", last_name="Doee"))
    db_session.commit()

    def mock_extract(text: str, **kwargs: Any) -> Dict[str, Any]:
        return {"first_name": "Jane", "last_name": "Doe", "primary_email": "jane.doe@example.com", "primary_phone": "", "current_title": "Engineer", "warnings": []}

    _patch_extractor(monkeypatch, mock_extract)

    app.dependency_overrides[get_settings] = lambda: Settings(
        db_path=str(tmp_path / "review.db"),
        cas_root_dir=str(tmp_path / "cas"),
        vector_db_path=str(tmp_path / "vec"),
        entity_res_auto_merge_threshold=1.01,
        entity_res_review_threshold=0.70,
    )

    files = [("files", ("review_resume.txt", b"Jane Doe\nSenior Python Developer\nEmail: jane.doe@example.com\nPhone: 555-123-4567\nSkills: Python, FastAPI\nExperience: 8 years building APIs", "text/plain"))]
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = [json.loads(line[6:]) for line in response.iter_lines() if line and line.startswith("data: ")]
    completed = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed) == 1
    assert completed[0]["resolution_action"] == "REVIEW"
    assert completed[0]["matched_candidate_id"] == "lookalike-id"
    assert completed[0]["classified_as"] == "VALID_RESUME"
    assert completed[0]["status"] == "SUCCESS"


def test_upload_stream_transparency_events(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0] * 4 for _ in texts])
    _patch_extractor(monkeypatch, lambda text, **kwargs: {
        "first_name": "Sparse", "last_name": "Resume", "primary_email": "",
        "primary_phone": "", "current_title": "",
        "warnings": [{"level": "warning", "event": "ai_llm_extraction_failed", "action": "skipping_ai_extraction"}],
        "used_ai_fallback": True,
    })
    files = [("files", ("sparse_resume.txt", b"Sparse Resume\nRandom text without clear structure but long enough\nEmail: sparse@example.com\nSkills: testing", "text/plain"))]
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = [json.loads(line[6:]) for line in response.iter_lines() if line and line.startswith("data: ")]
    stages = [e.get("stage") for e in events]
    assert "HASHING" in stages
    assert "PARSING" in stages
    assert "CLASSIFYING" in stages
    assert "CHUNKING" in stages
    assert ("AI_EXTRACTION" in stages) or ("ENTITY_RESOLUTION" in stages)

    completed = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed) == 1
    assert "used_ai_fallback" in completed[0]


def test_upload_stream_rejects_oversized_file(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_size_mb=0)
    try:
        files = [("files", ("huge.pdf", b"any content at all", "application/pdf"))]
        response = client.post("/candidates/upload-stream", files=files)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = [json.loads(line[6:]) for line in response.iter_lines() if line and line.startswith("data: ")]
        failed_events = [e for e in events if e.get("status") == "FAILED"]
        assert len(failed_events) == 1
        assert "exceeds" in failed_events[0]["message"].lower()
        assert failed_events[0]["file_name"] == "huge.pdf"
    finally:
        app.dependency_overrides.pop(get_settings, None)


# ---------------------------------------------------------------------------
# Search & Search Streaming
# ---------------------------------------------------------------------------

@patch("api.routes.search.search_candidates")
def test_search_candidates(mock_search: Any, client: TestClient, db_session: Session) -> None:
    cid = str(uuid.uuid4())
    c = Candidate(id=cid, first_name="Search", last_name="Test", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    def mock_generator(*args: Any, **kwargs: Any) -> Any:
        yield ("COMPLETE", 100, "Search complete", (
            [
                {
                    "candidate_id": cid,
                    "rank": 1,
                    "rrf_score": 0.0328,
                    "match_scorecard": {
                        "strict_filters": [],
                        "keyword_matches": [],
                        "semantic_matches": [],
                        "ai_inferences": [],
                    },
                }
            ],
            ["Vector search skipped (test warning)"],
        ))

    mock_search.side_effect = mock_generator

    response = client.post(
        "/search",
        json={"query_text": "Python Engineer", "city": "NYC", "top_k": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Python Engineer"
    assert data["total_results"] == 1
    assert "warnings" in data
    assert data["results"][0]["candidate_id"] == cid
    assert data["results"][0]["rrf_score"] == 0.0328
    assert data["results"][0]["candidate_info"]["first_name"] == "Search"


def test_upload_and_search_exact_keyword_integration(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Java",
            "last_name": "Developer",
            "primary_email": "java@example.com",
            "primary_phone": "",
            "current_title": "Java Developer",
            "warnings": [],
        },
    )

    resume_bytes = b"Java Developer\nSenior Software Engineer\nExperienced in Java, Spring Boot, microservices architecture."
    upload_res = client.post(
        "/candidates/upload",
        files={"file": ("java_resume.txt", resume_bytes, "text/plain")},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    cand_id = upload_data["candidate_id"]

    search_res = client.post("/search", json={"query_text": "java"})
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_results"] >= 1
    assert search_data["results"][0]["candidate_id"] == cand_id
    assert search_data["results"][0]["candidate_info"]["first_name"] == "Java"


@patch("api.routes.search.search_candidates")
def test_search_response_passes_through_populated_scorecard(mock_search: Any, client: TestClient) -> None:
    scorecard = {
        "strict_filters": [{"field": "current_city", "operator": "=", "value": "NYC"}],
        "keyword_matches": ["python"],
        "semantic_matches": [{"signal": "semantic_similarity", "vector_rank": 1}],
        "ai_inferences": [],
    }

    def mock_generator(*args: Any, **kwargs: Any) -> Any:
        yield ("COMPLETE", 100, "Search complete", (
            [{
                "candidate_id": "cand-x",
                "rank": 1,
                "rrf_score": 0.03,
                "rerank_score": None,
                "match_percentage": 72.5,
                "match_scorecard": scorecard,
            }],
            [],
        ))

    mock_search.side_effect = mock_generator

    response = client.post("/search", json={"query_text": "python", "city": "NYC"})
    assert response.status_code == 200
    item = response.json()["results"][0]
    assert item["match_scorecard"]["keyword_matches"] == ["python"]
    assert item["match_scorecard"]["strict_filters"][0]["value"] == "NYC"
    assert item["rerank_score"] is None
    assert item["match_percentage"] == 72.5


def test_exact_title_flag_emits_title_exact_dsl() -> None:
    soft = _build_search_query(SearchQueryRequest(query_text="sql", title="AI Engineer"))
    assert "title:'AI Engineer'" in soft
    assert "title_exact" not in soft

    exact = _build_search_query(
        SearchQueryRequest(query_text="sql", title="AI Engineer", exact_title=True)
    )
    assert "title_exact:'AI Engineer'" in exact


def test_job_ad_mode_returns_recipe_metadata_with_fallback_warning(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from candidate_intelligence_platform.search import job_ad_distiller as jad
    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: None)
    _mock_embedding(monkeypatch)

    response = client.post("/search", json={"query_text": JOB_AD})
    assert response.status_code == 200
    data = response.json()
    recipe = data["job_ad_recipe"]
    assert recipe is not None
    assert recipe["source"] == "fallback"
    assert recipe["min_yoe"] >= 5.0
    assert any("unavailable" in w for w in data["warnings"])


def test_job_ad_mode_builds_filters_and_short_semantic_summary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from candidate_intelligence_platform.search import job_ad_distiller as jad

    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: "llama3.2")

    class FakeResponse:
        class message:
            content = json.dumps({
                "title": "Data Engineer",
                "skills": ["kubernetes", "postgres"],
                "min_yoe": 5,
                "location": "NYC",
            })

    monkeypatch.setattr("ollama.chat", lambda **kwargs: FakeResponse())
    _mock_embedding(monkeypatch)

    captured: Dict[str, Any] = {}

    def mock_generator(full_query: str, db: Any, vector_db: Any, return_warnings: bool = False, semantic_query: Any = None) -> Any:
        captured["query"] = full_query
        captured["semantic_query"] = semantic_query
        yield ("COMPLETE", 100, "Search complete", ([], []))

    with patch("api.routes.search.search_candidates", side_effect=mock_generator):
        response = client.post("/search", json={"query_text": JOB_AD})

    assert response.status_code == 200
    data = response.json()
    assert data["job_ad_recipe"]["source"] == "ai"

    full_query = captured["query"]
    assert "title:'Data Engineer'" in full_query
    assert "yoe >= 5" in full_query
    assert "kubernetes" in full_query
    assert full_query != JOB_AD

    semantic_query = captured["semantic_query"]
    assert semantic_query is not None
    assert len(semantic_query) < 1200


def test_search_stream_endpoint_exists(client: TestClient) -> None:
    response = client.post("/search/stream", json={"query_text": "software engineer", "top_k": 5})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_search_stream_emits_progress_events(client: TestClient) -> None:
    payload = {"query_text": "software engineer", "top_k": 5}
    with client.stream("POST", "/search/stream", json=payload) as response:
        assert response.status_code == 200
        events = [
            json.loads(line[6:])
            for line in response.iter_lines()
            if line and line.startswith("data: ")
        ]
        stages = [e.get("stage") for e in events]
        assert "STARTING" in stages
        assert "FTS_SEARCH" in stages
        assert "COMPLETE" in stages

        complete_event = next((e for e in events if e.get("stage") == "COMPLETE"), None)
        assert complete_event is not None
        assert "data" in complete_event
        assert "results" in complete_event["data"]


# ---------------------------------------------------------------------------
# Candidate Match Insight Streaming
# ---------------------------------------------------------------------------

def test_get_candidate_insight_stream(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    c_id = str(uuid.uuid4())
    candidate = Candidate(id=c_id, first_name="Insight", last_name="Tester")
    db_session.add(candidate)

    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=c_id,
        cas_file_hash="hash_insight",
        original_filename="resume_insight.pdf",
        file_type="pdf",
        is_primary=True,
        raw_text="Insight Software Engineer",
        layout_metadata={},
    )
    db_session.add(rv)
    db_session.commit()

    async def mock_generate(prompt: str, **kwargs: Any) -> Any:
        yield "This "
        yield "is "
        yield "a "
        yield "match."

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", mock_generate)

    response = client.get(f"/candidates/{c_id}/insight?query=Software Engineer")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    text_content = response.text
    assert "This" in text_content
    assert "match." in text_content


def test_insight_streams_tokens_when_model_available(
    client: TestClient, candidate_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("api.routes.candidates.resolve_chat_model", lambda force_refresh=False: "llama3.2")

    async def fake_stream(prompt: str, model_name: str, **kwargs: Any) -> Any:
        assert model_name == "llama3.2"
        for tok in ["hello ", "world"]:
            yield tok

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", fake_stream)

    with client.stream("GET", f"/candidates/{candidate_id}/insight", params={"query": "python"}) as response:
        body = "".join(response.iter_text())

    events = _parse_sse_events(body)
    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "hello world"
    assert not any(e.get("error") for e in events)


def test_insight_emits_visible_message_when_no_chat_model(
    client: TestClient, candidate_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("api.routes.candidates.resolve_chat_model", lambda force_refresh=False: None)

    async def must_not_run(prompt: str, model_name: str, **kwargs: Any) -> Any:
        raise AssertionError("ollama stream should not be called when no model is available")
        yield

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", must_not_run)

    with client.stream("GET", f"/candidates/{candidate_id}/insight", params={"query": "python"}) as response:
        body = "".join(response.iter_text())

    events = _parse_sse_events(body)
    errors = [e for e in events if e.get("error") == "AI_EXPLANATION_UNAVAILABLE"]
    assert len(errors) == 1
    assert "taking a break right now" in errors[0]["message"].lower()


def test_insight_invalid_model_retries_fallback_before_giving_up(
    client: TestClient, candidate_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CIP_LLM_MODEL", "broken-model")
    monkeypatch.setattr("api.routes.candidates.resolve_chat_model", lambda force_refresh=False: "broken-model")
    called_models: List[str] = []

    async def fake_stream(prompt: str, model_name: str, **kwargs: Any) -> Any:
        called_models.append(model_name)
        if model_name == "broken-model":
            raise RuntimeError("model 'broken-model' not found")
        yield "recovered"

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", fake_stream)

    with client.stream("GET", f"/candidates/{candidate_id}/insight", params={"query": "python"}) as response:
        body = "".join(response.iter_text())

    events = _parse_sse_events(body)
    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "recovered"
    assert called_models == ["broken-model", "llama3.2"]
    assert not any(e.get("error") for e in events)


def test_insight_total_failure_surfaces_visible_message(
    client: TestClient, candidate_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("api.routes.candidates.resolve_chat_model", lambda force_refresh=False: "llama3.2")

    async def always_fails(prompt: str, model_name: str, **kwargs: Any) -> Any:
        raise RuntimeError("ollama connection refused")
        yield

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", always_fails)

    with client.stream("GET", f"/candidates/{candidate_id}/insight", params={"query": "python"}) as response:
        body = "".join(response.iter_text())

    events = _parse_sse_events(body)
    errors = [e for e in events if e.get("error") == "AI_EXPLANATION_UNAVAILABLE"]
    assert len(errors) == 1
    assert "taking a break right now" in errors[0]["message"].lower()


def test_insight_passes_criteria_to_prompt(
    client: TestClient, candidate_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("api.routes.candidates.resolve_chat_model", lambda force_refresh=False: "llama3.2")
    captured_prompt: List[str] = []

    async def fake_stream(prompt: str, model_name: str, **kwargs: Any) -> Any:
        captured_prompt.append(prompt)
        yield "all good"

    monkeypatch.setattr("api.routes.candidates.stream_ollama_generate", fake_stream)

    with client.stream(
        "GET",
        f"/candidates/{candidate_id}/insight",
        params={
            "query": "python",
            "city": "Boston",
            "job_title": "Lead Architect",
            "min_years": 8,
        },
    ) as response:
        body = "".join(response.iter_text())

    events = _parse_sse_events(body)
    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "all good"
    assert len(captured_prompt) == 1
    assert "Target City / Location: Boston" in captured_prompt[0]
    assert "Target Job Title: Lead Architect" in captured_prompt[0]
    assert "Minimum Experience: 8.0 years" in captured_prompt[0] or "Minimum Experience: 8 years" in captured_prompt[0]
