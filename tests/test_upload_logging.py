import pytest
import structlog
from config.logging import LOG_BUFFER, get_recent_logs


def test_upload_resume_emits_wide_event(client, monkeypatch):
    LOG_BUFFER.clear()
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {"first_name": "Test", "last_name": "User", "primary_email": "", "primary_phone": "", "current_title": "Engineer", "warnings": []}
    )
    test_file_content = b"Test User\nSenior Engineer\nEmail: test.user@example.com\nSkills: Python, Docker\nExperience: 6 years building backend services"
    files = {"file": ("test_resume.pdf", test_file_content, "application/pdf")}

    response = client.post("/candidates/upload", files=files)
    assert response.status_code == 200, response.text

    upload_events = [log for log in get_recent_logs(200) if log.get("event") == "resume_upload_complete"]

    assert len(upload_events) == 1
    event = upload_events[0]

    assert "status" in event
    assert "file_hash" in event
    assert event["status"] == "success"
    # GET /logs serves this buffer unauthenticated, so candidate-identifying
    # fields must never land here (PR #25 review).
    assert "candidate_name" not in event
    assert "file_name" not in event
