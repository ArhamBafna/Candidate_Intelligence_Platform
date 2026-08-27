import pytest

from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql


@pytest.mark.parametrize("query,sql_fragments,expected_params,expected_clean", [
    # 1. Plain keywords only
    (
        "python java developer",
        ["candidate_fts MATCH :fts_query"],
        {"fts_query": "python java developer"},
        "python java developer",
    ),
    # 2. location filter only
    (
        "location:'San Francisco'",
        ["current_city", "LIKE"],
        {"location": "San Francisco"},
        "San Francisco",
    ),
    # 3. title soft filter (no SQL fragment of its own)
    (
        "title:'Backend Engineer' python",
        ["candidate_fts MATCH :fts_query"],
        {"title": "Backend Engineer", "fts_query": "python"},
        "Backend Engineer python",
    ),
    # 4. title_exact filter (strict SQL equality)
    (
        "title_exact:'Backend Engineer'",
        ["LOWER(candidates.current_title) = LOWER(:title)"],
        {"title": "Backend Engineer", "title_exact": True},
        "Backend Engineer",
    ),
    # 5. yoe >= filter (soft, no SQL)
    (
        "title:'Dev' yoe >= 5 python",
        ["candidate_fts MATCH :fts_query"],
        {"title": "Dev", "yoe": 5.0, "fts_query": "python"},
        "Dev python",
    ),
    # 6. Combined filters
    (
        "location:'NYC' title:'Senior' yoe >= 3 python docker",
        ["current_city", "candidate_fts MATCH :fts_query"],
        {"location": "NYC", "title": "Senior", "yoe": 3.0, "fts_query": "python docker"},
        "NYC Senior python docker",
    ),
    # 7. AND stripping
    (
        "python AND java AND docker",
        ["candidate_fts MATCH :fts_query"],
        {"fts_query": "python java docker"},
        "python java docker",
    ),
    # 8. Word containing AND survives
    (
        "SANDPAPER python",
        ["candidate_fts MATCH :fts_query"],
        {"fts_query": "SANDPAPER python"},
        "SANDPAPER python",
    ),
    # 9. Unbalanced quotes stripped
    (
        "python's world",
        [],
        {"fts_query": "pythons world"},
        "pythons world",
    ),
    # 10. FTS5 illegal chars stripped
    (
        "python+java/c++",
        [],
        {"fts_query": "python java c"},
        "python java c",
    ),
])
def test_parse_query_to_sql(query, sql_fragments, expected_params, expected_clean):
    sql, params, clean_text = parse_query_to_sql(query)

    for frag in sql_fragments:
        assert frag in sql, f"Expected '{frag}' in SQL: {sql}"

    for key, value in expected_params.items():
        assert key in params, f"Missing param key '{key}'"
        assert params[key] == value, f"params[{key}] = {params[key]!r}, expected {value!r}"

    assert clean_text == expected_clean
