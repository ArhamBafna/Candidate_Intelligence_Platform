import pytest
import json
from fastapi.testclient import TestClient

def test_upload_stream_multi_resume(client: TestClient):
    files = [
        ("files", ("resume1.txt", b"John Doe\nSoftware Engineer\nPython, React", "text/plain")),
        ("files", ("resume2.txt", b"Jane Smith\nData Scientist\nPython, SQL", "text/plain"))
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

def test_upload_stream_duplicate_resume(client: TestClient):
    files = [("files", ("resume1.txt", b"John Doe\nSoftware Engineer\nPython, React", "text/plain"))]
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

def test_upload_stream_transparency_events(client: TestClient):
    files = [("files", ("sparse_resume.txt", b"Random text without clear structure", "text/plain"))]
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200

    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))

    stages = [e.get("stage") for e in events]
    assert "HASHING" in stages
    assert "PARSING" in stages
    assert "CHUNKING" in stages
    # Must report either AI_EXTRACTION or ENTITY_RESOLUTION
    assert ("AI_EXTRACTION" in stages) or ("ENTITY_RESOLUTION" in stages)
    
    completed = [e for e in events if e.get("stage") == "COMPLETED"]
    assert len(completed) == 1
    assert "used_ai_fallback" in completed[0]

