# Task Tracker

- [x] Ticket 01: Missing Unit & Edge-Case Test Coverage
  - [x] Test `get_recent_logs(limit=N)` verifies truncation when buffer has more items than limit (`config/logging.py:15`).
  - [x] Test `memory_buffer_processor` verifies log entries are prepended with buffer lock acquired (`config/logging.py:10`).
  - [x] Test `extract_inferences` mocks `ollama.chat` to return malformed JSON / throw exception, asserting empty list returned and warning emitted (`local_llm_fallback.py:42`).
  - [x] Test `parse_query_to_sql` handles free-text queries without `location:` or `yoe >=` filters (`ast_parser.py:3`).
  - [x] Test `fetch_candidate_documents` short-circuits to empty list when `candidate_ids` is empty (`hybrid_searcher.py:72`).
  - [x] Test database engine connect event ignores non-sqlite DBAPI connections without executing PRAGMAs (`config/database.py:12`).
  - [x] Test `execute_vector_search` handles missing `candidate_vectors` table gracefully by recording warning and returning empty dict (`hybrid_searcher.py:37`).
  - [x] `uv run pytest tests/` passes with all new tests green.

- [x] Ticket 02: Algorithmic & In-Memory Performance Optimization
  - [x] Add `@functools.lru_cache(maxsize=1024)` to single-query embedding generation in `embeddings.py:6`.
  - [x] Convert `candidate_ids` to `set` in `execute_vector_search` in `hybrid_searcher.py:64` for O(1) membership checks.
  - [x] Precompile `KNOWN_SKILLS` regular expressions at module level in `deterministic_ner.py:47`.
  - [x] Convert `rrf_results` into dictionary lookup in `search_candidates` in `hybrid_searcher.py:137`.
  - [x] Use `collections.defaultdict(float)` in `reciprocal_rank_fusion` in `rank_fusion.py:8`.
  - [x] `uv run pytest tests/` passes.

- [x] Ticket 03: Database Batch Queries & Async Event-Loop Unblocking
  - [x] `/search` endpoint in `api/routes/search.py:47` fetches candidate details in a single bulk query using `Candidate.id.in_(top_ids)`.
  - [x] `/search/stream` endpoint in `api/routes/search.py:138` uses bulk candidate retrieval.
  - [x] `stream_upload_generator` in `api/routes/candidates.py:517` runs file hashing and DB queries via `asyncio.to_thread`.
  - [x] `batch_stream_generator` in `api/routes/candidates.py:705` runs DB queries via `asyncio.to_thread`.
  - [x] Confirm `candidate_id` is set on vector chunks in `api/routes/candidates.py:612`.
  - [x] `uv run pytest tests/` passes.

- [x] Ticket 04: Security Hardening (FTS Query Sanitization & CORS Restrictions)
  - [x] `parse_query_to_sql` in `ast_parser.py:35` strips or escapes unbalanced quotes and illegal FTS5 operators before building match clause.
  - [x] CORS middleware in `api/main.py:44` sets `allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]` and `allow_headers=["*"]`.
  - [x] `uv run pytest tests/` passes.

- [x] Ticket 05: Code Simplification & Long Function Decomposition
  - [x] Refactor `build_match_rationale` in `explainer.py:3` to accept a structured dataclass or Pydantic model (`MatchParameters`) and update callers in `hybrid_searcher.py`.
  - [x] Split `extract_candidate_profile_hybrid` in `hybrid_extractor.py:44` into discrete helper functions (deterministic extraction, LLM fallback, score consolidation).
  - [x] Split `perform_search_stream` in `api/routes/search.py:90` into cohesive modular pipeline steps.
  - [x] `uv run pytest tests/` passes without breaking existing API contracts.

- [x] Ticket 06: PDF Parser OCR Fallback & Final Verification
  - [x] Add `pytesseract` fallback in `ingestion/parsers/pdf_parser.py:44` when extracted text length is below threshold.
  - [x] Add unit test verifying OCR fallback execution with a mocked image page.
  - [x] Run full test suite: `uv run pytest`.
  - [x] Run `/code-review` across all changed files.
