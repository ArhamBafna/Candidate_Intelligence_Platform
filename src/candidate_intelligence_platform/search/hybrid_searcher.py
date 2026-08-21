from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Callable, Dict, List, Any, Generator, Tuple
import json
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
from candidate_intelligence_platform.search.rank_fusion import reciprocal_rank_fusion
from candidate_intelligence_platform.search.reranker import rerank_candidates
from candidate_intelligence_platform.intelligence.explainer import build_match_rationale
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings, generate_single_embedding
import structlog

logger = structlog.get_logger(__name__)

def execute_fts_query(sql: str, params: dict, db: Session) -> Dict[str, int]:
    if not sql:
        return {}
    results = db.execute(text(sql), params).fetchall()
    ranks = {}
    for rank, row in enumerate(results, start=1):
        ranks[row[0]] = rank
    return ranks

def execute_vector_search(query_text: str, candidate_ids: Optional[List[str]], vector_db: Any, warnings: Optional[List[str]] = None) -> Dict[str, int]:
    """Execute vector search with early termination optimizations."""
    # EARLY TERMINATION: Skip if no query text
    if not query_text:
        return {}
    
    # EARLY TERMINATION: If candidate_ids was provided (from FTS filters) but is empty,
    # it means no candidates matched the hard filters. In this case, we skip vector search.
    # Note: search_candidates passes None if FTS matched everything or if FTS was skipped,
    # which means we search against ALL candidates.
    if candidate_ids is not None and not candidate_ids:
        return {}
    
    # Compute embedding (needed for error logging even if vector_db unavailable)
    try:
        query_vector = list(generate_single_embedding(query_text))
    except Exception as e:
        logger.warning("ai_vector_search_failed", query=query_text, error=str(e), action="falling_back_to_keyword_search")
        if warnings is not None:
            warnings.append("Semantic vector search skipped (embedding model unavailable); showing keyword matches.")
        return {}
    
    # EARLY TERMINATION: Skip if vector DB unavailable
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
        # Optimization: if we have a specific set of candidate IDs, we could potentially
        # push that filter down to LanceDB, but for now we filter in memory after the search.
        results = table.search(query_vector).limit(100).to_list()
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

def search_candidates(query: str, db: Session, vector_db: Any, return_warnings: bool = False) -> Generator[Tuple[str, int, str, Any], None, None]:
    warnings = []
    
    yield ("STARTING", 0, "Initializing search...", None)
    yield ("FTS_SEARCH", 20, "Executing keyword and filter query...", None)
    
    sql, params = parse_query_to_sql(query)
    fts_query = params.get("fts_query", query)
    
    fts_ranks = execute_fts_query(sql, params, db)
    
    # We want to search within the filtered set if filters were applied.
    # If no results from FTS, we still want to try vector search on all candidates
    # UNLESS there were hard filters (like location/yoe) that yielded 0 matches.
    
    # Check if there were hard filters in the query
    has_hard_filters = "location" in params or "yoe" in params
    filtered_ids = list(fts_ranks.keys())
    
    # If there are hard filters and no one matched them, skip vector search.
    # Otherwise, if it's just a text query and FTS failed, or if some matched, proceed.
    if has_hard_filters and not filtered_ids:
        vector_ranks = {}
    else:
        yield ("VECTOR_SEARCH", 40, "Performing semantic vector search...", None)
        # If no filtered_ids (but no hard filters), we search against ALL candidates by passing None
        vector_ranks = execute_vector_search(fts_query, filtered_ids or None, vector_db, warnings=warnings)
    
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
        params_obj = MatchParameters(candidate_id=cid, rank=rank, rrf_score=rrf, rerank_score=score)
        rationale = build_match_rationale(params_obj)
        results.append(rationale)
        
    final_result = (results, warnings) if return_warnings else results
    yield ("COMPLETE", 100, "Search complete.", final_result)

