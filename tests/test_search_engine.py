import pytest
from config.settings import Settings
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
from candidate_intelligence_platform.search.rank_fusion import reciprocal_rank_fusion
from candidate_intelligence_platform.search.reranker import rerank_candidates
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates, execute_vector_search

def test_parse_query_to_sql():
    query = "python AND location:'NYC' AND yoe >= 5"
    sql, params = parse_query_to_sql(query)

    assert "candidates.current_city LIKE '%' || :location || '%' COLLATE NOCASE" in sql
    assert "candidates.total_yoe >= :yoe" not in sql
    assert "candidate_fts MATCH :fts_query" in sql

    assert params["location"] == "NYC"
    assert params["yoe"] == 5
    assert "python" in params["fts_query"]
    assert "nyc" in params["fts_query"].lower()

def test_parse_query_to_sql_special_chars():
    query = "Java/J2EE hands-on C++"
    sql, params = parse_query_to_sql(query)
    
    assert "candidate_fts MATCH :fts_query" in sql
    # The special characters should be stripped or replaced by spaces
    assert params["fts_query"] == "Java J2EE hands on C"

def test_parse_title_filter_is_sql_like():
    query = "python AND title:'senior engineer'"
    sql, params = parse_query_to_sql(query)

    assert "candidates.current_title LIKE '%' || :title || '%' COLLATE NOCASE" in sql
    assert params["title"] == "senior engineer"
    assert "python" in params["fts_query"]
    assert "senior engineer" in params["fts_query"].lower()

def test_parse_title_filter_not_confused_by_substring_field_names():
    query = "subtitle:'junk' python"
    sql, params = parse_query_to_sql(query)

    assert ":title" not in sql
    assert "title" not in params
    assert params["fts_query"] == "subtitle 'junk' python"

def test_parse_and_substring_words_preserved():
    sql, params = parse_query_to_sql("SANDPAPER AND python")

    assert "SANDPAPER" in params["fts_query"]
    assert "SPAPER" not in params["fts_query"]
    assert "python" in params["fts_query"]

def test_parse_yoe_accepts_float():
    sql, params = parse_query_to_sql("python AND yoe >= 2.5")

    assert "candidates.total_yoe >= :yoe" not in sql
    assert params["yoe"] == 2.5
    assert params["fts_query"] == "python"

def test_keyword_only_query_orders_by_bm25(db_session):
    from storage.db_models import Candidate
    from sqlalchemy import text as sql_text
    from candidate_intelligence_platform.search.hybrid_searcher import execute_fts_query

    db_session.add_all([
        Candidate(id="cand_weak", first_name="Weak", last_name="Match"),
        Candidate(id="cand_strong", first_name="Strong", last_name="Match"),
        Candidate(id="cand_mid", first_name="Mid", last_name="Match"),
    ])
    db_session.commit()

    fts_rows = [
        {"candidate_id": "cand_weak", "full_name": "Weak Match", "current_title": "",
         "current_company": "", "resume_content": "salesperson who once heard about python"},
        {"candidate_id": "cand_strong", "full_name": "Strong Match", "current_title": "Python Engineer",
         "current_company": "PyTools",
         "resume_content": "python python python python python python python python python python"},
        {"candidate_id": "cand_mid", "full_name": "Mid Match", "current_title": "Python Developer",
         "current_company": "", "resume_content": "developer with python and go experience"},
    ]
    for row in fts_rows:
        db_session.execute(
            sql_text(
                "INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) "
                "VALUES (:candidate_id, :full_name, :current_title, :current_company, :resume_content)"
            ),
            row,
        )
    db_session.commit()

    sql, params = parse_query_to_sql("python")
    assert "ORDER BY bm25(candidate_fts)" in sql

    ranks = execute_fts_query(sql, params, db_session)

    assert set(ranks) == {"cand_weak", "cand_strong", "cand_mid"}
    assert ranks["cand_strong"] < ranks["cand_mid"] < ranks["cand_weak"]

def test_reciprocal_rank_fusion():
    fts_ranks = {"cand_1": 1, "cand_2": 2, "cand_3": 3}
    vector_ranks = {"cand_3": 1, "cand_1": 4}

    results, _, _ = reciprocal_rank_fusion(fts_ranks, vector_ranks)

    assert len(results) == 3
    assert results[0][0] == "cand_3"
    assert results[1][0] == "cand_1"
    assert results[2][0] == "cand_2"

def test_reciprocal_rank_fusion_weights():
    fts_ranks = {"kw_only": 1}
    vector_ranks = {"vec_only": 1}

    equal_res, _, _ = reciprocal_rank_fusion(fts_ranks, vector_ranks)
    equal = dict(equal_res)
    assert equal["kw_only"] == pytest.approx(equal["vec_only"])

    kw_res, _, _ = reciprocal_rank_fusion(fts_ranks, vector_ranks, k=60, keyword_weight=2.0, vector_weight=1.0)
    keyword_heavy = dict(kw_res)
    assert keyword_heavy["kw_only"] > keyword_heavy["vec_only"]

    vec_res, _, _ = reciprocal_rank_fusion(fts_ranks, vector_ranks, k=60, keyword_weight=1.0, vector_weight=3.0)
    vector_heavy = dict(vec_res)
    assert vector_heavy["vec_only"] > vector_heavy["kw_only"]

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

    fusion_calls = {}

    def mock_fusion(fts, vec, **kwargs):
        fusion_calls.update(kwargs)
        return [("cand_2", 0.05), ("cand_1", 0.04)], {}, {}

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
    assert fusion_calls["k"] == Settings().rrf_k
    assert fusion_calls["keyword_weight"] == Settings().keyword_weight
    assert fusion_calls["vector_weight"] == Settings().vector_weight

def test_hybrid_search_candidates_applies_tuning_knobs(monkeypatch):
    """rrf_k / weights / rerank_pool_size come from settings with env overrides."""
    query = "python"

    def mock_parse(q):
        return "", {"fts_query": "python"}

    def mock_db_fts(sql, params, db):
        return {}

    def mock_vector_search(query_text, candidate_ids, vector_db, warnings=None):
        return {"cand_1": 1, "cand_2": 2, "cand_3": 3}

    def mock_fusion(fts, vec, **kwargs):
        assert kwargs["k"] == 42
        assert kwargs["keyword_weight"] == 0.7
        assert kwargs["vector_weight"] == 1.3
        return [("cand_1", 0.05), ("cand_2", 0.04), ("cand_3", 0.03)], {}, {}

    def mock_explainer(params):
        return {"candidate_id": params.candidate_id, "rank": params.rank, "rrf_score": params.rrf_score}

    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setenv("CIP_RRF_K", "42")
    monkeypatch.setenv("CIP_KEYWORD_WEIGHT", "0.7")
    monkeypatch.setenv("CIP_VECTOR_WEIGHT", "1.3")
    monkeypatch.setenv("CIP_RERANK_POOL_SIZE", "2")
    monkeypatch.setattr(hs, "parse_query_to_sql", mock_parse)
    monkeypatch.setattr(hs, "execute_fts_query", mock_db_fts)
    monkeypatch.setattr(hs, "execute_vector_search", mock_vector_search)
    monkeypatch.setattr(hs, "reciprocal_rank_fusion", mock_fusion)
    monkeypatch.setattr(hs, "build_match_rationale", mock_explainer)
    monkeypatch.setattr(hs, "fetch_candidate_documents", lambda ids, db: ["d1", "d2"])

    gen = search_candidates(query, None, None)
    results = None
    for stage, progress, message, data in gen:
        if stage == "COMPLETE":
            results = data

    assert len(results) == 2

def test_execute_vector_search_respects_pool_size(monkeypatch):
    captured = {}

    class FakeSearch:
        def limit(self, n):
            captured["limit"] = n
            return self
        def to_list(self):
            return [{"candidate_id": f"c{i}"} for i in range(captured["limit"])]

    class FakeTable:
        def search(self, vector):
            return FakeSearch()

    class FakeVectorDB:
        def open_table(self, name):
            return FakeTable()

    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "generate_single_embedding", lambda text: [0.1, 0.2])
    monkeypatch.setenv("CIP_VECTOR_POOL_SIZE", "3")

    ranks = execute_vector_search("python dev", None, FakeVectorDB())

    assert captured["limit"] == 3
    assert len(ranks) == 3

def test_execute_vector_search_prefilters_before_limit(monkeypatch):
    """candidate restriction is applied inside the vector store before the limit."""
    calls = {}

    class FakeSearch:
        def where(self, clause, prefilter=None):
            calls["where"] = clause
            calls["prefilter"] = prefilter
            return self
        def limit(self, n):
            calls["limit"] = n
            return self
        def to_list(self):
            # Rows that fail the restriction would normally occupy the slice.
            return [
                {"candidate_id": "cand_pass_2"},
                {"candidate_id": "cand_fail"},
                {"candidate_id": "cand_pass_1"},
                {"candidate_id": "cand_pass_2"},
            ]

    class FakeTable:
        def search(self, vector):
            calls["searched"] = True
            return FakeSearch()

    class FakeVectorDB:
        def open_table(self, name):
            return FakeTable()

    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "generate_single_embedding", lambda text: [0.1, 0.2])

    ranks = execute_vector_search(
        "python dev", ["cand_pass_1", "cand_pass_2"], FakeVectorDB()
    )

    assert calls["searched"] is True
    assert calls["prefilter"] is True
    assert "'cand_pass_1'" in calls["where"]
    assert "'cand_pass_2'" in calls["where"]
    assert "cand_fail" not in calls["where"]
    assert calls["limit"] == Settings().vector_pool_size
    assert set(ranks) == {"cand_pass_2", "cand_pass_1"}

def test_execute_vector_search_no_restriction_for_pure_semantic(monkeypatch):
    """No keyword matches means no restriction: global search unchanged."""
    calls = {}

    class FakeSearch:
        def where(self, clause, prefilter=None):
            calls["where"] = clause
            return self
        def limit(self, n):
            return self
        def to_list(self):
            return [{"candidate_id": "anyone"}]

    class FakeTable:
        def search(self, vector):
            return FakeSearch()

    class FakeVectorDB:
        def open_table(self, name):
            return FakeTable()

    import candidate_intelligence_platform.search.hybrid_searcher as hs
    monkeypatch.setattr(hs, "generate_single_embedding", lambda text: [0.1, 0.2])

    ranks = execute_vector_search("python dev", None, FakeVectorDB())

    assert "where" not in calls
    assert ranks == {"anyone": 1}

def test_execute_vector_search_prefilter_end_to_end(tmp_path, monkeypatch):
    """Real LanceDB store: filtered candidate must survive even when it falls
    outside the global top slice that the limit would keep."""
    import lancedb
    from storage.vector_store import CandidateSectionVector

    def make_vec(base: float) -> list[float]:
        return [base] * 384

    db_path = str(tmp_path / "lancedb_prefilter")
    db = lancedb.connect(db_path)
    tbl = db.create_table("candidate_vectors", schema=CandidateSectionVector)

    rows = []
    for i in range(3):
        rows.append({
            "chunk_id": f"decoy_{i}",
            "candidate_id": "cand_decoy",
            "resume_version_id": f"rv_decoy_{i}",
            "section_type": "SUMMARY",
            "chunk_text": "decoy content",
            "vector": make_vec(1.0),
            "start_offset": 0,
            "end_offset": 13,
        })
    rows.append({
        "chunk_id": "target_chunk",
        "candidate_id": "cand_target",
        "resume_version_id": "rv_target",
        "section_type": "SKILLS",
        "chunk_text": "target skills",
        "vector": make_vec(0.5),
        "start_offset": 0,
        "end_offset": 13,
    })
    tbl.add(rows)

    query_vector = make_vec(1.0)
    monkeypatch.setattr(
        "candidate_intelligence_platform.search.hybrid_searcher.generate_single_embedding",
        lambda text: query_vector,
    )
    monkeypatch.setenv("CIP_VECTOR_POOL_SIZE", "2")

    restricted = execute_vector_search("skills", ["cand_target"], db)
    assert restricted == {"cand_target": 1}

    unrestricted = execute_vector_search("skills", None, db)
    assert unrestricted == {"cand_decoy": 1}

def test_fetch_candidate_documents_empty():
    from candidate_intelligence_platform.search.hybrid_searcher import fetch_candidate_documents
    docs = fetch_candidate_documents([], None)
    assert docs == []


def _run_pipeline_capturing_embedding(monkeypatch, query: str):
    """Run search_candidates with mocked stores; return the embedded text."""
    captured = {}

    class FakeSearch:
        def where(self, clause, prefilter=None):
            return self
        def limit(self, n):
            return self
        def to_list(self):
            return []

    class FakeTable:
        def search(self, vector):
            captured["vector_dim"] = len(vector)
            return FakeSearch()

    class FakeVectorDB:
        def open_table(self, name):
            return FakeTable()

    import candidate_intelligence_platform.search.hybrid_searcher as hs

    def fake_embed(text):
        captured["embedded_text"] = text
        return [0.1, 0.2]

    monkeypatch.setattr(hs, "generate_single_embedding", fake_embed)
    monkeypatch.setattr(hs, "execute_fts_query", lambda sql, params, db: {"cand_1": 1})
    monkeypatch.setattr(hs, "execute_strict_filter_query", lambda sql, params, db: ["cand_1"] if "location" in params or "yoe" in params else None)
    monkeypatch.setattr(hs, "reciprocal_rank_fusion", lambda fts, vec, **kw: (([("cand_1", 0.05)] if fts or vec else []), {}, {}))
    monkeypatch.setattr(hs, "rerank_candidates", lambda q, docs: [0.9])
    monkeypatch.setattr(hs, "build_match_rationale", lambda p: {"candidate_id": p.candidate_id})
    monkeypatch.setattr(hs, "fetch_candidate_documents", lambda ids, db: ["doc"])

    gen = search_candidates(query, None, FakeVectorDB())
    for stage, progress, message, data in gen:
        if stage == "COMPLETE":
            pass
    return captured.get("embedded_text")


def test_embedding_input_excludes_filter_values(monkeypatch):
    """Direct DSL query: only free text reaches the embedding step."""
    embedded = _run_pipeline_capturing_embedding(
        monkeypatch,
        "python AND location:'NYC' AND title:'senior engineer' AND yoe >= 2.5",
    )

    lowered = (embedded or "").lower()
    assert "python" in lowered
    assert "nyc" in lowered
    assert "senior engineer" in lowered
    assert "yoe" not in lowered
    assert "2.5" not in lowered


def test_embedding_input_clean_for_structured_api_flatten(monkeypatch):
    """Structured API request flattened to DSL still embeds free text only."""
    from api.routes.search import _build_search_query
    from api.schemas.search import SearchQueryRequest

    request = SearchQueryRequest(
        query_text="react developer",
        city="New York",
        min_yoe=3,
        title="frontend engineer",
    )
    flattened = _build_search_query(request)
    assert "location:'New York'" in flattened  # sanity: filters present in DSL

    embedded = _run_pipeline_capturing_embedding(monkeypatch, flattened)

    lowered = (embedded or "").lower()
    assert "react developer" in lowered
    assert "new york" in lowered
    assert "frontend engineer" in lowered
    assert "3" not in lowered


def test_pure_filter_query_skips_embedding(monkeypatch):
    """No free text at all: nothing gets embedded."""
    embedded = _run_pipeline_capturing_embedding(
        monkeypatch,
        "yoe >= 3",
    )

    assert embedded is None


def _run_pipeline(monkeypatch, query: str, fts_ranks: dict, vector_ranks: dict, docs: dict):
    import candidate_intelligence_platform.search.hybrid_searcher as hs

    class FakeSearch:
        def where(self, clause, prefilter=None):
            return self
        def limit(self, n):
            return self
        def to_list(self):
            return [{"candidate_id": cid} for cid in vector_ranks]

    class FakeTable:
        def search(self, vector):
            return FakeSearch()

    class FakeVectorDB:
        def open_table(self, name):
            return FakeTable()

    monkeypatch.setattr(hs, "generate_single_embedding", lambda text: [0.1, 0.2])
    monkeypatch.setattr(hs, "execute_fts_query", lambda sql, params, db: fts_ranks)
    monkeypatch.setattr(hs, "execute_strict_filter_query", lambda sql, params, db: list(fts_ranks.keys()))
    monkeypatch.setattr(hs, "execute_vector_search", lambda q, ids, vdb, warnings=None: vector_ranks)
    monkeypatch.setattr(hs, "fetch_candidate_documents", lambda ids, db: [docs.get(cid, "") for cid in ids])

    gen = search_candidates(query, None, FakeVectorDB(), return_warnings=True)
    for stage, progress, message, data in gen:
        if stage == "COMPLETE":
            results, warnings = data
    return results, warnings


def test_reranker_failure_preserves_fusion_order_and_warns(monkeypatch):
    import candidate_intelligence_platform.search.hybrid_searcher as hs

    def boom(q, docs):
        raise RuntimeError("cross-encoder exploded")

    monkeypatch.setattr(hs, "rerank_candidates", boom)

    results, warnings = _run_pipeline(
        monkeypatch,
        "python",
        fts_ranks={"cand_a": 1, "cand_b": 2, "cand_c": 3},
        vector_ranks={"cand_b": 1},
        docs={},
    )

    assert [r["candidate_id"] for r in results] == ["cand_b", "cand_a", "cand_c"]
    assert all(r["rerank_score"] is None for r in results)
    percentages = [r["match_percentage"] for r in results]
    assert len(set(percentages)) > 1
    assert any("reranking" in w.lower() for w in warnings)


def test_match_scorecards_populated_from_query_and_data(monkeypatch):
    results, _ = _run_pipeline(
        monkeypatch,
        "python AND location:'NYC' AND title:'senior engineer' AND yoe >= 2.5",
        fts_ranks={"cand_1": 1},
        vector_ranks={"cand_1": 2},
        docs={"cand_1": "Senior engineer fluent in python and docker"},
    )

    card = results[0]["match_scorecard"]
    assert {"field": "current_city", "operator": "CONTAINS", "value": "NYC"} in card["strict_filters"]
    assert {"field": "current_title", "operator": "CONTAINS", "value": "senior engineer"} in card["strict_filters"]
    assert {"field": "total_yoe", "operator": ">=", "value": 2.5} in card["strict_filters"]
    assert "python" in card["keyword_matches"]
    assert card["semantic_matches"][0]["vector_rank"] == 2

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

