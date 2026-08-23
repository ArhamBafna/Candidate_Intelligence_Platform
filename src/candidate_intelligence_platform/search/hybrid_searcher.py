from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Callable, Dict, List, Any, Generator, Tuple
import json
from config.settings import Settings
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
from candidate_intelligence_platform.search.rank_fusion import reciprocal_rank_fusion
from candidate_intelligence_platform.search.reranker import rerank_candidates
from candidate_intelligence_platform.intelligence.explainer import build_match_rationale
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings, generate_single_embedding
import structlog

logger = structlog.get_logger(__name__)

def _describe_strict_filters(params: dict) -> list:
    """Turn parsed query filter params into scorecard descriptors."""
    descriptors = []
    if "location" in params:
        descriptors.append({"field": "current_city", "operator": "=", "value": params["location"]})
    if "title" in params:
        descriptors.append({"field": "current_title", "operator": "=", "value": params["title"]})
    if "yoe" in params:
        descriptors.append({"field": "total_yoe", "operator": ">=", "value": params["yoe"]})
    return descriptors

def _keyword_hits(fts_query: str, document: str) -> list:
    """Free-text terms from the query that appear in the candidate document."""
    if not fts_query or not document:
        return []
    doc_lower = document.lower()
    seen = set()
    hits = []
    for term in fts_query.split():
        key = term.lower()
        if key and key not in seen and key in doc_lower:
            seen.add(key)
            hits.append(term)
    return hits

def _semantic_signals(candidate_id: str, vector_ranks: Dict[str, int]) -> list:
    """Semantic contribution of a candidate based on vector search placement."""
    if candidate_id not in vector_ranks:
        return []
    return [{"signal": "semantic_similarity", "vector_rank": vector_ranks[candidate_id]}]

def execute_fts_query(sql: str, params: dict, db: Session) -> Dict[str, int]:
    if not sql:
        return {}
    results = db.execute(text(sql), params).fetchall()
    ranks = {}
    for rank, row in enumerate(results, start=1):
        ranks[row[0]] = rank
    return ranks

def execute_vector_search(query_text: str, candidate_ids: Optional[List[str]], vector_db: Any, warnings: Optional[List[str]] = None) -> Dict[str, int]:
    """Execute vector search."""
    if not query_text:
        return {}
    
    # Compute embedding (needed for error logging even if vector_db unavailable)
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
        
    pool_size = Settings().vector_pool_size
    try:
        search_query = table.search(query_vector)
        if candidate_ids:
            # Restriction must be applied as a prefilter so it takes effect
            # before the pool-size limit truncates the result list.
            escaped_ids = ",".join("'" + cid.replace("'", "''") + "'" for cid in candidate_ids)
            search_query = search_query.where(f"candidate_id IN ({escaped_ids})", prefilter=True)
        results = search_query.limit(pool_size).to_list()
    except Exception as e:
        logger.warning("ai_vector_search_failed", query=query_text, error=str(e), action="falling_back_to_keyword_search")
        if warnings is not None:
            warnings.append(f"Semantic vector search skipped ({str(e)}); showing keyword matches.")
        return {}
    
    ranks = {}
    current_rank = 1
    
    # If candidate_ids is provided, filter results. If None, return all.
    candidate_ids_set = set(candidate_ids) if candidate_ids is not None else None
        
    for r in results:
        cid = r.get("candidate_id")
        if (candidate_ids_set is None or cid in candidate_ids_set) and cid not in ranks:
            ranks[cid] = current_rank
            current_rank += 1
            
    return ranks

def fetch_candidate_documents(candidate_ids: List[str], db: Session) -> List[str]:
    if not candidate_ids:
        return []
        
    from storage.db_models import ResumeVersion
    
    docs = db.query(ResumeVersion.candidate_id, ResumeVersion.raw_text).filter(
        ResumeVersion.candidate_id.in_(candidate_ids),
        ResumeVersion.is_primary == True
    ).all()
    
    doc_map = {row.candidate_id: row.raw_text for row in docs}
    return [doc_map.get(cid, "") for cid in candidate_ids]

def search_candidates(query: str, db: Session, vector_db: Any, return_warnings: bool = False, semantic_query: Optional[str] = None) -> Generator[Tuple[str, int, str, Any], None, None]:
    warnings = []
    
    yield ("STARTING", 0, "Initializing search...", None)
    yield ("FTS_SEARCH", 20, "Executing keyword and filter query...", None)
    
    sql, params = parse_query_to_sql(query)
    # Embed ONLY the cleaned free-text portion; structured filter values
    # (city, title, min yoe) must never ride along into the embedding input.
    fts_query = params.get("fts_query", "")
    
    fts_ranks = execute_fts_query(sql, params, db)
    filtered_ids = list(fts_ranks.keys())
    
    yield ("VECTOR_SEARCH", 40, "Performing semantic vector search...", None)
    # If no filtered_ids, search across all candidates in vector index.
    # semantic_query overrides the embedding input (e.g. distilled job-ad
    # summary); it is still pure free text with no filter tokens.
    vector_input = semantic_query if semantic_query else fts_query
    vector_ranks = execute_vector_search(vector_input, filtered_ids or None, vector_db, warnings=warnings)
    
    yield ("RANK_FUSION", 60, "Fusing keyword and semantic ranks...", None)
        
    settings = Settings()
    rrf_results = reciprocal_rank_fusion(
        fts_ranks,
        vector_ranks,
        k=settings.rrf_k,
        keyword_weight=settings.keyword_weight,
        vector_weight=settings.vector_weight
    )
    
    if not rrf_results:
        final_result = ([], warnings) if return_warnings else []
        yield ("COMPLETE", 100, "Search complete. No matches found.", final_result)
        return
        
    top_candidates = [cid for cid, score in rrf_results[:settings.rerank_pool_size]]
    
    yield ("DB_HYDRATION", 70, "Fetching candidate profiles...", None)
        
    documents = fetch_candidate_documents(top_candidates, db)
    
    yield ("RERANKING", 80, "Reranking top matches...", None)

    doc_map = dict(zip(top_candidates, documents))
    strict_filters = _describe_strict_filters(params)
    rerank_input = semantic_query if semantic_query else query
    try:
        rerank_scores = rerank_candidates(rerank_input, documents)
        reranked = sorted(zip(top_candidates, rerank_scores), key=lambda x: x[1], reverse=True)
    except Exception as e:
        logger.warning("ai_reranking_failed", query=query, error=str(e), action="keeping_fusion_order")
        warnings.append("AI reranking failed; showing fused ranking without AI re-ordering.")
        # Honest degradation: keep fusion order, no synthetic rerank scores.
        reranked = [(cid, None) for cid in top_candidates]

    from candidate_intelligence_platform.intelligence.explainer import MatchParameters

    results = []
    rrf_dict = dict(rrf_results)
    for rank, (cid, score) in enumerate(reranked, start=1):
        rrf = rrf_dict.get(cid, 0.0)
        params_obj = MatchParameters(
            candidate_id=cid,
            rank=rank,
            rrf_score=rrf,
            rerank_score=score,
            strict_filters=strict_filters,
            keyword_matches=_keyword_hits(fts_query, doc_map.get(cid, "")),
            semantic_matches=_semantic_signals(cid, vector_ranks),
        )
        rationale = build_match_rationale(params_obj)
        results.append(rationale)
        
    final_result = (results, warnings) if return_warnings else results
    yield ("COMPLETE", 100, "Search complete.", final_result)

