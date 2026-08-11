from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.dependencies import get_db
from api.schemas.candidates import (
    CandidateResponse, 
    CandidateStatusUpdate, 
    TimelineEventResponse
)
from storage.db_models import Candidate
from crm.state_machine import CandidateStateMachine
from crm.timeline_ledger import TimelineLedger

router = APIRouter(prefix="/candidates", tags=["candidates"])

@router.get("", response_model=List[CandidateResponse])
def list_candidates(db: Session = Depends(get_db)):
    candidates = db.query(Candidate).all()
    return candidates

@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.patch("/{candidate_id}/status")
def update_candidate_status(
    candidate_id: str, 
    update: CandidateStatusUpdate, 
    db: Session = Depends(get_db)
):
    try:
        sm = CandidateStateMachine()
        sm.transition_state(
            session=db,
            candidate_id=candidate_id,
            new_status=update.new_status,
            recruiter_name=update.recruiter_name,
            reason=update.reason
        )
        db.commit()
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{candidate_id}/timeline", response_model=List[TimelineEventResponse])
def get_candidate_timeline(candidate_id: str, db: Session = Depends(get_db)):
    ledger = TimelineLedger()
    events = ledger.get_events(session=db, candidate_id=candidate_id)
    return events
