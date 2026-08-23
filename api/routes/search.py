from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
from api.dependencies import get_db, get_vector_db, get_settings
from api.schemas.search import SearchQueryRequest, SearchResponse, SearchResultItem
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates
from candidate_intelligence_platform.intelligence.chat_model import resolve_chat_model
from config.settings import Settings
from storage.db_models import Candidate
import structlog
import time

logger = structlog.get_logger(__name__)

AI_EXPLANATION_UNAVAILABLE_WARNING = (
    "AI explanations are unavailable right now (chat model could not be reached); "
    "results are shown without AI-generated match notes."
)

def _build_search_query(request: SearchQueryRequest) -> str:
    query_parts = []
    if request.query_text and request.query_text.strip():
        query_parts.append(request.query_text.strip())
    if request.city:
        query_parts.append(f"location:'{request.city}'")
    if request.min_yoe:
        query_parts.append(f"yoe >= {request.min_yoe}")
    if request.title:
        query_parts.append(f"title:'{request.title}'")
    return " AND ".join(query_parts) if query_parts else ""

def _resolve_top_k(request: SearchQueryRequest, settings: Settings) -> int:
    return request.top_k if request.top_k is not None else settings.default_top_k

def _hydrate_candidates(db: Session, raw_results: list) -> dict:
    top_ids = [raw.get("candidate_id") for raw in raw_results if raw.get("candidate_id")]
    candidates = db.query(Candidate).filter(Candidate.id.in_(top_ids)).all()
    return {c.id: c for c in candidates}

def _format_search_results(raw_results: list, candidate_map: dict) -> list[SearchResultItem]:
    items = []
    for raw in raw_results:
        cid = raw.get("candidate_id", "")
        c_info = None
        if cid:
            candidate_obj = candidate_map.get(cid)
            if candidate_obj:
                c_info = {
                    "first_name": candidate_obj.first_name,
                    "last_name": candidate_obj.last_name,
                    "current_title": candidate_obj.current_title,
                    "current_company": candidate_obj.current_company,
                    "current_city": candidate_obj.current_city,
                    "availability_status": candidate_obj.availability_status,
                }
        
        item = SearchResultItem(
            candidate_id=cid,
            rank=raw.get("rank", 1),
            rrf_score=raw.get("rrf_score", 0.0),
            rerank_score=raw.get("rerank_score"),
            match_percentage=raw.get("match_percentage", 0.0),
            match_scorecard=raw.get("match_scorecard", {}),
            candidate_info=c_info
        )
        items.append(item)
    return items

def _ai_explanation_warning(warnings: list[str]) -> list[str]:
    """Append a visible AI-unavailable warning when no chat model is usable."""
    updated = list(warnings)
    try:
        if resolve_chat_model() is None:
            updated.append(AI_EXPLANATION_UNAVAILABLE_WARNING)
    except Exception as e:
        logger.warning("ai_chat_availability_check_failed", error=str(e))
        updated.append(AI_EXPLANATION_UNAVAILABLE_WARNING)
    return updated

router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=SearchResponse)
def perform_search(request: SearchQueryRequest, db: Session = Depends(get_db), vector_db = Depends(get_vector_db), settings: Settings = Depends(get_settings)):
    full_query = _build_search_query(request)

    t0 = time.perf_counter()
    if full_query:
        for stage, progress, msg, data in search_candidates(full_query, db, vector_db, return_warnings=True):
            if stage == "COMPLETE":
                raw_results, warnings = data
    else:
        raw_results, warnings = [], []
    
    top_k = _resolve_top_k(request, settings)
    warnings = _ai_explanation_warning(warnings)
    top_results = raw_results[:top_k]
    vector_search_duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    
    t1 = time.perf_counter()
    candidate_map = _hydrate_candidates(db, top_results)
    items = _format_search_results(top_results, candidate_map)
        
    response = SearchResponse(
        query=request.query_text,
        total_results=len(items),
        results=items,
        warnings=warnings
    )
    db_retrieval_duration_ms = round((time.perf_counter() - t1) * 1000, 2)
    total_duration_ms = vector_search_duration_ms + db_retrieval_duration_ms

    logger.info(
        "candidate_search_complete",
        query=request.query_text,
        filters={"city": request.city, "min_yoe": request.min_yoe, "title": request.title},
        candidates_returned=len(items),
        vector_search_duration_ms=vector_search_duration_ms,
        db_retrieval_duration_ms=db_retrieval_duration_ms,
        total_duration_ms=total_duration_ms
    )
    return response

@router.post("/stream")
def perform_search_stream(request: SearchQueryRequest, db: Session = Depends(get_db), vector_db = Depends(get_vector_db), settings: Settings = Depends(get_settings)):
    def event_generator():
        try:
            full_query = _build_search_query(request)
            
            t0 = time.perf_counter()
            if full_query:
                for stage, progress, message, data in search_candidates(full_query, db, vector_db, return_warnings=True):
                    if stage == "COMPLETE":
                        raw_results, warnings = data
                    else:
                        event = {
                            "stage": stage,
                            "progress": progress,
                            "message": message,
                            "status": "IN_PROGRESS"
                        }
                        yield f"data: {json.dumps(event)}\n\n"
            else:
                raw_results, warnings = [], []

            top_k = _resolve_top_k(request, settings)
            warnings = _ai_explanation_warning(warnings)
            top_results = raw_results[:top_k]
            
            # Hydrate candidate info
            candidate_map = _hydrate_candidates(db, top_results)
            items = _format_search_results(top_results, candidate_map)
                
            response_data = SearchResponse(
                query=request.query_text,
                total_results=len(items),
                results=items,
                warnings=warnings
            )
            
            yield f"data: {json.dumps({'stage': 'COMPLETE', 'progress': 100, 'message': 'Search complete', 'status': 'SUCCESS', 'data': response_data.model_dump()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'ERROR', 'progress': 100, 'message': str(e), 'status': 'FAILED'})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
