import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from storage.db_models import Candidate
from storage.vector_store import get_lancedb_connection

@patch("api.routes.search.search_candidates")
def test_search_candidates(mock_search, client: TestClient, db_session: Session):
    cid = str(uuid.uuid4())
    c = Candidate(id=cid, first_name="Search", last_name="Test", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    def mock_generator(*args, **kwargs):
        yield ("COMPLETE", 100, "Search complete", (
            [
                {
                    "candidate_id": cid,
                    "rank": 1,
                    "rrf_score": 0.0328,
                    "match_scorecard": {
                        "strict_filters": [],
                        "keyword_matches": [],
                        "semantic_matches": [],
                        "ai_inferences": []
                    }
                }
            ],
            ["Vector search skipped (test warning)"]
        ))
    mock_search.side_effect = mock_generator

    response = client.post(
        "/search",
        json={
            "query_text": "Python Engineer",
            "city": "NYC",
            "top_k": 10
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Python Engineer"
    assert data["total_results"] == 1
    assert "warnings" in data
    assert data["results"][0]["candidate_id"] == cid
    assert data["results"][0]["rrf_score"] == 0.0328
    assert data["results"][0]["candidate_info"]["first_name"] == "Search"

def test_upload_and_search_exact_keyword_integration(client: TestClient, monkeypatch):
    import api.routes.candidates as cand_routes
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Java",
            "last_name": "Developer",
            "primary_email": "java@example.com",
            "primary_phone": "",
            "current_title": "Java Developer",
            "warnings": []
        }
    )

    # 1. Upload Java resume
    resume_bytes = b"Java Developer\nSenior Software Engineer\nExperienced in Java, Spring Boot, microservices architecture."
    upload_res = client.post(
        "/candidates/upload",
        files={"file": ("java_resume.txt", resume_bytes, "text/plain")}
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    cand_id = upload_data["candidate_id"]

    # 2. Search exact query "java"
    search_res = client.post(
        "/search",
        json={"query_text": "java"}
    )
    assert search_res.status_code == 200
    search_data = search_res.json()

    assert search_data["total_results"] >= 1
    assert search_data["results"][0]["candidate_id"] == cand_id
    assert search_data["results"][0]["candidate_info"]["first_name"] == "Java"

@patch("api.routes.search.search_candidates")
def test_search_response_passes_through_populated_scorecard(mock_search, client: TestClient):
    scorecard = {
        "strict_filters": [{"field": "current_city", "operator": "=", "value": "NYC"}],
        "keyword_matches": ["python"],
        "semantic_matches": [{"signal": "semantic_similarity", "vector_rank": 1}],
        "ai_inferences": [],
    }

    def mock_generator(*args, **kwargs):
        yield ("COMPLETE", 100, "Search complete", (
            [{
                "candidate_id": "cand-x",
                "rank": 1,
                "rrf_score": 0.03,
                "rerank_score": None,
                "match_percentage": 72.5,
                "match_scorecard": scorecard,
            }],
            []
        ))

    mock_search.side_effect = mock_generator

    response = client.post("/search", json={"query_text": "python", "city": "NYC"})

    assert response.status_code == 200
    item = response.json()["results"][0]
    assert item["match_scorecard"]["keyword_matches"] == ["python"]
    assert item["match_scorecard"]["strict_filters"][0]["value"] == "NYC"
    assert item["rerank_score"] is None
    assert item["match_percentage"] == 72.5
