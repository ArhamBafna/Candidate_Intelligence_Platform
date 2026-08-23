from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SearchQueryRequest(BaseModel):
    query_text: str
    min_yoe: Optional[float] = None
    city: Optional[str] = None
    title: Optional[str] = None
    top_k: Optional[int] = None

class SearchResultItem(BaseModel):
    candidate_id: str
    rank: int
    rrf_score: float
    rerank_score: Optional[float] = None
    match_percentage: float = 0.0
    match_scorecard: Dict[str, Any] = Field(default_factory=dict)
    candidate_info: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
    warnings: List[str] = Field(default_factory=list)
    job_ad_recipe: Optional[Dict[str, Any]] = None

