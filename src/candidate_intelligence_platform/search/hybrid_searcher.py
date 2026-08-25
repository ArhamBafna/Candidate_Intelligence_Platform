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

def _describe_strict_filters(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn parsed query filter params into scorecard descriptors.

    Only exclusionary filters are listed: location, exact title (verbatim
    equality), and YoE. Soft title matches are surfaced via the
    `title_match` badge instead, never as strict filters.
    """
    descriptors: List[Dict[str, Any]] = []
    if "location" in params:
        descriptors.append({"field": "current_city", "operator": "CONTAINS", "value": params["location"]})
    if params.get("title_exact") and "title" in params:
        descriptors.append({"field": "current_title", "operator": "=", "value": params["title"]})
    if "yoe" in params:
        descriptors.append({"field": "total_yoe", "operator": ">=", "value": params["yoe"]})
    return descriptors


def _build_strict_filter_clause(params: Dict[str, Any]) -> Optional[str]:
    """Exclusionary SQL filters: location, and exact title only.

    The soft job title filter never contributes SQL here; it is scored via
    the vector/FTS query and the RRF exact-match bonus instead, so
    semantically related titles are never dropped before fusion.
    """
    where_parts: List[str] = []
    if "location" in params:
        where_parts.append("(candidates.current_city LIKE '%' || :location || '%' COLLATE NOCASE OR candidate_fts.resume_content LIKE '%' || :location || '%' COLLATE NOCASE)")
    if params.get("title_exact") and "title" in params:
        where_parts.append("(LOWER(candidates.current_title) = LOWER(:title))")
    if not where_parts:
        return None
    return "SELECT candidates.id FROM candidates JOIN candidate_fts ON candidates.id = candidate_fts.candidate_id WHERE " + " AND ".join(where_parts)


def resolve_title_match(
    candidate_id: str,
    params: Dict[str, Any],
    vector_ranks: Dict[str, int],
    candidate_metadata: Dict[str, Dict[str, Any]],
) -> str:
    """Classify why a candidate matched the job-title filter.

    Returns one of:
    - "exact": current_title equals the requested title verbatim
      (case-insensitive) - also the +20% RRF bonus definition.
    - "semantic": candidate surfaced through vector search, whose query
      contains the title text.
    - "none": candidate matched on keyword/other signals only.
    """
    target_title = params.get("title")
    if not target_title:
        return "none"
    meta = candidate_metadata.get(candidate_id, {})
    if meta.get("current_title") == target_title.lower():
        return "exact"
    if candidate_id in vector_ranks:
        return "semantic"
    return "none"

def _keyword_hits(fts_query: str, document: str) -> List[str]:
    """Free-text terms from the query that appear in the candidate document."""
    if not fts_query or not document:
        return []
    doc_lower = document.lower()
    seen: set = set()
    hits: List[str] = []
    for term in fts_query.split():
        key = term.lower()
        if key and key not in seen and key in doc_lower:
            seen.add(key)
            hits.append(term)
    return hits

def _semantic_signals(candidate_id: str, vector_ranks: Dict[str, int]) -> List[Dict[str, Any]]:
    """Semantic contribution of a candidate based on vector search placement."""
    if candidate_id not in vector_ranks:
        return []
    return [{"signal": "semantic_similarity", "vector_rank": vector_ranks[candidate_id]}]

def execute_fts_query(sql: str, params: Dict[str, Any], db: Session) -> Dict[str, int]:
    if not sql:
        return {}
    results = db.execute(text(sql), params).fetchall()
    ranks: Dict[str, int] = {}
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

def execute_strict_filter_query(sql: str, params: Dict[str, Any], db: Session) -> List[str]:
    if not sql or db is None:
        return []
    results = db.execute(text(sql), params).fetchall()
    return [row[0] for row in results]

def search_candidates(query: str, db: Session, vector_db: Any, return_warnings: bool = False, semantic_query: Optional[str] = None) -> Generator[Tuple[str, int, str, Any], None, None]:
    warnings: List[str] = []
    
    yield ("STARTING", 0, "Initializing search...", None)
    yield ("FTS_SEARCH", 20, "Executing keyword and filter query...", None)
    
    sql, params, clean_text = parse_query_to_sql(query)
    # The FTS query contains only unstructured free-text keywords
    fts_query = params.get("fts_query", "")
    
    fts_ranks = execute_fts_query(sql, params, db)
    
    # Strict (exclusionary) filters narrow the vector pool; soft title and
    # yoe never exclude candidates and therefore never restrict it.
    strict_sql = _build_strict_filter_clause(params)
    strict_filtered_ids = (
        execute_strict_filter_query(strict_sql, params, db) if strict_sql is not None else None
    )
    
    yield ("VECTOR_SEARCH", 40, "Performing semantic vector search...", None)
    
    vector_input = semantic_query if semantic_query else clean_text
    
    if strict_sql is not None and not strict_filtered_ids:
        # Strict filters applied but no matches found in SQLite.
        vector_ranks = {}
    else:
        # Vector search evaluates all candidates constrained ONLY by strict filters.
        vector_ranks = execute_vector_search(vector_input, strict_filtered_ids, vector_db, warnings=warnings)
    
    yield ("RANK_FUSION", 60, "Fusing keyword and semantic ranks...", None)
        
    settings = Settings()
    
    from storage.db_models import Candidate
    all_cids = set(fts_ranks.keys()).union(vector_ranks.keys())
    candidate_metadata = {}
    if all_cids and db is not None:
        rows = db.query(Candidate.id, Candidate.total_yoe, Candidate.current_title, Candidate.current_city).filter(Candidate.id.in_(all_cids)).all()
        for r in rows:
            candidate_metadata[r.id] = {
                "total_yoe": r.total_yoe,
                "current_title": (r.current_title or "").lower(),
                "current_city": (r.current_city or "").lower()
            }

    rrf_results, soft_penalties, soft_bonuses = reciprocal_rank_fusion(
        fts_ranks,
        vector_ranks,
        candidate_metadata=candidate_metadata,
        params=params,
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
    rerank_input = semantic_query if semantic_query else clean_text
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
            soft_penalties=soft_penalties.get(cid, []),
            soft_bonuses=soft_bonuses.get(cid, []),
            title_match=resolve_title_match(cid, params, vector_ranks, candidate_metadata),
        )
        rationale = build_match_rationale(params_obj)
        results.append(rationale)
        
    final_result = (results, warnings) if return_warnings else results
    yield ("COMPLETE", 100, "Search complete.", final_result)

