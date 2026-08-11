import pytest
from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql

def test_parse_query_to_sql():
    query = "python AND location:'NYC' AND yoe >= 5"
    sql, params = parse_query_to_sql(query)
    
    assert "candidates.current_city = :location" in sql
    assert "candidates.total_yoe >= :yoe" in sql
    assert "candidate_fts MATCH :fts_query" in sql
    
    assert params["location"] == "NYC"
    assert params["yoe"] == 5
    assert "python" in params["fts_query"]
