import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from storage.db_models import Base, Candidate, CandidateTimelineEvent
from crm.state_machine import CandidateStateMachine, InvalidStateTransition, TransitionContext
import uuid

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_transition_state_success(db_session: Session):
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(
        id=candidate_id,
        first_name="Test",
        last_name="State",
        availability_status="ACTIVE"
    )
    db_session.add(candidate)
    db_session.commit()

    sm = CandidateStateMachine()
    
    # Transition to PLACED
    context = TransitionContext(
        session=db_session,
        candidate_id=candidate_id,
        new_status="PLACED",
        recruiter_name="recruiter_bob",
        reason="Offer accepted"
    )
    sm.transition_state(context)
    db_session.commit()

    # Check state updated
    db_session.refresh(candidate)
    assert candidate.availability_status == "PLACED"

    # Check timeline event logged
    events = db_session.query(CandidateTimelineEvent).filter_by(candidate_id=candidate_id).all()
    assert len(events) == 1
    assert events[0].event_type == "STAGE_CHANGED"
    assert events[0].event_metadata["from_status"] == "ACTIVE"
    assert events[0].event_metadata["to_status"] == "PLACED"
    assert events[0].description == "Offer accepted"
    assert events[0].created_by == "recruiter_bob"

def test_invalid_state_transition(db_session: Session):
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(
        id=candidate_id,
        first_name="Test",
        last_name="State",
        availability_status="ACTIVE"
    )
    db_session.add(candidate)
    db_session.commit()

    sm = CandidateStateMachine()
    
    # Invalid transition
    with pytest.raises(InvalidStateTransition):
        context = TransitionContext(
            session=db_session,
            candidate_id=candidate_id,
            new_status="UNKNOWN_STATUS",
            recruiter_name="recruiter_bob"
        )
        sm.transition_state(context)
