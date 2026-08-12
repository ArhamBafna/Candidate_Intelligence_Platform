from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.dependencies import get_db
from api.schemas.candidates import (
    CandidateResponse, 
    CandidateStatusUpdate, 
    TimelineEventResponse,
    CandidateUpdate
)
from storage.db_models import Candidate, ResumeVersion, CandidateClaim, CandidateTimelineEvent
from crm.state_machine import CandidateStateMachine
from crm.timeline_ledger import TimelineLedger
from sqlalchemy import text
from ingestion.chunker import chunk_document
from ingestion.parsers.models import ParsedDocument
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings
from api.dependencies import get_vector_db
from storage.vector_store import CandidateSectionVector
from candidate_intelligence_platform.extraction.hybrid_extractor import extract_candidate_profile_hybrid

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

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: str, 
    db: Session = Depends(get_db),
    vector_db = Depends(get_vector_db)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    try:
        db.execute(text("DELETE FROM candidate_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
        db.execute(text("DELETE FROM claims_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
    except Exception:
        pass

    # Delete related child records
    db.query(ResumeVersion).filter(ResumeVersion.candidate_id == candidate_id).delete()
    db.query(CandidateClaim).filter(CandidateClaim.candidate_id == candidate_id).delete()
    db.query(CandidateTimelineEvent).filter(CandidateTimelineEvent.candidate_id == candidate_id).delete()
        
    db.delete(candidate)
    db.commit()

    if vector_db:
        if hasattr(vector_db, "delete_candidate_vectors"):
            vector_db.delete_candidate_vectors(candidate_id)
        else:
            try:
                table_names = vector_db.table_names()
                if "candidate_vectors" in table_names:
                    table = vector_db.open_table("candidate_vectors")
                    table.delete(f'candidate_id = "{candidate_id}"')
            except Exception:
                pass

    return None

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

@router.put("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(candidate_id: str, update_data: CandidateUpdate, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(candidate, key, value)
        
    ledger = TimelineLedger()
    ledger.log_event(
        session=db,
        candidate_id=candidate_id,
        event_type="PROFILE_UPDATED",
        title="Profile Updated",
        description="Recruiter manually updated candidate profile",
        metadata={},
        created_by="Recruiter"
    )
    
    db.commit()
    db.refresh(candidate)
    return candidate

@router.get("/{candidate_id}/file")
def get_candidate_file(candidate_id: str, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    from storage.cas import CASManager
    from config.settings import Settings
    from pathlib import Path
    
    rv = db.query(ResumeVersion).filter(
        ResumeVersion.candidate_id == candidate_id, 
        ResumeVersion.is_primary == True
    ).first()
    
    if not rv:
        raise HTTPException(status_code=404, detail="Primary resume not found")
        
    cas_mgr = CASManager(Settings().cas_root_dir)
    ext = f".{rv.file_type.lower()}"
    shard1 = rv.cas_file_hash[:2]
    shard2 = rv.cas_file_hash[2:4]
    filename = f"{rv.cas_file_hash}{ext}"
    
    target_path = cas_mgr.root_dir / shard1 / shard2 / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File content missing from CAS")
        
    return FileResponse(
        path=target_path, 
        filename=rv.original_filename, 
        media_type="application/pdf" if rv.file_type.upper() == "PDF" else "application/octet-stream"
    )

@router.post("/{candidate_id}/reprocess")
def reprocess_candidate(
    candidate_id: str, 
    db: Session = Depends(get_db),
    vector_db = Depends(get_vector_db)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    rv = db.query(ResumeVersion).filter(
        ResumeVersion.candidate_id == candidate_id,
        ResumeVersion.is_primary == True
    ).first()
    
    if rv and rv.raw_text:
        raw_text = rv.raw_text
        
        # 1. Refresh Full-Text Search (FTS)
        try:
            db.execute(text("DELETE FROM candidate_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
            db.execute(
                text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
                {
                    "cid": candidate_id,
                    "fname": f"{candidate.first_name} {candidate.last_name}",
                    "title": candidate.current_title or "",
                    "company": candidate.current_company or "",
                    "content": raw_text
                }
            )
        except Exception:
            pass

        # 2. Refresh Vector Embeddings
        if vector_db:
            if hasattr(vector_db, "delete_candidate_vectors"):
                vector_db.delete_candidate_vectors(candidate_id)
            else:
                try:
                    tables = vector_db.list_tables() if hasattr(vector_db, "list_tables") else vector_db.table_names()
                    if "candidate_vectors" in tables:
                        table = vector_db.open_table("candidate_vectors")
                        table.delete(f'candidate_id = "{candidate_id}"')
                except Exception:
                    pass
            
            doc = ParsedDocument(text=raw_text, pages=1)
            chunks = chunk_document(doc, candidate_id, "SUMMARY")
            if chunks:
                texts = [c.text for c in chunks]
                embeddings = generate_embeddings(texts)
                if hasattr(vector_db, "create_table"):
                    table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
                    records = []
                    for i, chunk in enumerate(chunks):
                        records.append({
                            "chunk_id": chunk.chunk_id,
                            "candidate_id": chunk.candidate_id,
                            "resume_version_id": rv.id,
                            "section_type": chunk.section_name,
                            "chunk_text": chunk.text,
                            "vector": embeddings[i],
                            "start_offset": chunk.start_offset,
                            "end_offset": chunk.end_offset
                        })
                    table.add(records)

    ledger = TimelineLedger()
    ledger.log_event(
        session=db,
        candidate_id=candidate_id,
        event_type="REPROCESS_TRIGGERED",
        title="Reprocessing Triggered",
        description="Recruiter triggered a manual re-processing of candidate data",
        metadata={},
        created_by="Recruiter"
    )
    db.commit()
    return {"status": "success", "message": "Reprocessing completed successfully"}

from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import uuid
import json
import asyncio
import hashlib
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
        
    extracted = extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
    cand_id = str(uuid.uuid4())
    cand = Candidate(
        id=cand_id,
        first_name=extracted["first_name"],
        last_name=extracted["last_name"],
        primary_email=extracted["primary_email"],
        primary_phone=extracted["primary_phone"],
        availability_status="ACTIVE",
        current_title=extracted["current_title"]
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
        metadata={},
        created_by="Recruiter"
    )
    db.commit()

    # FTS Insertion
    db.execute(
        text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
        {
            "cid": cand_id,
            "fname": f"{cand.first_name} {cand.last_name}",
            "title": cand.current_title,
            "company": cand.current_company or "",
            "content": raw_text
        }
    )
    db.commit()

    # Vector Insertion
    doc = ParsedDocument(text=raw_text, pages=1)
    chunks = chunk_document(doc, cand_id, "SUMMARY")
    if chunks:
        texts = [c.text for c in chunks]
        embeddings = generate_embeddings(texts)
        vector_db = get_vector_db()
        table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
        records = []
        for i, chunk in enumerate(chunks):
            records.append({
                "chunk_id": chunk.chunk_id,
                "candidate_id": chunk.candidate_id,
                "resume_version_id": rv.id,
                "section_type": chunk.section_name,
                "chunk_text": chunk.text,
                "vector": embeddings[i],
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset
            })
        table.add(records)

    return {"status": "success", "candidate_id": cand_id, "first_name": cand.first_name, "last_name": cand.last_name}

@router.post("/upload-stream")
async def upload_stream_resumes(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    async def stream_generator():
        for file in files:
            try:
                # 1. Hashing
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'HASHING', 'status': 'IN_PROGRESS', 'progress': 10})}\n\n"
                content = await file.read()
                cas_mgr = CASManager(Settings().cas_root_dir)
                ext = Path(file.filename).suffix if file.filename else ".txt"
                
                file_hash = hashlib.sha256(content).hexdigest()
                existing_rv = db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == file_hash).first()
                if existing_rv:
                    yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'HASHING', 'status': 'SKIPPED_DUPLICATE', 'message': 'File already exists', 'progress': 100})}\n\n"
                    continue
                
                _, cas_path = cas_mgr.store(content, extension=ext)
                
                # 2. Parsing
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'PARSING', 'status': 'IN_PROGRESS', 'progress': 30})}\n\n"
                await asyncio.sleep(0.01) # Yield to event loop
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
                    
                # 3. Chunking
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'CHUNKING', 'status': 'IN_PROGRESS', 'progress': 50})}\n\n"
                await asyncio.sleep(0.01)
                doc = ParsedDocument(text=raw_text, pages=1)
                chunks = chunk_document(doc, cand_id if 'cand_id' in locals() else "tmp", "SUMMARY")
                
                # 4. Entity Resolution (simplified extraction)
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'ENTITY_RESOLUTION', 'status': 'IN_PROGRESS', 'progress': 70})}\n\n"
                extracted = extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
                cand_id = str(uuid.uuid4())
                cand = Candidate(
                    id=cand_id,
                    first_name=extracted["first_name"],
                    last_name=extracted["last_name"],
                    primary_email=extracted["primary_email"],
                    primary_phone=extracted["primary_phone"],
                    availability_status="ACTIVE",
                    current_title=extracted["current_title"]
                )
                
                # 5. Saving
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'SAVING', 'status': 'IN_PROGRESS', 'progress': 90})}\n\n"
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
                    description=f"File {file.filename} uploaded via batch",
                    metadata={},
                    created_by="Recruiter"
                )
                db.commit()

                # FTS Insertion
                db.execute(
                    text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
                    {
                        "cid": cand_id,
                        "fname": f"{cand.first_name} {cand.last_name}",
                        "title": cand.current_title,
                        "company": cand.current_company or "",
                        "content": raw_text
                    }
                )
                db.commit()

                # Vector Insertion (use pre-computed chunks but fix candidate_id)
                if chunks:
                    for c in chunks:
                        c.candidate_id = cand_id
                    texts = [c.text for c in chunks]
                    embeddings = generate_embeddings(texts)
                    vector_db = get_vector_db()
                    table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
                    records = []
                    for i, chunk in enumerate(chunks):
                        records.append({
                            "chunk_id": chunk.chunk_id,
                            "candidate_id": chunk.candidate_id,
                            "resume_version_id": rv.id,
                            "section_type": chunk.section_name,
                            "chunk_text": chunk.text,
                            "vector": embeddings[i],
                            "start_offset": chunk.start_offset,
                            "end_offset": chunk.end_offset
                        })
                    table.add(records)
                
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'candidate_id': cand_id, 'candidate_name': f'{cand.first_name} {cand.last_name}'})}\n\n"
                
            except Exception as e:
                db.rollback()
                yield f"data: {json.dumps({'file_name': file.filename, 'stage': 'ERROR', 'status': 'FAILED', 'message': str(e), 'progress': 100})}\n\n"
                
    return StreamingResponse(stream_generator(), media_type="text/event-stream")
