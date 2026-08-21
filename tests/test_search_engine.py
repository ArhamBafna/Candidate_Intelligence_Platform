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

def test_parse_query_to_sql_special_chars():
    query = "Java/J2EE hands-on C++"
    sql, params = parse_query_to_sql(query)
    
    assert "candidate_fts MATCH :fts_query" in sql
    # The special characters should be stripped or replaced by spaces
    assert params["fts_query"] == "Java J2EE hands on C"

def test_reciprocal_rank_fusion():
    fts_ranks = {"cand_1": 1, "cand_2": 2, "cand_3": 3}
    vector_ranks = {"cand_3": 1, "cand_1": 4}

    results = reciprocal_rank_fusion(fts_ranks, vector_ranks)

    assert len(results) == 3
    assert results[0][0] == "cand_3"
    assert results[1][0] == "cand_1"
    assert results[2][0] == "cand_2"

def test_rerank_candidates(monkeypatch):
    class MockReranker:
        def rerank(self, query, documents):
            return [0.2, 0.9]

    monkeypatch.setattr("candidate_intelligence_platform.search.reranker._get_reranker", lambda: MockReranker())

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

    def mock_vector_search(query_text, candidate_ids, vector_db, warnings=None):
        return {"cand_2": 1, "cand_1": 2}

    def mock_fusion(fts, vec):
        return [("cand_2", 0.05), ("cand_1", 0.04)]

    def mock_rerank(q, docs):
        return [0.9, 0.8]

    def mock_explainer(params):
        return {"candidate_id": params.candidate_id, "rank": params.rank, "rrf_score": params.rrf_score, "match_percentage": 85.0, "match_scorecard": {}}

    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "parse_query_to_sql", mock_parse)
    monkeypatch.setattr(hs, "execute_fts_query", mock_db_fts)
    monkeypatch.setattr(hs, "execute_vector_search", mock_vector_search)
    monkeypatch.setattr(hs, "reciprocal_rank_fusion", mock_fusion)
    monkeypatch.setattr(hs, "rerank_candidates", mock_rerank)
    monkeypatch.setattr(hs, "build_match_rationale", mock_explainer)
    monkeypatch.setattr(hs, "fetch_candidate_documents", lambda ids, db: ["doc2", "doc1"])

    gen = search_candidates(query, None, None)
    results = None
    for stage, progress, message, data in gen:
        if stage == "COMPLETE":
            results = data
            
    assert len(results) == 2
    assert results[0]["candidate_id"] == "cand_2"
    assert results[0]["rank"] == 1

def test_fetch_candidate_documents_empty():
    from candidate_intelligence_platform.search.hybrid_searcher import fetch_candidate_documents
    docs = fetch_candidate_documents([], None)
    assert docs == []

def test_execute_vector_search_missing_table(monkeypatch):
    from candidate_intelligence_platform.search.hybrid_searcher import execute_vector_search
    
    class MockVectorDB:
        def search(self, table_name):
            raise Exception("Table candidate_vectors does not exist.")
            
    # Should handle gracefully and return empty dict
    results = execute_vector_search("test query", {"cand_1"}, MockVectorDB())
    assert results == {}

def test_execute_vector_search_end_to_end(tmp_path):
    import lancedb
    from storage.vector_store import CandidateSectionVector
    from candidate_intelligence_platform.search.hybrid_searcher import execute_vector_search
    from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings

    db_path = str(tmp_path / "lancedb_search")
    db = lancedb.connect(db_path)
    tbl = db.create_table("candidate_vectors", schema=CandidateSectionVector)

    emb = generate_embeddings(["Senior Python Engineer in New York"])[0]
    tbl.add([{
        "chunk_id": "c1",
        "candidate_id": "cand_1",
        "resume_version_id": "rv1",
        "section_type": "SUMMARY",
        "chunk_text": "Senior Python Engineer in New York",
        "vector": emb,
        "start_offset": 0,
        "end_offset": 35
    }])

    warnings = []
    ranks = execute_vector_search("new york", ["cand_1"], db, warnings=warnings)
    assert warnings == []
    assert ranks == {"cand_1": 1}

