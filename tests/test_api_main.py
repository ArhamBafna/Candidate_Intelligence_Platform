import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_cors_headers(client: TestClient):
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

def test_404_handler(client: TestClient):
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_unhandled_exception_still_logs_http_request(client, monkeypatch):
    """PR #25 review: failed requests keep an access record (path/status/duration)."""
    class StubLogger:
        def __init__(self) -> None:
            self.events: list = []

        def info(self, event: str, **kwargs: object) -> None:
            self.events.append((event, kwargs))

        def error(self, event: str, **kwargs: object) -> None:
            self.events.append((event, kwargs))

    stub = StubLogger()
    monkeypatch.setattr("api.main.logger", stub)

    from api.dependencies import get_db

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
