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

def test_upload_and_search_exact_keyword_integration(client: TestClient):
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
