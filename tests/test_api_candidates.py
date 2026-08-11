import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from api.main import app
from api.dependencies import get_db
from storage.db_models import Base, Candidate, CandidateTimelineEvent
import uuid
from sqlalchemy.pool import StaticPool

# Setup test DB
engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_db():
    # Setup fresh DB state for each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

def test_list_candidates(client, test_db: Session):
    c = Candidate(id=str(uuid.uuid4()), first_name="John", last_name="Doe", availability_status="ACTIVE")
    test_db.add(c)
    test_db.commit()

    response = client.get("/candidates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["first_name"] == "John"
    assert data[0]["last_name"] == "Doe"

def test_get_candidate(client, test_db: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Jane", last_name="Smith", availability_status="PLACED")
    test_db.add(c)
    test_db.commit()

    response = client.get(f"/candidates/{c_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == c_id
    assert data["first_name"] == "Jane"
    assert data["availability_status"] == "PLACED"

def test_get_candidate_not_found(client):
    response = client.get("/candidates/unknown-id")
    assert response.status_code == 404

def test_update_candidate_status(client, test_db: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Alice", last_name="Wonder", availability_status="ACTIVE")
    test_db.add(c)
    test_db.commit()

    response = client.patch(
        f"/candidates/{c_id}/status", 
        json={"new_status": "PLACED", "recruiter_name": "Bob", "reason": "Hired!"}
    )
    assert response.status_code == 200
    
    # Check if DB was updated
    test_db.refresh(c)
    assert c.availability_status == "PLACED"

def test_get_candidate_timeline(client, test_db: Session):
    # Setup candidate and trigger a status update to create a timeline event
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Timeline", last_name="Test", availability_status="ACTIVE")
    test_db.add(c)
    test_db.commit()

    client.patch(
        f"/candidates/{c_id}/status", 
        json={"new_status": "PLACED", "recruiter_name": "Bob"}
    )

    response = client.get(f"/candidates/{c_id}/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["event_type"] == "STAGE_CHANGED"
    assert data[0]["created_by"] == "Bob"
