import pytest
from fastapi.testclient import TestClient
from config.logging import get_recent_logs


def test_search_emits_wide_event(client: TestClient):
    response = client.post("/search", json={"query_text": "test query"})
    assert response.status_code == 200, response.text

    search_events = [log for log in get_recent_logs(200) if log.get("event") == "candidate_search_complete"]

    assert len(search_events) == 1
    event = search_events[0]

    assert "query" in event
    assert "candidates_returned" in event
    assert "vector_search_duration_ms" in event
    assert "db_retrieval_duration_ms" in event
    assert "total_duration_ms" in event
    assert event["query"] == "test query"
