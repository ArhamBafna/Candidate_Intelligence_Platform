import pytest
from fastapi.testclient import TestClient
import structlog
from structlog.testing import LogCapture
from api.main import app

client = TestClient(app)

def test_upload_resume_emits_wide_event(monkeypatch):
    # Setup structlog for testing
    cap_logs = LogCapture()
    old_processors = structlog.get_config()["processors"]
    
    # We override processors to just capture the logs without rendering to string
    structlog.configure(processors=[cap_logs])
    
    try:
        # Mock file upload
        test_file_content = b"Mock PDF content"
        files = {"file": ("test_resume.pdf", test_file_content, "application/pdf")}
        
        response = client.post("/candidates/upload", files=files)
        
        # In a real scenario, this would create a db record etc.
        # We just want to check if the wide event was emitted.
        
        # Filter captured logs for our wide event
        upload_events = [log for log in cap_logs.entries if log.get("event") == "resume_upload_complete"]
        
        assert len(upload_events) == 1
        event = upload_events[0]
        
        assert "status" in event
        assert "file_hash" in event
        assert event["status"] == "success"
    finally:
        structlog.configure(processors=old_processors)

def test_upload_resume_emits_wide_event_skipped(monkeypatch):
    # Similar test for the stream endpoint where it skips
    # Actually let's test the main upload endpoint or the stream upload endpoint skipping logic.
    pass
