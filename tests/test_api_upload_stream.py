import pytest
import json
from fastapi.testclient import TestClient

def _patch_extractor(monkeypatch, mock_extract):
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        mock_extract
    )

LONG_JOHN = b"John Doe\nSoftware Engineer\nEmail: john@example.com\nSkills: Python, React, cloud platforms"
LONG_JANE = b"Jane Smith\nData Scientist\nEmail: jane@example.com\nSkills: Python, SQL, machine learning"

def test_upload_stream_multi_resume(client: TestClient, monkeypatch):
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0]*4 for _ in texts])
    def mock_extract(text, **kwargs):
        if "Jane" in text:
            return {"first_name": "Jane", "last_name": "Smith", "primary_email": "jane@example.com", "primary_phone": "", "current_title": "Data Scientist", "warnings": []}
        return {"first_name": "John", "last_name": "Doe", "primary_email": "john@example.com", "primary_phone": "", "current_title": "Software Engineer", "warnings": []}
    _patch_extractor(monkeypatch, mock_extract)
    files = [
        ("files", ("resume1.txt", LONG_JOHN, "text/plain")),
        ("files", ("resume2.txt", LONG_JANE, "text/plain"))
    ]

    response = client.post("/candidates/upload-stream", files=files)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))

    assert len(events) > 0

    completed_events = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed_events) == 2
    for e in completed_events:
        assert "warnings" in e

    names = {e.get("candidate_name") for e in completed_events}
    assert "John Doe" in names
    assert "Jane Smith" in names

def test_upload_stream_duplicate_resume(client: TestClient, monkeypatch):
    _patch_extractor(monkeypatch, lambda text, **kwargs: {
        "first_name": "John", "last_name": "Doe", "primary_email": "john@example.com",
        "primary_phone": "", "current_title": "Software Engineer", "warnings": []
    })
    files = [("files", ("resume1.txt", LONG_JOHN, "text/plain"))]
    client.post("/candidates/upload-stream", files=files)

    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))

    skipped_events = [e for e in events if e.get("status") == "SKIPPED_DUPLICATE"]
    assert len(skipped_events) == 1
    assert skipped_events[0].get("file_name") == "resume1.txt"

def test_upload_stream_non_resume_rejected(client: TestClient, monkeypatch):
    _patch_extractor(monkeypatch, lambda text, **kwargs: {
        "first_name": "Uploaded", "last_name": "Candidate", "primary_email": "",
        "primary_phone": "", "current_title": "", "warnings": []
    })
    files = [("files", ("contract.pdf", b"This Referral Agreement is entered into by and between the parties hereto. Governing law and indemnification terms apply.", "application/pdf"))]
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))

    rejected = [e for e in events if e.get("status") == "SKIPPED_NON_RESUME"]
    assert len(rejected) == 1
    assert rejected[0]["classified_as"] == "NON_RESUME_LEGAL_CONTRACT"
    assert "legal contract" in rejected[0]["message"]

def test_upload_stream_review_exposes_duplicate_hint_fields(client: TestClient, db_session, monkeypatch, tmp_path):
    """REVIEW band COMPLETED event carries resolution_action + matched_candidate_id (UI chip reads these)."""
    from api.main import app
    from api.dependencies import get_settings
    from config.settings import Settings
    from storage.db_models import Candidate

    db_session.add(Candidate(id="lookalike-id", first_name="Jon", last_name="Doee"))
    db_session.commit()

    def mock_extract(text, **kwargs):
        return {"first_name": "Jane", "last_name": "Doe", "primary_email": "jane.doe@example.com", "primary_phone": "", "current_title": "Engineer", "warnings": []}
    _patch_extractor(monkeypatch, mock_extract)

    # Force the REVIEW band: disable auto-merge entirely.
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

    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))

    completed = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed) == 1
    assert completed[0]["resolution_action"] == "REVIEW"
    assert completed[0]["matched_candidate_id"] == "lookalike-id"
    assert completed[0]["classified_as"] == "VALID_RESUME"
    assert completed[0]["status"] == "SUCCESS"

def test_upload_stream_transparency_events(client: TestClient, monkeypatch):
    monkeypatch.setattr("storage.index_writer.generate_embeddings", lambda texts: [[0.0]*4 for _ in texts])
    _patch_extractor(monkeypatch, lambda text, **kwargs: {"first_name": "Sparse", "last_name": "Resume", "primary_email": "", "primary_phone": "", "current_title": "", "warnings": [{"level": "warning", "event": "ai_llm_extraction_failed", "action": "skipping_ai_extraction"}], "used_ai_fallback": True})
    files = [("files", ("sparse_resume.txt", b"Sparse Resume\nRandom text without clear structure but long enough\nEmail: sparse@example.com\nSkills: testing", "text/plain"))]
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))

    stages = [e.get("stage") for e in events]
    assert "HASHING" in stages
    assert "PARSING" in stages
    assert "CLASSIFYING" in stages
    assert "CHUNKING" in stages
    # Must report either AI_EXTRACTION or ENTITY_RESOLUTION
    assert ("AI_EXTRACTION" in stages) or ("ENTITY_RESOLUTION" in stages)

    completed = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed) == 1
    assert "used_ai_fallback" in completed[0]
