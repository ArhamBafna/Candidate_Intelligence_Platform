import math
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class MatchParameters:
    candidate_id: str
    rank: int
    rrf_score: float
    strict_filters: list = field(default_factory=list)
    keyword_matches: list = field(default_factory=list)
    semantic_matches: list = field(default_factory=list)
    ai_inferences: list = field(default_factory=list)
    rerank_score: Optional[float] = None

def build_match_rationale(params: MatchParameters) -> dict:
    """
    Builds the Match Rationale scorecard for a candidate search result,
    including a 0.0 - 100.0 percentage match score.
    """
    pct_from_rerank: Optional[float] = None
    if params.rerank_score is not None:
        try:
            sigmoid = 1.0 / (1.0 + math.exp(-params.rerank_score))
            pct_from_rerank = round(sigmoid * 100.0, 1)
        except (OverflowError, ValueError):
            pct_from_rerank = None

    if pct_from_rerank is not None:
        match_percentage = pct_from_rerank
    elif params.rrf_score > 0.0:
        max_rrf = 2.0 / 61.0
        pct = (params.rrf_score / max_rrf) * 100.0
        match_percentage = min(100.0, max(0.0, round(pct, 1)))
    else:
        match_percentage = 0.0

    return {
        "candidate_id": params.candidate_id,
        "rank": params.rank,
        "rrf_score": params.rrf_score,
        "rerank_score": params.rerank_score,
        "match_percentage": match_percentage,
        "match_scorecard": {
            "strict_filters": params.strict_filters,
            "keyword_matches": params.keyword_matches,
            "semantic_matches": params.semantic_matches,
            "ai_inferences": params.ai_inferences
        }
    }

