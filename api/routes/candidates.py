from typing import AsyncGenerator, List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from api.dependencies import get_db, get_vector_db, get_settings, _get_sessionmaker
from config.settings import Settings
from storage.cas import CASManager
from api.schemas.candidates import (
    CandidateResponse, 
    CandidateStatusUpdate, 
    TimelineEventResponse,
    CandidateUpdate,
    BatchCandidateIds,
    BatchReprocessRequest
)
from storage.db_models import Candidate, ResumeVersion, CandidateTimelineEvent
from crm.state_machine import CandidateStateMachine, TransitionContext
from crm.timeline_ledger import TimelineLedger
from api.services.candidate_service import CandidateService
from sqlalchemy import text
from sqlalchemy.orm import Session
from candidate_intelligence_platform.ingestion.intake import (
    ingest_file,
    reprocess_text,
    classify_document,
    IntakeProgress,
    IntakeResult,
    IntakeSource,
    IntakeStatus,
    TimelineMode,
)
from candidate_intelligence_platform.extraction.hybrid_extractor import (
    normalize_name,
    normalize_title
)
from candidate_intelligence_platform.intelligence.chat_model import (
    chat_retry_candidates,
    resolve_chat_model,
    get_llm_provider,
    normalize_model_name,
)
from candidate_intelligence_platform.intelligence.ai_messages import (
    AI_EXPLANATION_UNAVAILABLE,
    CLOUD_FALLBACK_TO_DEVICE,
    DEVICE_FALLBACK_NOTICE,
    label_for_model,
)
from candidate_intelligence_platform.prompts import build_match_insight_prompt
import structlog
import json
import time
import asyncio
import hashlib
import uuid
from pathlib import Path
from fastapi.responses import StreamingResponse, FileResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/candidates", tags=["candidates"])

def translate_reprocess_progress(p: IntakeProgress, llm_model: str) -> Optional[Dict[str, Any]]:
    """Canonical pipeline stages -> reprocess contracted stage names/progress."""
    if p.stage == "ENTITY_RESOLUTION":
        return {
            "stage": "ENTITY_RESOLUTION",
            "stage_detail": "Rule-based NER Extraction",
            "status": "IN_PROGRESS",
            "progress": 30,
            "used_ai": False
        }
    if p.stage == "AI_EXTRACTION":
        model = str(p.detail.get("model_name") or llm_model)
        friendly = label_for_model(model)
        return {
            "stage": "AI_EXTRACTION",
            "stage_detail": f"AI reading ({friendly})",
            "status": "IN_PROGRESS",
            "progress": 30,
            "message": f"{friendly} is reading this document...",
            "used_ai": True,
            "model_name": model
        }
    if p.stage == "UPDATING_FTS":
        return {"stage": "UPDATING_FTS", "status": "IN_PROGRESS", "progress": 50, "message": "Refreshing FTS search index"}
    if p.stage == "GENERATING_VECTORS":
        return {"stage": "GENERATING_VECTORS", "status": "IN_PROGRESS", "progress": 75, "message": "Chunking document and re-generating LanceDB vector embeddings"}
    if p.stage == "LOGGING_TIMELINE":
        return {"stage": "LOGGING_TIMELINE", "status": "IN_PROGRESS", "progress": 90, "message": "Logging timeline audit event"}
    return None

@router.get("", response_model=List[CandidateResponse])
def list_candidates(db: Session = Depends(get_db)) -> List[Candidate]:
    candidates = db.query(Candidate).all()
    return candidates

@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: str, 
    db: Session = Depends(get_db),
    vector_db = Depends(get_vector_db)
) -> None:
    success = CandidateService.delete_candidate(db, candidate_id, vector_db)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")

    logger.info("candidate_deleted", candidate_id=candidate_id)
    return None

@router.patch("/{candidate_id}/status")
def update_candidate_status(
    candidate_id: str, 
    update: CandidateStatusUpdate, 
    db: Session = Depends(get_db)
) -> Dict[str, str]:
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
def get_candidate_timeline(candidate_id: str, db: Session = Depends(get_db)) -> List[CandidateTimelineEvent]:
    ledger = TimelineLedger()
    events = ledger.get_events(session=db, candidate_id=candidate_id)
    return events

@router.put("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(candidate_id: str, update_data: CandidateUpdate, db: Session = Depends(get_db)) -> Candidate:
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
def get_candidate_file(candidate_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> FileResponse:
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
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
) -> Dict[str, Any]:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    rv = db.query(ResumeVersion).filter(
        ResumeVersion.candidate_id == candidate_id,
        ResumeVersion.is_primary == True
    ).first()

    if rv and rv.raw_text:
        result = reprocess_text(
            raw_text=rv.raw_text,
            candidate_id=candidate_id,
            resume_version_id=rv.id,
            db=db,
            vector_db=vector_db,
            settings=settings,
        )
        if result.status == IntakeStatus.ERROR:
            db.rollback()
            raise HTTPException(status_code=500, detail=result.warnings[0] if result.warnings else "Reprocessing failed")
        db.commit()
        return {
            "status": "success",
            "message": "Reprocessing completed successfully",
            "warnings": result.warnings,
            "used_ai_fallback": result.used_ai_fallback,
            "model_name": result.model_name
        }

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
    return {"status": "success", "message": "Reprocessing completed successfully", "warnings": [], "used_ai_fallback": False, "model_name": None}

@router.post("/{candidate_id}/reprocess-stream")
async def reprocess_candidate_stream(
    candidate_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
) -> StreamingResponse:
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

            used_ai = False
            if raw_text:
                collected: List[str] = []

                def on_progress_bridge(p: IntakeProgress) -> None:
                    mapped = translate_reprocess_progress(p, settings.llm_model)
                    if mapped is not None:
                        payload = {"candidate_id": candidate_id, "candidate_name": candidate_name, **mapped}
                        payload.setdefault("warnings", reprocess_warnings)
                        collected.append(json.dumps(payload))

                result = await asyncio.to_thread(
                    lambda: reprocess_text(
                        raw_text=raw_text,
                        candidate_id=candidate_id,
                        resume_version_id=rv.id,
                        db=db,
                        vector_db=vector_db,
                        settings=settings,
                        on_progress=on_progress_bridge,
                    )
                )

                for payload_json in collected:
                    yield f"data: {payload_json}\n\n"
                reprocess_warnings.extend(result.warnings)

                if result.status == IntakeStatus.ERROR:
                    db.rollback()
                    yield f"data: {json.dumps({'candidate_id': candidate_id, 'stage': 'ERROR', 'status': 'FAILED', 'progress': 100, 'message': result.warnings[0] if result.warnings else 'Reprocessing failed', 'warnings': reprocess_warnings})}\n\n"
                    return

                db.commit()

                if result.used_ai_fallback:
                    model = result.model_name or settings.llm_model
                    yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'AI_EXTRACTION', 'stage_detail': f'AI Model Inference ({model})', 'status': 'COMPLETED', 'progress': 40, 'message': f'Local AI Model extraction finished ({model}).', 'used_ai': True, 'model_name': model, 'warnings': reprocess_warnings})}\n\n"
                    await asyncio.sleep(0.02)

                mode_str = "AI Model" if result.used_ai_fallback else "Rule-based NER"
                yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'message': f'Reprocessing completed successfully ({mode_str})', 'used_ai_fallback': result.used_ai_fallback, 'model_name': result.model_name, 'warnings': reprocess_warnings})}\n\n"
            else:
                # No raw text: preserve legacy stage sequence without extraction work.
                yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'UPDATING_FTS', 'status': 'IN_PROGRESS', 'progress': 50, 'message': 'Refreshing FTS search index', 'warnings': reprocess_warnings})}\n\n"
                await asyncio.sleep(0.05)
                yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'GENERATING_VECTORS', 'status': 'IN_PROGRESS', 'progress': 75, 'message': 'Chunking document and re-generating LanceDB vector embeddings', 'warnings': reprocess_warnings})}\n\n"
                await asyncio.sleep(0.05)
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
                yield f"data: {json.dumps({'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'message': 'Reprocessing completed successfully (Rule-based NER)', 'used_ai_fallback': False, 'model_name': None, 'warnings': reprocess_warnings})}\n\n"
        except Exception as e:
            db.rollback()
            yield f"data: {json.dumps({'candidate_id': candidate_id, 'stage': 'ERROR', 'status': 'FAILED', 'progress': 100, 'message': str(e), 'warnings': reprocess_warnings})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
) -> Dict[str, Any]:
    content = await file.read()
    cas_mgr = CASManager(settings.cas_root_dir)

    def run_pipeline() -> IntakeResult:
        return ingest_file(
            content=content,
            filename=file.filename or "resume",
            db=db,
            cas_mgr=cas_mgr,
            vector_db=vector_db,
            settings=settings,
            source=IntakeSource.UPLOAD,
            timeline_mode=TimelineMode.LEDGER,
        )

    upload_started = time.perf_counter()
    result = await asyncio.to_thread(run_pipeline)
    duration_s = round(time.perf_counter() - upload_started, 1)

    if result.status == IntakeStatus.SKIPPED_DUPLICATE:
        return {
            "status": "skipped",
            "message": "File already exists",
            "candidate_id": result.candidate_id,
            "classified_as": result.classified_as
        }

    if result.status == IntakeStatus.SKIPPED_NON_RESUME:
        reason = result.warnings[0] if result.warnings else ""
        return {
            "status": "rejected",
            "reason": f"This file doesn't look like a resume: {reason}. Nothing was saved.",
            "classified_as": result.classified_as,
            "warnings": result.warnings
        }

    if result.status == IntakeStatus.ERROR:
        db.rollback()
        raise HTTPException(status_code=500, detail=result.warnings[0] if result.warnings else "Intake failed")

    db.commit()

    cand = db.query(Candidate).filter(Candidate.id == result.candidate_id).first() if result.candidate_id else None
    candidate_name = f"{cand.first_name} {cand.last_name}".strip() if cand else ""
    logger.info(
        "resume_upload_complete",
        status="success",
        file_hash=hashlib.sha256(content).hexdigest(),
        candidate_id=result.candidate_id,
        candidate_name=candidate_name,
        file_name=file.filename or "",
        classified_as=result.classified_as,
        duration_s=duration_s
    )
    return {
        "status": "success",
        "candidate_id": result.candidate_id,
        "first_name": cand.first_name if cand else "",
        "last_name": cand.last_name if cand else "",
        "warnings": result.warnings,
        "resolution_action": result.resolution_action.value if result.resolution_action else None,
        "matched_candidate_id": result.matched_candidate_id,
        "classified_as": result.classified_as,
        "used_ai_fallback": result.used_ai_fallback,
        "model_name": result.model_name
    }

@router.post("/upload-stream")
async def upload_stream_resumes(
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db), 
    settings: Settings = Depends(get_settings),
    vector_db = Depends(get_vector_db)
) -> StreamingResponse:
    # Bounded semaphore to limit concurrent file processing
    upload_semaphore = asyncio.Semaphore(4)
    event_queue = asyncio.Queue()
    
    # Get sessionmaker for creating new sessions per task
    SessionLocal = _get_sessionmaker(settings.db_path)

    async def process_file(file: UploadFile):
        async with upload_semaphore:
            # Create a dedicated session for this file to ensure thread safety
            # when using asyncio.to_thread with DB operations
            task_db = SessionLocal()
            loop = asyncio.get_running_loop()

            def translate_progress(p: IntakeProgress) -> Optional[Dict[str, Any]]:
                """Canonical pipeline stages -> upload-stream contracted stage names/progress."""
                if p.stage == "HASHING":
                    return {"stage": "HASHING", "status": "IN_PROGRESS", "progress": 10}
                if p.stage == "PARSING":
                    return {"stage": "PARSING", "status": "IN_PROGRESS", "progress": 30}
                if p.stage == "CLASSIFYING":
                    return {"stage": "CLASSIFYING", "status": "IN_PROGRESS", "progress": 40, "message": p.message}
                if p.stage == "EXTRACTING":
                    return {
                        "stage": "ENTITY_RESOLUTION",
                        "stage_detail": "Rule-based NER Extraction",
                        "status": "IN_PROGRESS",
                        "progress": 70,
                        "message": "Extracting profile entities (Rule-based NER)...",
                        "used_ai": False
                    }
                if p.stage == "AI_EXTRACTION":
                    model = str(p.detail.get("model_name") or settings.llm_model)
                    return {
                        "stage": "AI_EXTRACTION",
                        "stage_detail": f"AI Model Inference ({model})",
                        "status": "IN_PROGRESS",
                        "progress": 70,
                        "message": f"Running local AI Model extraction ({model})...",
                        "used_ai": True,
                        "model_name": model
                    }
                if p.stage == "SAVING":
                    return {"stage": "SAVING", "status": "IN_PROGRESS", "progress": 90}
                if p.stage == "GENERATING_VECTORS":
                    return {"stage": "CHUNKING", "status": "IN_PROGRESS", "progress": 80}
                return None

            def on_progress(p: IntakeProgress) -> None:
                mapped = translate_progress(p)
                if mapped is not None:
                    loop.call_soon_threadsafe(
                        event_queue.put_nowait,
                        json.dumps({"file_name": file.filename, **mapped})
                    )

            try:
                content = await file.read()
                cas_mgr = CASManager(settings.cas_root_dir)

                def run_pipeline() -> IntakeResult:
                    return ingest_file(
                        content=content,
                        filename=file.filename or "resume",
                        db=task_db,
                        cas_mgr=cas_mgr,
                        vector_db=vector_db,
                        settings=settings,
                        source=IntakeSource.UPLOAD_STREAM,
                        timeline_mode=TimelineMode.LEDGER,
                        on_progress=on_progress
                    )

                upload_started = time.perf_counter()
                result = await asyncio.to_thread(run_pipeline)
                duration_s = round(time.perf_counter() - upload_started, 1)

                if result.status == IntakeStatus.SKIPPED_DUPLICATE:
                    await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'HASHING', 'status': 'SKIPPED_DUPLICATE', 'message': 'File already exists', 'progress': 100, 'warnings': []}))
                    return

                if result.status == IntakeStatus.SKIPPED_NON_RESUME:
                    reason = result.warnings[0] if result.warnings else ""
                    await event_queue.put(json.dumps({
                        'file_name': file.filename, 'stage': 'COMPLETED', 'status': 'SKIPPED_NON_RESUME',
                        'message': reason, 'progress': 100, 'warnings': [reason], 'classified_as': result.classified_as
                    }))
                    return

                if result.status == IntakeStatus.ERROR:
                    task_db.rollback()
                    await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'ERROR', 'status': 'FAILED', 'message': result.warnings[0] if result.warnings else 'Intake failed', 'progress': 100, 'warnings': []}))
                    return

                task_db.commit()

                cand = task_db.query(Candidate).filter(Candidate.id == result.candidate_id).first() if result.candidate_id else None
                candidate_name = f"{cand.first_name} {cand.last_name}".strip() if cand else ""

                logger.info(
                    "resume_upload_complete",
                    status="success",
                    candidate_id=result.candidate_id,
                    candidate_name=candidate_name,
                    file_name=file.filename or "",
                    classified_as=result.classified_as,
                    duration_s=duration_s
                )
                await event_queue.put(json.dumps({
                    'file_name': file.filename,
                    'stage': 'COMPLETED',
                    'status': 'SUCCESS',
                    'progress': 100,
                    'candidate_id': result.candidate_id,
                    'candidate_name': candidate_name,
                    'used_ai_fallback': result.used_ai_fallback,
                    'model_name': result.model_name,
                    'warnings': result.warnings,
                    'resolution_action': result.resolution_action.value if result.resolution_action else None,
                    'matched_candidate_id': result.matched_candidate_id,
                    'classified_as': result.classified_as
                }))

            except Exception as e:
                task_db.rollback()
                logger.error(
                    "resume_upload_complete",
                    status="failed",
                    file_name=file.filename or "",
                    error=str(e)
                )
                await event_queue.put(json.dumps({'file_name': file.filename, 'stage': 'ERROR', 'status': 'FAILED', 'message': str(e), 'progress': 100, 'warnings': []}))
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
) -> Dict[str, Any]:
    deleted_ids = []
    try:
        for candidate_id in payload.candidate_ids:
            if CandidateService.delete_candidate(db, candidate_id, vector_db, commit=False):
                deleted_ids.append(candidate_id)
        db.commit()  # Single commit for all deletes
    except Exception:
        db.rollback()
        raise

    logger.info(
        "candidates_deleted",
        requested_count=len(payload.candidate_ids),
        deleted_count=len(deleted_ids)
    )

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
) -> StreamingResponse:
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

                collected: List[str] = []

                def on_progress_bridge(p: IntakeProgress) -> None:
                    mapped = translate_reprocess_progress(p, settings.llm_model)
                    if mapped is not None:
                        payload = {
                            'batch_index': idx + 1,
                            'batch_total': total_candidates,
                            'candidate_id': candidate_id,
                            'candidate_name': candidate_name,
                            **mapped
                        }
                        payload.setdefault('warnings', reprocess_warnings)
                        collected.append(json.dumps(payload))

                result = await asyncio.to_thread(
                    lambda: reprocess_text(
                        raw_text=raw_text,
                        candidate_id=candidate_id,
                        resume_version_id=rv.id,
                        db=task_db,
                        vector_db=vector_db,
                        settings=settings,
                        on_progress=on_progress_bridge,
                    )
                )

                for payload_json in collected:
                    await event_queue.put(payload_json)

                reprocess_warnings.extend(result.warnings)

                if result.status == IntakeStatus.ERROR:
                    task_db.rollback()
                    await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'ERROR', 'status': 'FAILED', 'progress': 100, 'message': result.warnings[0] if result.warnings else 'Reprocessing failed', 'warnings': reprocess_warnings}))
                    return

                task_db.commit()
                refreshed = task_db.query(Candidate).filter(Candidate.id == candidate_id).first()
                if refreshed:
                    candidate_name = f"{refreshed.first_name} {refreshed.last_name}"

                if result.used_ai_fallback:
                    model = result.model_name or settings.llm_model
                    await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'AI_EXTRACTION', 'stage_detail': f'AI Model Inference ({model})', 'status': 'COMPLETED', 'progress': 40, 'message': f'Local AI Model extraction finished ({model}).', 'used_ai': True, 'model_name': model, 'warnings': reprocess_warnings}))

                mode_str = "AI Model" if result.used_ai_fallback else "Rule-based"
                await event_queue.put(json.dumps({'batch_index': idx + 1, 'batch_total': total_candidates, 'candidate_id': candidate_id, 'candidate_name': candidate_name, 'stage': 'COMPLETED', 'status': 'SUCCESS', 'progress': 100, 'message': f'Reprocessed successfully ({mode_str})', 'used_ai_fallback': result.used_ai_fallback, 'model_name': result.model_name, 'warnings': reprocess_warnings}))

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


async def stream_openrouter_generate(prompt: str, model_name: str, settings: Settings, **kwargs):
    import httpx

    from candidate_intelligence_platform.intelligence.chat_model import (
        OpenRouterModelPaidError,
        is_openrouter_model_free,
        mark_openrouter_model_paid,
    )

    if not settings.openrouter_api_key:
        return
    if not is_openrouter_model_free(model_name):
        raise OpenRouterModelPaidError(model_name)

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
        ) as response:
            if response.status_code == 402:
                await response.aread()
                mark_openrouter_model_paid(model_name)
                raise OpenRouterModelPaidError(model_name)
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


async def stream_ollama_generate(prompt: str, model_name: str, **kwargs):
    import ollama
    client = ollama.AsyncClient()
    try:
        async for chunk in await client.generate(model=model_name, prompt=prompt, stream=True, **kwargs):
            yield chunk['response']
    except asyncio.CancelledError:
        logger.info("Ollama streaming cancelled by client disconnect")
        raise

AI_INSIGHT_UNAVAILABLE_MESSAGE = AI_EXPLANATION_UNAVAILABLE

@router.get("/{candidate_id}/insight")
async def get_candidate_insight(
    candidate_id: str,
    query: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> StreamingResponse:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    rv = db.query(ResumeVersion).filter(
        ResumeVersion.candidate_id == candidate_id,
        ResumeVersion.is_primary == True
    ).first()
    
    raw_text = rv.raw_text if rv and rv.raw_text else ""
    
    prompt = build_match_insight_prompt(raw_text, query)

    async def stream_tokens(model_name: str, provider: str) -> AsyncGenerator[str, None]:
        if provider == "openrouter":
            async for token in stream_openrouter_generate(prompt=prompt, model_name=model_name, settings=settings):
                yield token
        else:
            async for token in stream_ollama_generate(prompt=prompt, model_name=model_name):
                yield token

    def _unavailable_event() -> str:
        return f"data: {json.dumps({'error': 'AI_EXPLANATION_UNAVAILABLE', 'message': AI_INSIGHT_UNAVAILABLE_MESSAGE})}\n\n"

    async def event_generator():
        try:
            provider = get_llm_provider()
            resolved = await asyncio.to_thread(resolve_chat_model)
            
            if resolved is None:
                logger.warning(
                    "ai_chat_insight_failed",
                    configured_model=settings.llm_model,
                    fallback_model=settings.fallback_llm_model,
                    reason="no_usable_chat_model",
                    action="serving_visible_unavailable_message"
                )
                yield _unavailable_event()
                return
            
            model_used = resolved
            tokens_sent = 0
            try:
                async for token in stream_tokens(model_used, provider):
                    tokens_sent += 1
                    yield f"data: {json.dumps({'token': token})}\n\n"
            except asyncio.CancelledError:
                raise
            except Exception as first_error:
                if tokens_sent > 0:
                    raise
                recovered = False
                last_error: Exception = first_error
                
                # Build fallback chain based on provider
                if provider == "openrouter":
                    # OpenRouter ox-alpha first; on failure go straight to local Ollama
                    fallback_models = chat_retry_candidates(settings.llm_model, settings.fallback_llm_model)
                    fallback_models = [m for m in fallback_models if normalize_model_name(m) != normalize_model_name(model_used)]
                else:
                    fallback_models = chat_retry_candidates(settings.llm_model, settings.fallback_llm_model, failed_model=model_used)

                for candidate_model in fallback_models:
                    # OpenRouter failures always fall back to local Ollama
                    fallback_provider = "ollama"

                    logger.warning(
                        "ai_chat_model_fallback",
                        configured_model=model_used,
                        fallback_model=candidate_model,
                        fallback_provider=fallback_provider,
                        error=str(last_error),
                        action="retrying_with_fallback_model"
                    )
                    try:
                        notice = (
                            CLOUD_FALLBACK_TO_DEVICE
                            if provider == "openrouter"
                            else DEVICE_FALLBACK_NOTICE
                        )
                        yield f"data: {json.dumps({'notice': notice})}\n\n"
                        async for token in stream_tokens(candidate_model, fallback_provider):
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        recovered = True
                        break
                    except asyncio.CancelledError:
                        raise
                    except Exception as retry_error:
                        last_error = retry_error
                if not recovered:
                    raise last_error
        except asyncio.CancelledError:
            logger.info("SSE connection closed by client")
            raise
        except Exception as e:
            logger.warning(
                "ai_chat_insight_failed",
                configured_model=settings.llm_model,
                fallback_model=settings.fallback_llm_model,
                error=str(e),
                action="serving_visible_unavailable_message"
            )
            yield _unavailable_event()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

