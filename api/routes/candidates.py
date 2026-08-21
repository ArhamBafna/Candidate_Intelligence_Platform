from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_db, get_vector_db, get_settings, _get_sessionmaker
from config.settings import Settings
from api.schemas.candidates import (
    CandidateResponse, 
    CandidateStatusUpdate, 
    TimelineEventResponse,
    CandidateUpdate,
    BatchCandidateIds,
    BatchReprocessRequest
)
from storage.db_models import Candidate, ResumeVersion, CandidateClaim, CandidateTimelineEvent
from crm.state_machine import CandidateStateMachine, TransitionContext
from crm.timeline_ledger import TimelineLedger
from api.services.candidate_service import CandidateService
from sqlalchemy import text
from ingestion.chunker import chunk_document
from ingestion.parsers.models import ParsedDocument
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings
from api.dependencies import get_vector_db
from storage.vector_store import CandidateSectionVector
from candidate_intelligence_platform.extraction.hybrid_extractor import (
    extract_candidate_profile_hybrid,
    calculate_tier1_confidence,
    _extract_deterministic_profile,
    normalize_name,
    normalize_title,
    assess_tier1
)
from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts
import structlog

logger = structlog.get_logger(__name__)

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
    success = CandidateService.delete_candidate(db, candidate_id, vector_db)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return None

@router.patch("/{candidate_id}/status")
def update_candidate_status(
    candidate_id: str, 
    update: CandidateStatusUpdate, 
    db: Session = Depends(get_db)
):
    try:
        sm = CandidateStateMachine()
        context = TransitionContext(
            session=db,
            candidate_id=candidate_id,
            new_status=update.new_status,
            recruiter_name=update.recruiter_name,
            reason=update.reason
        )
        sm.transition_state(context)
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
    if "first_name" in update_dict:
        update_dict["first_name"] = normalize_name(update_dict["first_name"])
    if "last_name" in update_dict:
        update_dict["last_name"] = normalize_name(update_dict["last_name"])
    if "current_title" in update_dict:
        update_dict["current_title"] = normalize_title(update_dict["current_title"])
        
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
def get_candidate_file(candidate_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    from fastapi.responses import FileResponse
    from storage.cas import CASManager
    from pathlib import Path
    
    rv = db.query(ResumeVersion).filter(
        ResumeVersion.candidate_id == candidate_id, 
        ResumeVersion.is_primary == True
    ).first()
    
    if not rv:
        raise HTTPException(status_code=404, detail="Primary resume not found")
        
    cas_mgr = CASManager(settings.cas_root_dir)
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
        reprocess_warnings = []
        
        # 1. Entity Resolution
        extracted = extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
        if extracted.get("warnings"):
            reprocess_warnings.extend(extracted["warnings"])
        
        candidate.first_name = extracted.get("first_name", candidate.first_name)
        candidate.last_name = extracted.get("last_name", candidate.last_name)
        if extracted.get("primary_email"): candidate.primary_email = extracted["primary_email"]
        if extracted.get("primary_phone"): candidate.primary_phone = extracted["primary_phone"]
        if extracted.get("current_title"): candidate.current_title = extracted["current_title"]
        db.commit()
        
        # 2. Refresh Full-Text Search (FTS)
        try:
            CandidateService.update_fts_index(db, candidate_id, f"{candidate.first_name} {candidate.last_name}", candidate, raw_text)
        except Exception:
            reprocess_warnings.append("Full-Text Search (FTS) index update failed.")

        # 3. Refresh Vector Embeddings
        if vector_db:
            try:
                CandidateService.update_vector_index(vector_db, candidate_id, raw_text, rv.id)
            except Exception:
                reprocess_warnings.append("Vector re-indexing skipped (embedding model or vector store error).")
        else:
            reprocess_warnings.append("Vector re-indexing skipped (LanceDB connection unavailable).")

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
    return {"status": "success", "message": "Reprocessing completed successfully", "warnings": reprocess_warnings if 'reprocess_warnings' in locals() else []}

@router.post("/{candidate_id}/reprocess-stream")
async def reprocess_candidate_stream(
    candidate_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
):
    async def stream_generator():
        reprocess_warnings = []
        try:
            # 1. Fetch Candidate & Resume
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                yield f"data: {json.dumps({'candidate_id': candidate_id, 'stage': 'ERROR', 'status': 'FAILED', 'message': 'Candidate not found', 'progress': 100, 'warnings': []})}\n\n"
                return

            candidate_name = f"{candidate.first_name} {candidate.last_name}".strip()
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'FETCHING_RESUME', 'status': 'IN_PROGRESS', 'progress': 15, 'message': 'Fetching resume and candidate profile', 'warnings': []})}\n\n"
            await asyncio.sleep(0.05)

            rv = db.query(ResumeVersion).filter(
                ResumeVersion.candidate_id == candidate_id,
                ResumeVersion.is_primary == True
            ).first()

            raw_text = rv.raw_text if (rv and rv.raw_text) else ""

            # 2. Entity Resolution (compute facts ONCE, reuse for assessment and extraction)
            used_ai = False
            if raw_text:
                facts = await asyncio.to_thread(extract_facts, raw_text)
                profile, tier1_conf, needs_ai = assess_tier1(raw_text, facts, confidence_threshold=0.40)
                
                if needs_ai:
                    llm_model = settings.llm_model
                    yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'AI_EXTRACTION', 'stage_detail': f'AI Model Inference ({llm_model})', 'status': 'IN_PROGRESS', 'progress': 30, 'message': f'Running local AI Model extraction ({llm_model})...', 'used_ai': True, 'model_name': llm_model, 'warnings': reprocess_warnings})}\n\n"
                    await asyncio.sleep(0.02)
                else:
                    yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'ENTITY_RESOLUTION', 'stage_detail': 'Rule-based NER Extraction', 'status': 'IN_PROGRESS', 'progress': 30, 'message': 'Extracting profile entities (Rule-based NER)...', 'used_ai': False, 'warnings': reprocess_warnings})}\n\n"
                    await asyncio.sleep(0.02)

                # Pass precomputed facts to avoid re-running spaCy NER
                def do_extract():
                    return extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40, facts=facts)
                extracted = await asyncio.to_thread(do_extract)
                used_ai = extracted.get("used_ai_fallback", False)
                
                if extracted.get("warnings"):
                    reprocess_warnings.extend(extracted["warnings"])
                
                candidate.first_name = extracted.get("first_name", candidate.first_name)
                candidate.last_name = extracted.get("last_name", candidate.last_name)
                if extracted.get("primary_email"): candidate.primary_email = extracted["primary_email"]
                if extracted.get("primary_phone"): candidate.primary_phone = extracted["primary_phone"]
                if extracted.get("current_title"): candidate.current_title = extracted["current_title"]
                
                candidate_name = f"{candidate.first_name} {candidate.last_name}".strip()
                db.commit()

            # 3. Refresh Full-Text Search (FTS)
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'UPDATING_FTS', 'status': 'IN_PROGRESS', 'progress': 50, 'message': 'Refreshing FTS search index', 'warnings': reprocess_warnings})}\n\n"
            await asyncio.sleep(0.05)
            if raw_text:
                try:
                    CandidateService.update_fts_index(db, candidate_id, candidate_name, candidate, raw_text)
                except Exception:
                    db.rollback()
                    reprocess_warnings.append("Full-Text Search (FTS) index update failed.")

            # 4. Refresh Vector Embeddings
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'GENERATING_VECTORS', 'status': 'IN_PROGRESS', 'progress': 75, 'message': 'Chunking document and re-generating LanceDB vector embeddings', 'warnings': reprocess_warnings})}\n\n"
            await asyncio.sleep(0.05)
            if raw_text:
                try:
                    if vector_db:
                        CandidateService.update_vector_index(vector_db, candidate_id, raw_text, rv.id if rv else "")
                    else:
                        reprocess_warnings.append("Vector re-indexing skipped (LanceDB connection unavailable).")
                except Exception:
                    reprocess_warnings.append("Vector re-indexing skipped (embedding model or vector store error).")

            # 5. Log Timeline Event
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'LOGGING_TIMELINE', 'status': 'IN_PROGRESS', 'progress': 90, 'message': 'Logging timeline audit event', 'warnings': reprocess_warnings})}\n\n"
            await asyncio.sleep(0.05)
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

            # 6. Completed
            mode_str = "AI Model" if used_ai else "Rule-based NER"
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'message': f'Reprocessing completed successfully ({mode_str})', 'used_ai_fallback': used_ai, 'model_name': settings.llm_model if used_ai else None, 'warnings': reprocess_warnings})}\n\n"
        except Exception as e:
            db.rollback()
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'stage': 'ERROR', 'status': 'FAILED', 'progress': 100, 'message': str(e), 'warnings': reprocess_warnings})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


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
async def upload_resume(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
):
    content = await file.read()
    cas_mgr = CASManager(settings.cas_root_dir)
    ext = Path(file.filename).suffix if file.filename else ".txt"
    
    # CAS store + parse on thread pool (CPU/IO bound)
    def store_and_parse():
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
        return file_hash, raw_text
    
    file_hash, raw_text = await asyncio.to_thread(store_and_parse)
    
    # Check for duplicate (dedup)
    existing_rv = db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == file_hash).first()
    if existing_rv:
        return {"status": "skipped", "message": "File already exists", "candidate_id": existing_rv.candidate_id}
        
    upload_warnings = []
    
    # Extract on thread pool (CPU-bound spaCy NER)
    def extract_profile():
        return extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
    extracted = await asyncio.to_thread(extract_profile)
    if extracted.get("warnings"):
        upload_warnings.extend(extracted["warnings"])
        
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

    # Vector Insertion (CPU-bound embedding: run on thread pool)
    doc = ParsedDocument(text=raw_text, pages=1)
    chunks = chunk_document(doc, cand_id, "SUMMARY")
    if chunks and vector_db:
        def embed_and_store():
            texts = [c.text for c in chunks]
            embeddings = generate_embeddings(texts)
            if hasattr(vector_db, "create_table"):
                table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
                records = []
                for i, chunk in enumerate(chunks):
                    records.append(CandidateSectionVector.create_record(chunk, rv.id, embeddings[i]))
                table.add(records)
        await asyncio.to_thread(embed_and_store)

    logger.info("resume_upload_complete", status="success", file_hash=file_hash, parser_used=ext, candidate_id=cand_id)
    return {"status": "success", "candidate_id": cand_id, "first_name": cand.first_name, "last_name": cand.last_name, "warnings": upload_warnings}

@router.post("/upload-stream")
async def upload_stream_resumes(
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db), 
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
):
    # Bounded semaphore to limit concurrent file processing
    upload_semaphore = asyncio.Semaphore(4)
    event_queue = asyncio.Queue()
    
    # Get sessionmaker for creating new sessions per task
    SessionLocal = _get_sessionmaker(settings.db_path)

    async def process_file(file: UploadFile):
        async with upload_semaphore:
            file_warnings = []
            # Create a dedicated session for this file to ensure thread safety
            # when using asyncio.to_thread with DB operations
            task_db = SessionLocal()
            try:
                # 1. Hashing
                await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'HASHING', 'status': 'IN_PROGRESS', 'progress': 10}))
                content = await file.read()
                cas_mgr = CASManager(settings.cas_root_dir)
                ext = Path(file.filename).suffix if file.filename else ".txt"
                
                # Hash on thread pool (CPU-bound)
                file_hash = await asyncio.to_thread(lambda c: hashlib.sha256(c).hexdigest(), content)
                
                # Check for duplicate on thread pool (DB read)
                def check_existing_rv(h):
                    return task_db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == h).first()
                existing_rv = await asyncio.to_thread(check_existing_rv, file_hash)
                if existing_rv:
                    logger.info("resume_upload_complete", status="skipped", skip_reason="cas_duplicate", file_hash=file_hash)
                    await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'HASHING', 'status': 'SKIPPED_DUPLICATE', 'message': 'File already exists', 'progress': 100, 'warnings': []}))
                    return
                
                _, cas_path = cas_mgr.store(content, extension=ext)
                
                # 2. Parsing (CPU-bound: run on thread pool)
                await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'PARSING', 'status': 'IN_PROGRESS', 'progress': 30}))
                
                def parse_file():
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
                    return raw_text
                
                raw_text = await asyncio.to_thread(parse_file)
                    
                # 3. Entity Resolution
                # Compute facts ONCE
                facts = await asyncio.to_thread(extract_facts, raw_text)
                
                # assess_tier1 is fast, but we need its output to decide the stage message
                profile_preview, tier1_conf, needs_ai = assess_tier1(raw_text, facts, confidence_threshold=0.40)
                
                if needs_ai:
                    llm_model = settings.llm_model
                    await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'AI_EXTRACTION', 'stage_detail': f'AI Model Inference ({llm_model})', 'status': 'IN_PROGRESS', 'progress': 70, 'message': f'Running local AI Model extraction ({llm_model})...', 'used_ai': True, 'model_name': llm_model}))
                else:
                    await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'ENTITY_RESOLUTION', 'stage_detail': 'Rule-based NER Extraction', 'status': 'IN_PROGRESS', 'progress': 70, 'message': 'Extracting profile entities (Rule-based NER)...', 'used_ai': False}))

                # 4. Hybrid Extraction
                def extract_profile():
                    return extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40, facts=facts)
                extracted = await asyncio.to_thread(extract_profile)
                if extracted.get("warnings"):
                    file_warnings.extend(extracted["warnings"])
                used_ai = extracted.get("used_ai_fallback", False)

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
                await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'SAVING', 'status': 'IN_PROGRESS', 'progress': 90}))
                task_db.add(cand)
                
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
                task_db.add(rv)
                
                ledger = TimelineLedger()
                ledger.log_event(
                    session=task_db,
                    candidate_id=cand_id,
                    event_type="RESUME_INGESTED",
                    title="Resume Ingested",
                    description=f"File {file.filename} uploaded via batch",
                    metadata={},
                    created_by="Recruiter"
                )
                task_db.commit()

                def do_fts_insertion():
                    task_db.execute(
                        text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
                        {
                            "cid": cand_id,
                            "fname": f"{cand.first_name} {cand.last_name}",
                            "title": cand.current_title,
                            "company": cand.current_company or "",
                            "content": raw_text
                        }
                    )
                    task_db.commit()
                await asyncio.to_thread(do_fts_insertion)

                # 6. Chunking & Vector Insertion
                doc = ParsedDocument(text=raw_text, pages=1)
                def do_chunking():
                    return chunk_document(doc, cand_id, "SUMMARY")
                chunks = await asyncio.to_thread(do_chunking)
                
                if chunks and vector_db:
                    try:
                        def embed_and_store():
                            texts = [c.text for c in chunks]
                            embeddings = generate_embeddings(texts)
                            if hasattr(vector_db, "create_table"):
                                table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
                                records = []
                                for i, chunk in enumerate(chunks):
                                    records.append(CandidateSectionVector.create_record(chunk, rv.id, embeddings[i]))
                                table.add(records)
                        
                        await asyncio.to_thread(embed_and_store)
                    except Exception:
                        file_warnings.append("Vector indexing skipped (embedding engine or vector store unavailable).")
                
                logger.info("resume_upload_complete", status="success", file_hash=file_hash, parser_used=ext, candidate_id=cand_id)
                await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'candidate_id': cand_id, 'candidate_name': f'{cand.first_name} {cand.last_name}', 'used_ai_fallback': used_ai, 'model_name': settings.llm_model if used_ai else None, 'warnings': file_warnings}))
                
            except Exception as e:
                task_db.rollback()
                logger.error("resume_upload_complete", status="failed", file_hash=file_hash if 'file_hash' in locals() else None, error=str(e))
                await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'ERROR', 'status': 'FAILED', 'message': str(e), 'progress': 100, 'warnings': file_warnings}))
            finally:
                task_db.close()

    # Launch all tasks
    tasks = [asyncio.create_task(process_file(f)) for f in files]
    
    # Helper to close the queue when all tasks finish
    async def closer():
        await asyncio.gather(*tasks)
        await event_queue.put(None)
    
    asyncio.create_task(closer())

    async def stream_generator():
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {event}\n\n"
                
    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/batch-delete", status_code=status.HTTP_200_OK)
def batch_delete_candidates(
    payload: BatchCandidateIds,
    db: Session = Depends(get_db),
    vector_db = Depends(get_vector_db)
):
    deleted_ids = []
    try:
        for candidate_id in payload.candidate_ids:
            if CandidateService.delete_candidate(db, candidate_id, vector_db, commit=False):
                deleted_ids.append(candidate_id)
        db.commit()  # Single commit for all deletes
    except Exception:
        db.rollback()
        raise

    return {
        "status": "success",
        "deleted_count": len(deleted_ids),
        "candidate_ids": deleted_ids
    }


@router.post("/batch-reprocess-stream")
async def batch_reprocess_candidate_stream(
    payload: BatchReprocessRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
):
    # Bounded semaphore to limit concurrent processing
    process_semaphore = asyncio.Semaphore(4)
    event_queue = asyncio.Queue()
    
    # Get sessionmaker for creating new sessions per task
    SessionLocal = _get_sessionmaker(settings.db_path)

    async def process_candidate(idx: int, candidate_id: str, total_candidates: int):
        async with process_semaphore:
            reprocess_warnings = []
            # Create a dedicated session for this candidate to ensure thread safety
            task_db = SessionLocal()
            try:
                def fetch_candidate():
                    return task_db.query(Candidate).filter(Candidate.id == candidate_id).first()
                candidate = await asyncio.to_thread(fetch_candidate)
                if not candidate:
                    await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': 'Unknown Candidate', 'stage': 'ERROR', 'status': 'FAILED', 'progress': 100, 'message': 'Candidate not found', 'warnings': []}))
                    return

                candidate_name = f"{candidate.first_name} {candidate.last_name}"
                
                # 1. Fetch resume
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'FETCHING_RESUME', 'status': 'IN_PROGRESS', 'progress': 10, 'message': f'Fetching primary resume for {candidate_name}', 'warnings': reprocess_warnings}))
                
                def fetch_rv():
                    return task_db.query(ResumeVersion).filter(
                        ResumeVersion.candidate_id == candidate_id,
                        ResumeVersion.is_primary == True
                    ).first()
                rv = await asyncio.to_thread(fetch_rv)
                
                if not rv or not rv.raw_text:
                    reprocess_warnings.append("No primary resume text available for entity resolution.")
                    await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'COMPLETED', 'status': 'SKIPPED', 'progress': 100, 'message': 'No raw resume text available', 'warnings': reprocess_warnings}))
                    return
                
                raw_text = rv.raw_text

                # 2. Entity Resolution
                used_ai = False
                facts = await asyncio.to_thread(extract_facts, raw_text)
                profile_preview, tier1_conf, needs_ai = assess_tier1(raw_text, facts, confidence_threshold=0.40)

                if needs_ai:
                    llm_model = settings.llm_model
                    await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'AI_EXTRACTION', 'stage_detail': f'AI Model Inference ({llm_model})', 'status': 'IN_PROGRESS', 'progress': 30, 'message': f'Running local AI Model extraction ({llm_model})...', 'used_ai': True, 'model_name': llm_model, 'warnings': reprocess_warnings}))
                else:
                    await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'ENTITY_RESOLUTION', 'stage_detail': 'Rule-based NER Extraction', 'status': 'IN_PROGRESS', 'progress': 30, 'message': 'Re-extracting candidate profile entities (Rule-based)...', 'used_ai': False, 'warnings': reprocess_warnings}))

                # 3. Hybrid Extraction
                def do_extract():
                    return extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40, facts=facts)
                extracted = await asyncio.to_thread(do_extract)
                used_ai = extracted.get("used_ai_fallback", False)
                if extracted.get("warnings"):
                    reprocess_warnings.extend(extracted["warnings"])
                
                candidate.first_name = extracted.get("first_name", candidate.first_name)
                candidate.last_name = extracted.get("last_name", candidate.last_name)
                if extracted.get("primary_email"): candidate.primary_email = extracted["primary_email"]
                if extracted.get("primary_phone"): candidate.primary_phone = extracted["primary_phone"]
                if extracted.get("current_title"): candidate.current_title = extracted["current_title"]
                task_db.commit()
                candidate_name = f"{candidate.first_name} {candidate.last_name}"

                # 4. Refresh FTS
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'UPDATING_FTS', 'status': 'IN_PROGRESS', 'progress': 50, 'message': 'Refreshing FTS search index', 'warnings': reprocess_warnings}))
                try:
                    def do_fts_update():
                        CandidateService.update_fts_index(task_db, candidate_id, candidate_name, candidate, raw_text)
                        task_db.commit()
                    await asyncio.to_thread(do_fts_update)
                except Exception:
                    reprocess_warnings.append("Full-Text Search (FTS) index update failed.")

                # 5. Refresh Vectors
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'GENERATING_VECTORS', 'status': 'IN_PROGRESS', 'progress': 75, 'message': 'Chunking document and re-generating vector embeddings', 'warnings': reprocess_warnings}))
                if vector_db:
                    try:
                        def do_vector_update():
                            CandidateService.update_vector_index(vector_db, candidate_id, raw_text, rv.id)
                        await asyncio.to_thread(do_vector_update)
                    except Exception:
                        reprocess_warnings.append("Vector re-indexing skipped (embedding model or vector store error).")
                else:
                    reprocess_warnings.append("Vector re-indexing skipped (LanceDB connection unavailable).")

                # 6. Timeline Audit Log
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'LOGGING_TIMELINE', 'status': 'IN_PROGRESS', 'progress': 90, 'message': 'Logging timeline audit event', 'warnings': reprocess_warnings}))
                try:
                    def log_timeline():
                        ledger = TimelineLedger()
                        ledger.log_event(
                            session=task_db,
                            candidate_id=candidate_id,
                            event_type="REPROCESS_TRIGGERED",
                            title="Reprocessing Triggered",
                            description="Recruiter triggered batch re-processing of candidate data",
                            metadata={},
                            created_by="Recruiter"
                        )
                        task_db.commit()
                    await asyncio.to_thread(log_timeline)
                except Exception:
                    pass

                # 7. Completed for candidate
                mode_str = "AI Model" if used_ai else "Rule-based"
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'message': f'Reprocessed successfully ({mode_str})', 'used_ai_fallback': used_ai, 'model_name': settings.llm_model if used_ai else None, 'warnings': reprocess_warnings}))

            except Exception as e:
                task_db.rollback()
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'ERROR', 'status': 'FAILED', 'progress': 100, 'message': str(e), 'warnings': reprocess_warnings}))
            finally:
                task_db.close()

    # Launch all tasks
    total_candidates = len(payload.candidate_ids)
    tasks = [asyncio.create_task(process_candidate(idx, cid, total_candidates)) for idx, cid in enumerate(payload.candidate_ids)]
    
    # Helper to close the queue when all tasks finish
    async def closer():
        await asyncio.gather(*tasks)
        await event_queue.put(None)
    
    asyncio.create_task(closer())

    async def batch_stream_generator():
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {event}\n\n"

    return StreamingResponse(batch_stream_generator(), media_type="text/event-stream")


