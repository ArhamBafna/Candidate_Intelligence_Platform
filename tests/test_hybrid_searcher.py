import pytest
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates

def test_search_candidates(monkeypatch):
    query = "python AND location:'NYC'"
    
    def mock_parse(q):
        return "SELECT candidates.id FROM candidates WHERE candidates.current_city = :location", {"location": "NYC", "fts_query": "python"}
        
    def mock_db_fts(sql, params):
        return {"cand_1": 1, "cand_2": 2}
        
    def mock_vector_search(query_text, candidate_ids):
        return {"cand_2": 1, "cand_1": 2}
        
    def mock_fusion(fts, vec):
        return [("cand_2", 0.05), ("cand_1", 0.04)]
        
    def mock_rerank(q, docs):
        return [0.9, 0.8]
        
    def mock_explainer(cid, rank, score):
        return {"candidate_id": cid, "rank": rank, "rrf_score": score, "match_scorecard": {}}
        
    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "parse_query_to_sql", mock_parse)
    monkeypatch.setattr(hs, "execute_fts_query", mock_db_fts)
    monkeypatch.setattr(hs, "execute_vector_search", mock_vector_search)
    monkeypatch.setattr(hs, "reciprocal_rank_fusion", mock_fusion)
    monkeypatch.setattr(hs, "rerank_candidates", mock_rerank)
    monkeypatch.setattr(hs, "build_match_rationale", mock_explainer)
    monkeypatch.setattr(hs, "fetch_candidate_documents", lambda ids: ["doc2", "doc1"])
    
    results = search_candidates(query)
    
    assert len(results) == 2
    assert results[0]["candidate_id"] == "cand_2"
    assert results[0]["rank"] == 1
