import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db
from storage.db_models import Base, Candidate, CandidateTimelineEvent
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

def test_list_candidates(client, db_session: Session):
    c = Candidate(id=str(uuid.uuid4()), first_name="John", last_name="Doe", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    response = client.get("/candidates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["first_name"] == "John"
    assert data[0]["last_name"] == "Doe"

def test_get_candidate(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Jane", last_name="Smith", availability_status="PLACED")
    db_session.add(c)
    db_session.commit()

    response = client.get(f"/candidates/{c_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == c_id
    assert data["first_name"] == "Jane"
    assert data["availability_status"] == "PLACED"

def test_get_candidate_not_found(client):
    response = client.get("/candidates/unknown-id")
    assert response.status_code == 404

def test_update_candidate_status(client, db_session: Session):
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Alice", last_name="Wonder", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

    response = client.patch(
        f"/candidates/{c_id}/status", 
        json={"new_status": "PLACED", "recruiter_name": "Bob", "reason": "Hired!"}
    )
    assert response.status_code == 200
    
    # Check if DB was updated
    db_session.refresh(c)
    assert c.availability_status == "PLACED"

def test_get_candidate_timeline(client, db_session: Session):
    # Setup candidate and trigger a status update to create a timeline event
    c_id = str(uuid.uuid4())
    c = Candidate(id=c_id, first_name="Timeline", last_name="Test", availability_status="ACTIVE")
    db_session.add(c)
    db_session.commit()

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
