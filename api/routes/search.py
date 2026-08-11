from fastapi import APIRouter
from api.schemas.search import SearchQueryRequest, SearchResponse, SearchResultItem
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates

router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=SearchResponse)
def perform_search(request: SearchQueryRequest):
    # Construct the full query string from filters and query text
    # In a real implementation, we'd pass filters securely to the AST parser,
    # but for now we follow the simple search_candidates interface.
    
    query = request.query_text
    if request.city:
        query += f" AND location:'{request.city}'"
    if request.min_yoe:
        query += f" AND yoe >= {request.min_yoe}"
    if request.title:
        query += f" AND title:'{request.title}'"

    raw_results = search_candidates(query)
    
    # We slice to top_k
    top_results = raw_results[:request.top_k]
    
    items = []
    for raw in top_results:
        # Assuming the match rationale dict matches the SearchResultItem roughly
        item = SearchResultItem(
            candidate_id=raw.get("candidate_id", ""),
            rank=raw.get("rank", 1),
            rrf_score=raw.get("rrf_score", 0.0),
            match_scorecard=raw.get("match_scorecard", {})
        )
        items.append(item)
        
    return SearchResponse(
        query=request.query_text,
        total_results=len(items),
        results=items
    )
