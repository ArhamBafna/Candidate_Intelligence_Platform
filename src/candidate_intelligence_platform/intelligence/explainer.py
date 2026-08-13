import math

def build_match_rationale(candidate_id: str, rank: int, rrf_score: float, 
                          strict_filters: list = None, 
                          keyword_matches: list = None,
                          semantic_matches: list = None,
                          ai_inferences: list = None,
                          rerank_score: float = None) -> dict:
    """
    Builds the Match Rationale scorecard for a candidate search result,
    including a 0.0 - 100.0 percentage match score.
    """
    if rerank_score is not None:
        try:
            sigmoid = 1.0 / (1.0 + math.exp(-rerank_score))
            match_percentage = round(sigmoid * 100.0, 1)
        except Exception:
            match_percentage = 50.0
    elif rrf_score > 0.0:
        max_rrf = 2.0 / 61.0
        pct = (rrf_score / max_rrf) * 100.0
        match_percentage = min(100.0, max(0.0, round(pct, 1)))
    else:
        match_percentage = 0.0

    return {
        "candidate_id": candidate_id,
        "rank": rank,
        "rrf_score": rrf_score,
        "rerank_score": rerank_score,
        "match_percentage": match_percentage,
        "match_scorecard": {
            "strict_filters": strict_filters or [],
            "keyword_matches": keyword_matches or [],
            "semantic_matches": semantic_matches or [],
            "ai_inferences": ai_inferences or []
        }
    }

