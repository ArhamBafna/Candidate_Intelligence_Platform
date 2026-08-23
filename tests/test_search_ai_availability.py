import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from storage.db_models import Candidate
from api.routes.search import AI_EXPLANATION_UNAVAILABLE_WARNING


def _seed_candidate(db_session: Session) -> str:
    cid = str(uuid.uuid4())
    db_session.add(Candidate(id=cid, first_name="AI", last_name="Check", availability_status="ACTIVE"))
    db_session.commit()
    return cid


def _patch_search(monkeypatch, cid: str):
    def mock_generator(*args, **kwargs):
        yield ("COMPLETE", 100, "Search complete", (
            [
                {
                    "candidate_id": cid,
                    "rank": 1,
                    "rrf_score": 0.03,
                    "match_scorecard": {},
                }
            ],
            [],
        ))

    monkeypatch.setattr("api.routes.search.search_candidates", mock_generator)


def test_search_response_carries_ai_unavailable_warning(client: TestClient, db_session: Session, monkeypatch):
    cid = _seed_candidate(db_session)
    _patch_search(monkeypatch, cid)

    monkeypatch.setattr(
        "api.routes.search.resolve_chat_model",
        lambda force_refresh=False: None,
    )

    response = client.post("/search", json={"query_text": "python"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert data["results"][0]["candidate_id"] == cid
    assert any(AI_EXPLANATION_UNAVAILABLE_WARNING in w for w in data["warnings"])


def test_search_response_clean_when_chat_model_available(client: TestClient, db_session: Session, monkeypatch):
    cid = _seed_candidate(db_session)
    _patch_search(monkeypatch, cid)

    monkeypatch.setattr(
        "api.routes.search.resolve_chat_model",
        lambda force_refresh=False: "llama3.2",
    )

    response = client.post("/search", json={"query_text": "python"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert not any("unavailable" in w.lower() for w in data["warnings"])


def test_stream_search_response_carries_ai_unavailable_warning(client: TestClient, db_session: Session, monkeypatch):
    cid = _seed_candidate(db_session)
    _patch_search(monkeypatch, cid)

    monkeypatch.setattr(
        "api.routes.search.resolve_chat_model",
        lambda force_refresh=False: None,
    )

    with client.stream("POST", "/search/stream", json={"query_text": "python"}) as response:
        body = "".join(response.iter_text())

    assert '"status": "SUCCESS"' in body or '"status":"SUCCESS"' in body
    assert "AI explanations are unavailable" in body
