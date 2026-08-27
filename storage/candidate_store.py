from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
import logging

from storage.db_models import Candidate, ResumeVersion, CandidateClaim, CandidateTimelineEvent
from storage.index_writer import StorageIndexWriter

logger = logging.getLogger(__name__)

def delete_candidate_and_indices(db: Session, candidate_id: str, vector_db: Any, commit: bool = True) -> bool:
    """Deletes a candidate and cascades deletions to all related records and indices."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        return False

    try:
        # 1. Delete from indices (FTS and Vectors)
        writer = StorageIndexWriter(db_session=db, vector_db=vector_db)
        writer.delete_candidate_indices(candidate_id)

        # 2. Delete related child records explicitly (though CASCADE should handle it, we do it for completeness)
        db.query(ResumeVersion).filter(ResumeVersion.candidate_id == candidate_id).delete()
        db.query(CandidateClaim).filter(CandidateClaim.candidate_id == candidate_id).delete()
        db.query(CandidateTimelineEvent).filter(CandidateTimelineEvent.candidate_id == candidate_id).delete()

        # 3. Delete Candidate
        db.delete(candidate)
        
        if commit:
            db.commit()
            
    except Exception as e:
        db.rollback()
        logger.error("failed_to_delete_candidate", extra={"candidate_id": candidate_id, "error": str(e)})
        raise
        
    return True
