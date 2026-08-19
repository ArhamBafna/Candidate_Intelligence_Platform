from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from storage.db_models import Candidate
from crm.timeline_ledger import TimelineLedger

class InvalidStateTransition(Exception):
    pass

@dataclass
class TransitionContext:
    session: Session
    candidate_id: str
    new_status: str
    recruiter_name: str
    reason: Optional[str] = None

class CandidateStateMachine:
    VALID_STATUSES = {"ACTIVE", "PLACED", "INACTIVE", "DNC"}

    def __init__(self):
        self.ledger = TimelineLedger()

    def transition_state(self, context: TransitionContext) -> None:
        """
        Transitions the candidate to a new status and logs the event.
        """
        if context.new_status not in self.VALID_STATUSES:
            raise InvalidStateTransition(f"Status {context.new_status} is not valid. Must be one of {self.VALID_STATUSES}")

        candidate = context.session.query(Candidate).filter_by(id=context.candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate {context.candidate_id} not found.")

        old_status = candidate.availability_status
        if old_status == context.new_status:
            return  # No transition needed

        # Update candidate
        candidate.availability_status = context.new_status

        # Log timeline event
        self.ledger.log_event(
            session=context.session,
            candidate_id=context.candidate_id,
            event_type="STAGE_CHANGED",
            title=f"Status changed to {context.new_status}",
            description=context.reason,
            metadata={
                "from_status": old_status,
                "to_status": context.new_status
            },
            created_by=context.recruiter_name
        )
