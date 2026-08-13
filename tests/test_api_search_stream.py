import pytest
import json
from fastapi.testclient import TestClient
from api.main import app

def test_search_stream_endpoint_exists(client: TestClient):
    """
    Test that the POST /search/stream endpoint exists and accepts valid requests.
    """
    payload = {
        "query_text": "software engineer",
        "top_k": 5
    }
    
    response = client.post("/search/stream", json=payload)
    
    # We expect a 200 OK since the endpoint should stream events
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

def test_search_stream_emits_progress_events(client: TestClient):
    """
    Test that the search stream yields the expected stage events.
    """
    payload = {
        "query_text": "software engineer",
        "top_k": 5
    }
    
    with client.stream("POST", "/search/stream", json=payload) as response:
        assert response.status_code == 200
        
        events = []
        for line in response.iter_lines():
            if line and line.startswith("data: "):
                data = json.loads(line[6:])
                events.append(data)
                
        # Expect at least these stages
        stages = [e.get("stage") for e in events]
        assert "STARTING" in stages
        assert "FTS_SEARCH" in stages
        assert "COMPLETE" in stages
        
        # Check that the COMPLETE stage contains the final data payload
        complete_event = next((e for e in events if e.get("stage") == "COMPLETE"), None)
        assert complete_event is not None
        assert "data" in complete_event
        assert "results" in complete_event["data"]
