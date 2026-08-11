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

from fastapi import UploadFile, File
import uuid
from pathlib import Path
from storage.cas import CASManager
from config.settings import Settings
from storage.db_models import ResumeVersion

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    cas_mgr = CASManager(Settings().cas_root_dir)
    ext = Path(file.filename).suffix if file.filename else ".txt"
    file_hash, cas_path = cas_mgr.store(content, extension=ext)
    
    raw_text = ""
    if ext.lower() == ".pdf":
        try:
            from ingestion.parsers.pdf_parser import parse_pdf
            doc = parse_pdf(Path(cas_path))
            raw_text = doc.text
        except Exception:
            raw_text = content.decode("utf-8", errors="ignore")
    elif ext.lower() in [".docx", ".doc"]:
        try:
            from ingestion.parsers.docx_parser import parse_docx
            doc = parse_docx(Path(cas_path))
            raw_text = doc.text
        except Exception:
            raw_text = content.decode("utf-8", errors="ignore")
    else:
        raw_text = content.decode("utf-8", errors="ignore")
        
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    first_name = lines[0] if lines else "Uploaded"
    last_name = "Candidate"
    if " " in first_name and len(first_name.split()) == 2:
        parts = first_name.split()
        first_name, last_name = parts[0], parts[1]
        
    cand_id = str(uuid.uuid4())
    cand = Candidate(
        id=cand_id,
        first_name=first_name[:50],
        last_name=last_name[:50],
        availability_status="ACTIVE",
        current_title=lines[1][:100] if len(lines) > 1 else "Candidate"
    )
    db.add(cand)
    
    rv = ResumeVersion(
        id=str(uuid.uuid4()),
        candidate_id=cand_id,
        cas_file_hash=file_hash,
        original_filename=file.filename or "resume",
        file_type=ext.replace(".", "").upper(),
        raw_text=raw_text,
        layout_metadata={},
        is_primary=True
    )
    db.add(rv)
    
    ledger = TimelineLedger()
    ledger.log_event(
        session=db,
        candidate_id=cand_id,
        event_type="RESUME_INGESTED",
        title="Resume Ingested",
        description=f"File {file.filename} uploaded and processed",
        created_by="Recruiter"
    )
    db.commit()
    return {"status": "success", "candidate_id": cand_id, "first_name": cand.first_name, "last_name": cand.last_name}

