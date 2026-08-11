import pytest
from candidate_intelligence_platform.intelligence.explainer import build_match_rationale

def test_build_match_rationale():
    candidate_id = "test-123"
    rank = 1
    rrf_score = 0.5
    
    rationale = build_match_rationale(candidate_id, rank, rrf_score)
    
    assert rationale["candidate_id"] == "test-123"
    assert rationale["rank"] == 1
    assert rationale["rrf_score"] == 0.5
    assert "match_scorecard" in rationale
