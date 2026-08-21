import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from storage.db_models import CandidateTimelineEvent

class TimelineLedger:
    """
    Event-sourced logger for candidate timeline events.
    """

    def log_event(
        self,
        session: Session,
        candidate_id: str,
        event_type: str,
        title: str,
        description: Optional[str],
        metadata: Dict[str, Any],
        created_by: str,
        created_at: Optional[Any] = None
    ) -> CandidateTimelineEvent:
        """
        Logs a new event in the candidate's timeline.
        """
        event = CandidateTimelineEvent(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            event_type=event_type,
            title=title,
            description=description,
            event_metadata=metadata or {},
            created_by=created_by
        )
        if created_at is not None:
            event.created_at = created_at
        
        session.add(event)
        # Note: caller is responsible for committing the transaction
        return event

    def get_events(self, session: Session, candidate_id: str) -> List[CandidateTimelineEvent]:
        """
        Retrieves all timeline events for a candidate, ordered by creation date descending.
        """
        return session.query(CandidateTimelineEvent)\
            .filter(CandidateTimelineEvent.candidate_id == candidate_id)\
            .order_by(desc(CandidateTimelineEvent.created_at))\
            .all()
