import pytest
from candidate_intelligence_platform.search.rank_fusion import reciprocal_rank_fusion

def test_reciprocal_rank_fusion():
    fts_ranks = {"cand_1": 1, "cand_2": 2, "cand_3": 3}
    vector_ranks = {"cand_3": 1, "cand_1": 4}
    
    results = reciprocal_rank_fusion(fts_ranks, vector_ranks)
    
    assert len(results) == 3
    assert results[0][0] == "cand_3"
    assert results[1][0] == "cand_1"
    assert results[2][0] == "cand_2"
