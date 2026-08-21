from sqlalchemy import text
from typing import Optional, Callable
import json
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
from candidate_intelligence_platform.search.rank_fusion import reciprocal_rank_fusion
from candidate_intelligence_platform.search.reranker import rerank_candidates
from candidate_intelligence_platform.intelligence.explainer import build_match_rationale
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings, generate_single_embedding
import structlog

logger = structlog.get_logger(__name__)

def execute_fts_query(sql: str, params: dict, db) -> dict[str, int]:
    if not sql:
        return {}
    results = db.execute(text(sql), params).fetchall()
    ranks = {}
    for rank, row in enumerate(results, start=1):
        ranks[row[0]] = rank
    return ranks

def execute_vector_search(query_text: str, candidate_ids: list[str], vector_db, warnings: list[str] = None) -> dict[str, int]:
    if not query_text:
        return {}
    
    try:
        query_vector = list(generate_single_embedding(query_text))
    except Exception as e:
        logger.warning("ai_vector_search_failed", query=query_text, error=str(e), action="falling_back_to_keyword_search")
        if warnings is not None:
            warnings.append("Semantic vector search skipped (embedding model unavailable); showing keyword matches.")
        return {}
    
    if vector_db is None:
        if warnings is not None:
            warnings.append("Semantic vector search skipped (LanceDB connection unavailable); showing keyword matches.")
        return {}

    try:
        table = vector_db.open_table("candidate_vectors")
    except Exception:
        # Table might not exist if no resumes uploaded
        if warnings is not None:
            warnings.append("Semantic vector search skipped (candidate_vectors table not found); showing keyword matches.")
        return {}
        
    try:
        results = table.search(query_vector).limit(100).to_list()
    except Exception as e:
        logger.warning("ai_vector_search_failed", query=query_text, error=str(e), action="falling_back_to_keyword_search")
        if warnings is not None:
            warnings.append(f"Semantic vector search skipped ({str(e)}); showing keyword matches.")
        return {}
    
    ranks = {}
    current_rank = 1
    # candidate_ids contains the pre-filtered IDs (e.g. from FTS or AST filters)
    # If candidate_ids is empty, it means no candidates matched the FTS/AST filters,
    # so we shouldn't return anything.
    if not candidate_ids:
        return {}
        
    candidate_ids_set = set(candidate_ids)
        
    for r in results:
        cid = r.get("candidate_id")
        if cid in candidate_ids_set and cid not in ranks:
            ranks[cid] = current_rank
            current_rank += 1
            
    return ranks

def fetch_candidate_documents(candidate_ids: list[str], db) -> list[str]:
    if not candidate_ids:
        return []
        
    from storage.db_models import ResumeVersion
    
    docs = db.query(ResumeVersion.candidate_id, ResumeVersion.raw_text).filter(
        ResumeVersion.candidate_id.in_(candidate_ids),
        ResumeVersion.is_primary == True
    ).all()
    
    doc_map = {row.candidate_id: row.raw_text for row in docs}
    return [doc_map.get(cid, "") for cid in candidate_ids]

def search_candidates(query: str, db, vector_db, return_warnings: bool = False):
    warnings = []
    
    yield ("STARTING", 0, "Initializing search...", None)
    yield ("FTS_SEARCH", 20, "Executing keyword and filter query...", None)
    
    sql, params = parse_query_to_sql(query)
    fts_query = params.get("fts_query", query)
    
    fts_ranks = execute_fts_query(sql, params, db)
    
    filtered_ids = list(fts_ranks.keys())
    
    yield ("VECTOR_SEARCH", 40, "Performing semantic vector search...", None)
    try:
        vector_ranks = execute_vector_search(fts_query, filtered_ids, vector_db, warnings=warnings)
    except TypeError:
        vector_ranks = execute_vector_search(fts_query, filtered_ids, vector_db)
    
    yield ("RANK_FUSION", 60, "Fusing keyword and semantic ranks...", None)
        
    rrf_results = reciprocal_rank_fusion(fts_ranks, vector_ranks)
    
    if not rrf_results:
        final_result = ([], warnings) if return_warnings else []
        yield ("COMPLETE", 100, "Search complete. No matches found.", final_result)
        return
        
    top_candidates = [cid for cid, score in rrf_results[:50]]
    
    yield ("DB_HYDRATION", 70, "Fetching candidate profiles...", None)
        
    documents = fetch_candidate_documents(top_candidates, db)
    
    yield ("RERANKING", 80, "Reranking top matches...", None)
        
    try:
        rerank_scores = rerank_candidates(query, documents)
    except Exception as e:
        logger.warning("ai_reranking_failed", query=query, error=str(e), action="falling_back_to_rrf_scores")
        rerank_scores = [0.0] * len(top_candidates)
    
    reranked = sorted(zip(top_candidates, rerank_scores), key=lambda x: x[1], reverse=True)
    
    from candidate_intelligence_platform.intelligence.explainer import MatchParameters
    
    results = []
    rrf_dict = dict(rrf_results)
    for rank, (cid, score) in enumerate(reranked, start=1):
        rrf = rrf_dict.get(cid, 0.0)
        params = MatchParameters(candidate_id=cid, rank=rank, rrf_score=rrf, rerank_score=score)
        rationale = build_match_rationale(params)
        results.append(rationale)
        
    final_result = (results, warnings) if return_warnings else results
    yield ("COMPLETE", 100, "Search complete.", final_result)

