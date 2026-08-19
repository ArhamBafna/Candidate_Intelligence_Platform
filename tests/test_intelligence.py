import pytest
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings
from candidate_intelligence_platform.intelligence.explainer import build_match_rationale, MatchParameters

def test_generate_embeddings():
    texts = ["Hello world", "Machine learning engineer with 5 years experience"]
    embeddings = generate_embeddings(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384
    assert isinstance(embeddings[0][0], float)

def test_build_match_rationale():
    candidate_id = "test-123"
    rank = 1
    rrf_score = 0.032786
    
    # Case 1: RRF score fallback
    rationale = build_match_rationale(MatchParameters(candidate_id=candidate_id, rank=rank, rrf_score=rrf_score))
    
    assert rationale["candidate_id"] == "test-123"
    assert rationale["rank"] == 1
    assert rationale["rrf_score"] == rrf_score
    assert rationale["match_percentage"] == 100.0
    assert "match_scorecard" in rationale

    # Case 2: Cross-encoder rerank score (high match, score = 3.0 -> >95%)
    rationale_rerank = build_match_rationale(MatchParameters(candidate_id=candidate_id, rank=rank, rrf_score=rrf_score, rerank_score=3.0))
    assert rationale_rerank["rerank_score"] == 3.0
    assert 90.0 < rationale_rerank["match_percentage"] <= 100.0

    # Case 3: Cross-encoder rerank score (low match, score = -3.0 -> <10%)
    rationale_low = build_match_rationale(MatchParameters(candidate_id=candidate_id, rank=rank, rrf_score=rrf_score, rerank_score=-3.0))
    assert 0.0 <= rationale_low["match_percentage"] < 10.0


def test_embedding_semantic_similarity():
    import numpy as np
    
    texts = [
        "Senior Python Backend Developer with FastAPI experience",
        "Python software engineer specializing in backend REST APIs",
        "Executive Pastry Chef specializing in French baking"
    ]
    embeddings = generate_embeddings(texts)
    
    vec1 = np.array(embeddings[0])
    vec2 = np.array(embeddings[1])
    vec3 = np.array(embeddings[2])
    
    # Cosine similarity helper
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    sim_tech = cosine_sim(vec1, vec2)
    sim_unrelated = cosine_sim(vec1, vec3)
    
    # Similar python profiles should have significantly higher cosine similarity than baking chef
    assert sim_tech > sim_unrelated
    assert sim_tech > 0.6

