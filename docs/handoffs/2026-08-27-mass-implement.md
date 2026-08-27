# Session Handoff — 2026-08-27

## What Done

### Change 1: SQL injection fix in `_delete_vectors`
- File: `storage/index_writer.py:103-104`
- Problem: `candidate_id` interpolated directly into LanceDB delete predicate via f-string
- Fix: `safe_id = candidate_id.replace('"', '""')` before interpolation
- Doubles embedded double-quotes (standard SQLite string escaping)

### Change 2: AST parser test suite
- File: `tests/test_ast_parser.py` (new, 82 lines)
- 10 parametrized tests via `@pytest.mark.parametrize`
- Covers: plain keywords, location/title/title_exact/yoe filters, combined filters, AND stripping, SANDPAPER survival, unbalanced quotes, FTS5 illegal chars
- All use `parse_query_to_sql` from `src/candidate_intelligence_platform/search/ast_parser.py`

### Change 3: Index writer test suite
- File: `tests/test_index_writer.py` (new, 115 lines)
- 9 tests covering `_has_candidate_vectors_table` and `_delete_vectors`
- Tests: modern API path (`delete_candidate_vectors`), table fallback path, SQL injection escape path, no-op when vector_db is None, no-op when no table
- Direct coverage for Change 1 fix

### Change 4: Intake error path tests
- File: `tests/test_intake.py` (3 tests appended)
- `test_purge_cas_object_on_delete_exception`: CAS delete raises, warning captured, no propagation
- `test_ingest_file_fts_update_failure_returns_partial`: FTS write fails, returns PARTIAL, warning recorded
- `test_parse_raw_text_falls_back_on_parser_exception`: PDF parser raises, raw decode fallback, warning recorded

## Test Results
- 253 passed, 6 skipped (ollama/eval tests need flags)
- All new tests use mocked heavy models (spaCy, embeddings, LLM)
- All tests under 2s

## Review Cycles
1. Round 1: Found 9 issues (unused import, unreadable mock, missing annotations, comment mismatch, shotgun surgery, inline class, parametrize missing, matched_id missing, unnecessary rollback)
2. Round 2: Found 2 issues (missing index_writer tests, redundant monkeypatching)
3. Round 3: Found 0 issues worth implementing

## Files Changed
```
 storage/index_writer.py     | 2 lines changed
 tests/test_ast_parser.py    | 82 lines (new)
 tests/test_index_writer.py  | 115 lines (new)
 tests/test_intake.py        | 105 lines appended
```

## Commit
```
f2e518a fix: SQL injection in _delete_vectors + test coverage for AST parser, index_writer, and intake error paths
```

## Pushed
- Branch: main
- Remote: origin/main
