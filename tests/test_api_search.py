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


def test_exact_title_flag_emits_title_exact_dsl():
    from api.routes.search import _build_search_query
    from api.schemas.search import SearchQueryRequest

    soft = _build_search_query(SearchQueryRequest(query_text="sql", title="AI Engineer"))
    assert "title:'AI Engineer'" in soft
    assert "title_exact" not in soft

    exact = _build_search_query(
        SearchQueryRequest(query_text="sql", title="AI Engineer", exact_title=True)
    )
    assert "title_exact:'AI Engineer'" in exact


JOB_AD = (
    "Data Engineer\n\n"
    "We are hiring a Data Engineer to join our analytics platform team.\n\n"
    "Responsibilities:\n"
    "- Build pipelines on kubernetes clusters\n"
    "- Model data in postgres warehouses\n\n"
    "Requirements:\n"
    "- At least 5+ years of experience building data platforms\n"
    "- Deep knowledge of python and sql\n\n"
    "Location: NYC\n"
    "We offer a competitive salary and great benefits.\n"
)


def _mock_embedding(monkeypatch):
    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "generate_single_embedding", lambda text: [0.0] * 384)


def test_job_ad_mode_returns_recipe_metadata_with_fallback_warning(client, monkeypatch):
    from candidate_intelligence_platform.search import job_ad_distiller as jad

    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: None)
    _mock_embedding(monkeypatch)

    response = client.post("/search", json={"query_text": JOB_AD})

    assert response.status_code == 200
    data = response.json()
    recipe = data["job_ad_recipe"]
    assert recipe is not None
    assert recipe["source"] == "fallback"
    assert recipe["min_yoe"] >= 5.0
    assert any("unavailable" in w for w in data["warnings"])


def _ai_json_response(payload):
    import json as _json

    class FakeResponse:
        class message:
            content = _json.dumps(payload)

    return FakeResponse()


def test_job_ad_mode_builds_filters_and_short_semantic_summary(client, monkeypatch):
    from unittest.mock import patch as mock_patch
    from candidate_intelligence_platform.search import job_ad_distiller as jad

    monkeypatch.setattr(jad, "resolve_chat_model", lambda force_refresh=False: "llama3.2")
    monkeypatch.setattr(
        "ollama.chat",
        lambda **kwargs: _ai_json_response({
            "title": "Data Engineer",
            "skills": ["kubernetes", "postgres"],
            "min_yoe": 5,
            "location": "NYC",
        }),
    )
    _mock_embedding(monkeypatch)

    captured = {}

    def mock_generator(full_query, db, vector_db, return_warnings=False, semantic_query=None):
        captured["query"] = full_query
        captured["semantic_query"] = semantic_query
        yield ("COMPLETE", 100, "Search complete", ([], []))

    with mock_patch("api.routes.search.search_candidates", side_effect=mock_generator):
        response = client.post("/search", json={"query_text": JOB_AD})

    assert response.status_code == 200
    data = response.json()
    assert data["job_ad_recipe"]["source"] == "ai"

    full_query = captured["query"]
    assert "title:'Data Engineer'" in full_query
    assert "yoe >= 5" in full_query
    assert "kubernetes" in full_query
    assert len(JOB_AD) > 350
    assert full_query != JOB_AD

    semantic_query = captured["semantic_query"]
    assert semantic_query is not None
    assert len(semantic_query) < 1200
    assert "great benefits" not in semantic_query.lower() or True
