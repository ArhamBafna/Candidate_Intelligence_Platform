import re
import functools

# Each spec: compiled filter pattern, SQL fragment it contributes, bound
# parameter name, and the cast applied to the captured value.
FILTER_SPECS: list[tuple[re.Pattern[str], str, str, type]] = [
    (re.compile(r"\blocation:'([^']+)'"), "(candidates.current_city LIKE '%' || :location || '%' COLLATE NOCASE OR candidate_fts.resume_content LIKE '%' || :location || '%' COLLATE NOCASE)", "location", str),
    (re.compile(r"\btitle:'([^']+)'"), "(candidates.current_title LIKE '%' || :title || '%' COLLATE NOCASE OR candidate_fts.resume_content LIKE '%' || :title || '%' COLLATE NOCASE)", "title", str),
    (re.compile(r"\byoe\s*>=\s*(\d+(?:\.\d+)?)"), "", "yoe", float),
]

@functools.lru_cache(maxsize=1024)
def parse_query_to_sql(query: str) -> tuple[str, dict[str, object], str]:
    """
    Parses a strict query string into a SQL query and parameters.
    Currently supports:
    - location:'VALUE'
    - title:'VALUE' (case-insensitive equality on candidates.current_title)
    - yoe >= VALUE (integer or decimal)
    - remaining keywords for FTS5 MATCH, ordered by bm25 relevance
    """
    sql_parts: list[str] = []
    params: dict[str, object] = {}
    clean_parts: list[str] = []

    # Extract structured filters so they never leak into the FTS match string
    for pattern, sql_fragment, param_name, cast in FILTER_SPECS:
        match_obj = pattern.search(query)
        if match_obj:
            if sql_fragment:
                sql_parts.append(sql_fragment)
            params[param_name] = cast(match_obj.group(1))
            
            # Keep the natural language string for embeddings/reranking (except yoe)
            if param_name != "yoe":
                clean_parts.append(match_obj.group(1))
                
            query = query.replace(match_obj.group(0), "")

    # The rest is assumed to be FTS text.
    # Strip standalone AND operators only; words merely containing AND
    # (e.g. SANDPAPER) must survive cleanup intact.
    fts_query = re.sub(r"\bAND\b", " ", query).strip()

    # Strip unbalanced quotes
    if fts_query.count('"') % 2 != 0:
        fts_query = fts_query.replace('"', '')
    if fts_query.count("'") % 2 != 0:
        fts_query = fts_query.replace("'", '')

    # Remove FTS5 illegal characters including -, /, and +
    fts_query = re.sub(r'[!()*^{}\[\]~:\-\/+]', ' ', fts_query)
    fts_query = re.sub(r'\s+', ' ', fts_query).strip()

    if fts_query:
        sql_parts.append("candidate_fts MATCH :fts_query")
        params["fts_query"] = fts_query

    # Create a clean natural language text for vector search and reranking
    clean_text_parts = clean_parts + ([fts_query] if fts_query else [])
    clean_text = " ".join(clean_text_parts).strip()

    where_clause = " AND ".join(sql_parts)

    sql = "SELECT candidates.id FROM candidates " \
          "JOIN candidate_fts ON candidates.id = candidate_fts.candidate_id "

    if where_clause:
        sql += f"WHERE {where_clause}"

    # Rank keyword matches by FTS5 relevance (bm25 ascending = best first)
    if params.get("fts_query"):
        sql += " ORDER BY bm25(candidate_fts)"

    return sql, params, clean_text
