import pytest
from fastapi.testclient import TestClient
import structlog
from structlog.testing import LogCapture
from api.main import app

client = TestClient(app)

import json

def test_upload_resume_emits_wide_event(capsys):
    test_file_content = b"Mock PDF content"
    files = {"file": ("test_resume.pdf", test_file_content, "application/pdf")}
    
    response = client.post("/candidates/upload", files=files)
    assert response.status_code == 200, response.text
    
    captured = capsys.readouterr()
    log_lines = []
    for line in captured.out.splitlines():
        line_str = line.strip()
        if line_str.startswith("{") and line_str.endswith("}"):
            try:
                log_lines.append(json.loads(line_str))
            except Exception:
                pass
                
    upload_events = [log for log in log_lines if log.get("event") == "resume_upload_complete"]
    
    assert len(upload_events) == 1
    event = upload_events[0]
    
    assert "status" in event
    assert "file_hash" in event
    assert event["status"] == "success"



def test_upload_resume_emits_wide_event_skipped(monkeypatch):
    # Similar test for the stream endpoint where it skips
    # Actually let's test the main upload endpoint or the stream upload endpoint skipping logic.
    pass
