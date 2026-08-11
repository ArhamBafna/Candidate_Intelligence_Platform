import pytest
from candidate_intelligence_platform.search.reranker import rerank_candidates

def test_rerank_candidates():
    query = "Looking for a Python developer"
    candidates_texts = [
        "Experienced Java developer",
        "Senior Python engineer with 10 years of experience"
    ]
    
    results = rerank_candidates(query, candidates_texts)
    
    assert len(results) == 2
    assert results[1] > results[0]
