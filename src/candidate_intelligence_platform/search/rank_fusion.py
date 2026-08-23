from collections import defaultdict

def reciprocal_rank_fusion(
    fts_ranks: dict[str, int],
    vector_ranks: dict[str, int],
    k: int = 60,
    keyword_weight: float = 1.0,
    vector_weight: float = 1.0
) -> list[tuple[str, float]]:
    """
    Computes weighted Reciprocal Rank Fusion (RRF) for two sets of candidate ranks.
    RRF score = weight / (k + rank)
    """
    scores = defaultdict(float)
    
    for cand_id, rank in fts_ranks.items():
        scores[cand_id] += keyword_weight * (1.0 / (k + rank))
        
    for cand_id, rank in vector_ranks.items():
        scores[cand_id] += vector_weight * (1.0 / (k + rank))
        
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results
