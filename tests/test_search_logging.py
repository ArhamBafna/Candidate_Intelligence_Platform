import pytest
from fastapi.testclient import TestClient
import structlog
from structlog.testing import LogCapture
import json

def test_search_emits_wide_event(capsys, client: TestClient):
    response = client.post("/search", json={"query_text": "test query"})
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
                
    search_events = [log for log in log_lines if log.get("event") == "candidate_search_complete"]
    
    assert len(search_events) == 1
    event = search_events[0]
    
    assert "query" in event
    assert "candidates_returned" in event
    assert "vector_search_duration_ms" in event
    assert "db_retrieval_duration_ms" in event
    assert "total_duration_ms" in event
    assert event["query"] == "test query"
