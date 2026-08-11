import re

def parse_query_to_sql(query: str) -> tuple[str, dict]:
    """
    Parses a strict query string into a SQL query and parameters.
    Currently supports:
    - location:'VALUE'
    - yoe >= VALUE
    - remaining keywords for FTS5 MATCH
    """
    sql_parts = []
    params = {}
    
    # Extract location
    loc_match = re.search(r"location:'([^']+)'", query)
    if loc_match:
        sql_parts.append("candidates.current_city = :location")
        params["location"] = loc_match.group(1)
        query = query.replace(loc_match.group(0), "")
        
    # Extract yoe
    yoe_match = re.search(r"yoe\s*>=\s*(\d+)", query)
    if yoe_match:
        sql_parts.append("candidates.total_yoe >= :yoe")
        params["yoe"] = int(yoe_match.group(1))
        query = query.replace(yoe_match.group(0), "")
        
    # The rest is assumed to be FTS text. 
    # Let's clean up stray 'AND's.
    fts_query = query.replace("AND", "").strip()
    fts_query = re.sub(r'\s+', ' ', fts_query).strip()
    
    if fts_query:
        sql_parts.append("candidate_fts MATCH :fts_query")
        params["fts_query"] = fts_query

    where_clause = " AND ".join(sql_parts)
    
    sql = "SELECT candidates.id FROM candidates " \
          "JOIN candidate_fts ON candidates.id = candidate_fts.candidate_id "
          
    if where_clause:
        sql += f"WHERE {where_clause}"
    
    return sql, params
