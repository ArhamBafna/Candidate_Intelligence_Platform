from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
from api.dependencies import get_db, get_vector_db
from api.schemas.search import SearchQueryRequest, SearchResponse, SearchResultItem
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates
from storage.db_models import Candidate
import structlog
import time

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=SearchResponse)
def perform_search(request: SearchQueryRequest, db: Session = Depends(get_db)):
    query_parts = []
    if request.query_text and request.query_text.strip():
        query_parts.append(request.query_text.strip())
    if request.city:
        query_parts.append(f"location:'{request.city}'")
    if request.min_yoe:
        query_parts.append(f"yoe >= {request.min_yoe}")
    if request.title:
        query_parts.append(f"title:'{request.title}'")

    full_query = " AND ".join(query_parts) if query_parts else ""

    vector_db = get_vector_db()
    
    t0 = time.perf_counter()
    if full_query:
        raw_results, warnings = search_candidates(full_query, db, vector_db, return_warnings=True)
    else:
        raw_results, warnings = [], []
    
    top_results = raw_results[:request.top_k]
    vector_search_duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    
    t1 = time.perf_counter()
    items = []
    for raw in top_results:
        cid = raw.get("candidate_id", "")
        c_info = None
        if cid:
            candidate_obj = db.query(Candidate).filter(Candidate.id == cid).first()
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
def perform_search_stream(request: SearchQueryRequest, db: Session = Depends(get_db)):
    import queue
    import threading
    
    q = queue.Queue()
    
    def progress_callback(stage: str, progress: int, message: str):
        event = {
            "stage": stage,
            "progress": progress,
            "message": message,
            "status": "IN_PROGRESS"
        }
        q.put(event)
        
    def worker():
        try:
            query_parts = []
            if request.query_text and request.query_text.strip():
                query_parts.append(request.query_text.strip())
            if request.city:
                query_parts.append(f"location:'{request.city}'")
            if request.min_yoe:
                query_parts.append(f"yoe >= {request.min_yoe}")
            if request.title:
                query_parts.append(f"title:'{request.title}'")

            full_query = " AND ".join(query_parts) if query_parts else ""
            vector_db = get_vector_db()
            
            t0 = time.perf_counter()
            if full_query:
                raw_results, warnings = search_candidates(
                    full_query, db, vector_db, 
                    return_warnings=True, 
                    progress_callback=progress_callback
                )
            else:
                raw_results, warnings = [], []
                
            top_results = raw_results[:request.top_k]
            
            # Hydrate candidate info
            items = []
            for raw in top_results:
                cid = raw.get("candidate_id", "")
                c_info = None
                if cid:
                    candidate_obj = db.query(Candidate).filter(Candidate.id == cid).first()
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
                
            response_data = SearchResponse(
                query=request.query_text,
                total_results=len(items),
                results=items,
                warnings=warnings
            )
            
            q.put({
                "stage": "COMPLETE",
                "progress": 100,
                "message": "Search complete",
                "status": "SUCCESS",
                "data": response_data.model_dump()
            })
            q.put(None) # Sentinel to stop generator
        except Exception as e:
            q.put({
                "stage": "ERROR",
                "progress": 100,
                "message": str(e),
                "status": "FAILED"
            })
            q.put(None)
            
    threading.Thread(target=worker, daemon=True).start()
    
    def event_generator():
        while True:
            event = q.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
