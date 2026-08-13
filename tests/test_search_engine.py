import pytest
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
from candidate_intelligence_platform.search.rank_fusion import reciprocal_rank_fusion
from candidate_intelligence_platform.search.reranker import rerank_candidates
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates

def test_parse_query_to_sql():
    query = "python AND location:'NYC' AND yoe >= 5"
    sql, params = parse_query_to_sql(query)

    assert "candidates.current_city = :location" in sql
    assert "candidates.total_yoe >= :yoe" in sql
    assert "candidate_fts MATCH :fts_query" in sql

    assert params["location"] == "NYC"
    assert params["yoe"] == 5
    assert "python" in params["fts_query"]

def test_reciprocal_rank_fusion():
    fts_ranks = {"cand_1": 1, "cand_2": 2, "cand_3": 3}
    vector_ranks = {"cand_3": 1, "cand_1": 4}

    results = reciprocal_rank_fusion(fts_ranks, vector_ranks)

    assert len(results) == 3
    assert results[0][0] == "cand_3"
    assert results[1][0] == "cand_1"
    assert results[2][0] == "cand_2"

def test_rerank_candidates():
    query = "Looking for a Python developer"
    candidates_texts = [
        "Experienced Java developer",
        "Senior Python engineer with 10 years of experience"
    ]

    results = rerank_candidates(query, candidates_texts)

    assert len(results) == 2
    assert results[1] > results[0]

def test_hybrid_search_candidates(monkeypatch):
    query = "python AND location:'NYC'"

    def mock_parse(q):
        return "SELECT candidates.id FROM candidates WHERE candidates.current_city = :location", {"location": "NYC", "fts_query": "python"}

    def mock_db_fts(sql, params, db):
        return {"cand_1": 1, "cand_2": 2}

    def mock_vector_search(query_text, candidate_ids, vector_db):
        return {"cand_2": 1, "cand_1": 2}

    def mock_fusion(fts, vec):
        return [("cand_2", 0.05), ("cand_1", 0.04)]

    def mock_rerank(q, docs):
        return [0.9, 0.8]

    def mock_explainer(cid, rank, score, **kwargs):
        return {"candidate_id": cid, "rank": rank, "rrf_score": score, "match_percentage": 85.0, "match_scorecard": {}}

    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "parse_query_to_sql", mock_parse)
    monkeypatch.setattr(hs, "execute_fts_query", mock_db_fts)
    monkeypatch.setattr(hs, "execute_vector_search", mock_vector_search)
    monkeypatch.setattr(hs, "reciprocal_rank_fusion", mock_fusion)
    monkeypatch.setattr(hs, "rerank_candidates", mock_rerank)
    monkeypatch.setattr(hs, "build_match_rationale", mock_explainer)
    monkeypatch.setattr(hs, "fetch_candidate_documents", lambda ids, db: ["doc2", "doc1"])

    results = search_candidates(query, None, None)

    assert len(results) == 2
    assert results[0]["candidate_id"] == "cand_2"
    assert results[0]["rank"] == 1
