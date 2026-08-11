def build_match_rationale(candidate_id: str, rank: int, rrf_score: float, 
                          strict_filters: list = None, 
                          keyword_matches: list = None,
                          semantic_matches: list = None,
                          ai_inferences: list = None) -> dict:
    """
    Builds the Match Rationale scorecard for a candidate search result.
    """
    return {
        "candidate_id": candidate_id,
        "rank": rank,
        "rrf_score": rrf_score,
        "match_scorecard": {
            "strict_filters": strict_filters or [],
            "keyword_matches": keyword_matches or [],
            "semantic_matches": semantic_matches or [],
            "ai_inferences": ai_inferences or []
        }
    }
