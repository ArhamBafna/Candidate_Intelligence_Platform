import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db
from storage.db_models import Base, Candidate
import uuid

@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
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
