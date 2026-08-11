import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api.main import app

@pytest.fixture
def client():
    return TestClient(app)

@patch("api.routes.search.search_candidates")
def test_search_candidates(mock_search, client):
    # Setup mock return value based on Match Rationale JSON structure
    mock_search.return_value = [
        {
            "candidate_id": "c1a2b3c4",
            "rank": 1,
            "rrf_score": 0.0328,
            "match_scorecard": {
                "strict_filters": [],
                "keyword_matches": [],
                "semantic_matches": [],
                "ai_inferences": []
            }
        }
    ]

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
    assert data["results"][0]["candidate_id"] == "c1a2b3c4"
    assert data["results"][0]["rrf_score"] == 0.0328
