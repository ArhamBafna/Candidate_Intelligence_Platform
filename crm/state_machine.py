from typing import Optional
from sqlalchemy.orm import Session
from storage.db_models import Candidate
from crm.timeline_ledger import TimelineLedger

class InvalidStateTransition(Exception):
    pass

class CandidateStateMachine:
    VALID_STATUSES = {"ACTIVE", "PLACED", "INACTIVE", "DNC"}

    def __init__(self):
        self.ledger = TimelineLedger()

    def transition_state(
        self,
        session: Session,
        candidate_id: str,
        new_status: str,
        recruiter_name: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Transitions the candidate to a new status and logs the event.
        """
        if new_status not in self.VALID_STATUSES:
            raise InvalidStateTransition(f"Status {new_status} is not valid. Must be one of {self.VALID_STATUSES}")

        candidate = session.query(Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found.")

        old_status = candidate.availability_status
        if old_status == new_status:
            return  # No transition needed

        # Update candidate
        candidate.availability_status = new_status

        # Log timeline event
        self.ledger.log_event(
            session=session,
            candidate_id=candidate_id,
            event_type="STAGE_CHANGED",
            title=f"Status changed to {new_status}",
            description=reason,
            metadata={
                "from_status": old_status,
                "to_status": new_status
            },
            created_by=recruiter_name
        )
