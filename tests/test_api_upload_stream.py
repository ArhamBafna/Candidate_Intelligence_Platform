import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.dependencies import get_db
from storage.db_models import Base, init_db

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

def test_upload_stream_multi_resume(client, tmp_path, monkeypatch):
    # Mock settings so we don't pollute the real CAS directory
    from config.settings import Settings
    def mock_settings():
        return Settings(
            cas_root_dir=str(tmp_path / "cas"), 
            db_path=":memory:", 
            vector_db_path=str(tmp_path / "vector")
        )
    monkeypatch.setattr("api.routes.candidates.Settings", mock_settings)
    
    files = [
        ("files", ("resume1.txt", b"John Doe\nSoftware Engineer\nPython, React", "text/plain")),
        ("files", ("resume2.txt", b"Jane Smith\nData Scientist\nPython, SQL", "text/plain"))
    ]
    
    response = client.post("/candidates/upload-stream", files=files)
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))
            
    assert len(events) > 0
    
    completed_events = [e for e in events if e.get("stage") == "COMPLETED"]
    print(f"DEBUG EVENTS: {events}")
    assert len(completed_events) == 2
    
    names = {e.get("candidate_name") for e in completed_events}
    assert "John Doe" in names
    assert "Jane Smith" in names

def test_upload_stream_duplicate_resume(client, tmp_path, monkeypatch):
    from config.settings import Settings
    def mock_settings():
        return Settings(cas_root_dir=str(tmp_path / "cas"), db_path=":memory:", vector_db_path=str(tmp_path / "vector"))
    monkeypatch.setattr("api.routes.candidates.Settings", mock_settings)
    
    # First upload
    files = [("files", ("resume1.txt", b"John Doe\nSoftware Engineer\nPython, React", "text/plain"))]
    client.post("/candidates/upload-stream", files=files)
    
    # Second upload with same content
    response = client.post("/candidates/upload-stream", files=files)
    assert response.status_code == 200
    
    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))
            
    skipped_events = [e for e in events if e.get("status") == "SKIPPED_DUPLICATE"]
    assert len(skipped_events) == 1
    assert skipped_events[0].get("file_name") == "resume1.txt"
