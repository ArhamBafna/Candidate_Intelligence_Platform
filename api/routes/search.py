from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.dependencies import get_db, get_vector_db
from api.schemas.search import SearchQueryRequest, SearchResponse, SearchResultItem
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates
from storage.db_models import Candidate

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
    raw_results = search_candidates(full_query, db, vector_db) if full_query else []
    
    top_results = raw_results[:request.top_k]
    
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
            match_scorecard=raw.get("match_scorecard", {}),
            candidate_info=c_info
        )
        items.append(item)
        
    return SearchResponse(
        query=request.query_text,
        total_results=len(items),
        results=items
    )
