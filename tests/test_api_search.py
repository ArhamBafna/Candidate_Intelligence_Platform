import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db, get_vector_db
from storage.db_models import Base, Candidate, init_db
from storage.vector_store import get_lancedb_connection
import uuid

@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    init_db(engine)
    yield engine

@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@patch("api.routes.search.search_candidates")
def test_search_candidates(mock_search, client, db_session):
    cid = str(uuid.uuid4())
    c = Candidate(id=cid, first_name="Search", last_name="Test", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    mock_search.return_value = [
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
    assert data["results"][0]["candidate_id"] == cid
    assert data["results"][0]["rrf_score"] == 0.0328
    assert data["results"][0]["candidate_info"]["first_name"] == "Search"

def test_upload_and_search_exact_keyword_integration(client, tmp_path, monkeypatch):
    from config.settings import Settings
    def mock_settings():
        return Settings(
            cas_root_dir=str(tmp_path / "cas"), 
            db_path=":memory:", 
            vector_db_path=str(tmp_path / "vector")
        )
    monkeypatch.setattr("api.routes.candidates.Settings", mock_settings)
    
    vec_path = str(tmp_path / "vector")
    monkeypatch.setattr("api.dependencies._settings", mock_settings())
    monkeypatch.setattr("api.routes.candidates.get_vector_db", lambda: get_lancedb_connection(vec_path))
    monkeypatch.setattr("api.routes.search.get_vector_db", lambda: get_lancedb_connection(vec_path))

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

