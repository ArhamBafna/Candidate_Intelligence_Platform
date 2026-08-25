import math
from collections import defaultdict

def reciprocal_rank_fusion(
    fts_ranks: dict[str, int],
    vector_ranks: dict[str, int],
    candidate_metadata: dict[str, dict] = None,
    params: dict = None,
    k: int = 60,
    keyword_weight: float = 1.0,
    vector_weight: float = 1.0
) -> tuple[list[tuple[str, float]], dict[str, list[dict]], dict[str, list[dict]]]:
    """
    Computes weighted Reciprocal Rank Fusion (RRF) for two sets of candidate ranks.
    RRF score = weight / (k + rank)
    Applies soft score adjustments for YoE penalties and Title/City exact match bonuses.
    """
    if candidate_metadata is None:
        candidate_metadata = {}
    if params is None:
        params = {}

    scores = defaultdict(float)
    soft_penalties = defaultdict(list)
    soft_bonuses = defaultdict(list)
    
    for cand_id, rank in fts_ranks.items():
        scores[cand_id] += keyword_weight * (1.0 / (k + rank))
        
    for cand_id, rank in vector_ranks.items():
        scores[cand_id] += vector_weight * (1.0 / (k + rank))
        
    target_yoe = params.get("yoe")
    target_title = (params.get("title") or "").lower()
    target_city = (params.get("location") or "").lower()

    for cand_id in list(scores.keys()):
        meta = candidate_metadata.get(cand_id, {})
        
        # Exact match bonus
        bonus_multiplier = 1.0
        if target_title and meta.get("current_title") == target_title:
            bonus_multiplier += 0.20
            soft_bonuses[cand_id].append({"field": "current_title", "bonus": "+20%"})
            
        if target_city and meta.get("current_city") == target_city:
            bonus_multiplier += 0.20
            soft_bonuses[cand_id].append({"field": "current_city", "bonus": "+20%"})
            
        scores[cand_id] *= bonus_multiplier

        # S-curve YoE Penalty
        if target_yoe is not None:
            cand_yoe = meta.get("total_yoe")
            if cand_yoe is None or cand_yoe == 0:
                # Unparsed / missing YoE gets neutral default penalty (1.0)
                pass
            else:
                delta = max(0.0, target_yoe - cand_yoe)
                if delta > 0:
                    penalty = 1.0 - (1.0 / (1.0 + math.exp(-(delta - 2.0))))
                    scores[cand_id] *= penalty
                    pct_penalty = round((1.0 - penalty) * 100)
                    soft_penalties[cand_id].append({"field": "total_yoe", "penalty": f"-{pct_penalty}%"})

    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results, dict(soft_penalties), dict(soft_bonuses)
