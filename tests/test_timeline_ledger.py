import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from crm.timeline_ledger import TimelineLedger
from storage.db_models import Base, Candidate, CandidateTimelineEvent
import uuid

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_log_event_and_get_timeline(db_session: Session):
    # Setup test candidate
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(
        id=candidate_id,
        first_name="Test",
        last_name="User",
        primary_email=f"{candidate_id}@example.com"
    )
    db_session.add(candidate)
    db_session.commit()

    ledger = TimelineLedger()
    
    # Log an event
    ledger.log_event(
        session=db_session,
        candidate_id=candidate_id,
        event_type="STAGE_CHANGED",
        title="Moved to Interview",
        description="Candidate passed phone screen",
        metadata={"from": "NEW", "to": "INTERVIEW"},
        created_by="recruiter_jane"
    )
    
    # Fetch events
    events = ledger.get_events(session=db_session, candidate_id=candidate_id)
    
    assert len(events) == 1
    assert events[0].event_type == "STAGE_CHANGED"
    assert events[0].title == "Moved to Interview"
    assert events[0].event_metadata == {"from": "NEW", "to": "INTERVIEW"}
    assert events[0].created_by == "recruiter_jane"

def test_events_returned_in_descending_order(db_session: Session):
    # Setup
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(
        id=candidate_id,
        first_name="Test2",
        last_name="User2",
        primary_email=f"{candidate_id}@example.com"
    )
    db_session.add(candidate)
    db_session.commit()

    ledger = TimelineLedger()
    
    from datetime import datetime, timezone, timedelta
    # Insert multiple events with explicit times
    now = datetime.now(timezone.utc)
    ledger.log_event(db_session, candidate_id, "RESUME_INGESTED", "Ingested", None, {}, "system", created_at=now - timedelta(minutes=5))
    ledger.log_event(db_session, candidate_id, "NOTE_ADDED", "Note", "Good candidate", {}, "jane", created_at=now)
    
    events = ledger.get_events(db_session, candidate_id)
    assert len(events) == 2
    # Ensure descending order (most recent first)
    assert events[0].event_type == "NOTE_ADDED"
    assert events[1].event_type == "RESUME_INGESTED"
