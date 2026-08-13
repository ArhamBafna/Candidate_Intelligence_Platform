import pytest
from fastapi.testclient import TestClient
import structlog
from api.main import app

client = TestClient(app)

def test_get_logs_endpoint_returns_recent_events():
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
