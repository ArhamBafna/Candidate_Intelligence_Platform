# Task Tracker

## Centralized AI Prompts (Issue #24)

- [x] Create `src/candidate_intelligence_platform/prompts.py`: catalog comment block + three private templates + named builders
- [x] Move fact-extraction prompt (was inline in `extraction/local_llm_fallback.py`), byte-identical
- [x] Move candidate match-insight prompt (was inline in `api/routes/candidates.py`), byte-identical
- [x] Move job-ad distillation prompt (was `_DISTILL_PROMPT` in `search/job_ad_distiller.py`; missed by the issue inventory), byte-identical
- [x] Byte-identity snapshot guard tests in `tests/test_prompts.py`
- [x] AGENTS.md rule: every LLM prompt defined in the prompts module via a named builder
- [x] Full suite green with models mocked

## Unified Intake Pipeline (Issue #12)

- [x] Ticket U1: Spec — unified resume intake pipeline (Deepening #1)
  - [x] Add Ticket U1 checklist to docs/task.md
  - [x] Commit 1: intake module (`src/candidate_intelligence_platform/ingestion/intake.py`) + settings dials + `classify_document` move + `tests/test_intake.py` units
  - [x] Commit 2: `/upload` + `/upload-stream` doors onto `ingest_file`, SSE progress adapter, possible-duplicate UI chip
  - [x] Commit 3: three reprocess doors onto `reprocess_text`
  - [x] Commit 4: bulk script delegates to `ingest_file`, legacy report strings preserved
  - [x] Full suite green after each commit

## Performance Optimization Tickets

- [x] Ticket P0: Baseline & benchmark harness
  - [x] Create `tests/test_performance.py` with pytest-benchmark gates
  - [x] Add `pytest-benchmark` dependency to pyproject.toml
  - [x] Benchmark upload and search pipelines on test-resumes/

- [x] Ticket P1: Kill double spaCy pass + truncate NER input
  - [x] Add `facts` parameter to `extract_candidate_profile_hybrid` (backward-compatible)
  - [x] Add `assess_tier1` helper function for reuse
  - [x] Update upload-stream, reprocess-stream, batch-reprocess-stream to compute facts once
  - [x] Truncate spaCy NER input to first 5000 chars (names/locations always in header)
  - [x] Verify all existing tests pass

- [x] Ticket P2: Thread-offload CPU/IO + fix thread-safety
  - [x] Wrap `cas_mgr.store`, parsers, extraction, chunking, embeddings in `asyncio.to_thread`
  - [x] Fix thread-safety: SQLite session usage across threads
  - [x] Bounded asyncio semaphore for concurrent uploads
  - [x] Thread-offload single upload endpoint
  - [x] Verify all existing tests pass

- [x] Ticket P3: DB indexes + single-transaction writes + busy_timeout
  - [x] Add `PRAGMA busy_timeout=5000` in database.py
  - [x] Add FK indexes: resume_versions(candidate_id), candidate_claims(candidate_id), candidate_timeline_events(candidate_id)
  - [x] Remove internal commits from TimelineLedger.log_event
  - [x] Remove internal commits from CandidateService.update_fts_index
  - [x] Add hash dedup to single /upload endpoint
  - [x] Batch batch_delete_candidates with single commit
  - [x] Verify all existing tests pass

- [x] Ticket P4: Search lazy models + early termination
  - [x] Lazy-load TextCrossEncoder (reranker) with thread-safe singleton
  - [x] Lazy-load spaCy nlp model
  - [x] Lazy-load fastembed TextEmbedding
  - [x] Early-return in execute_vector_search before computing embedding
  - [x] Skip vector search when FTS returns 0 results
  - [x] Verify all existing tests pass

- [x] Ticket P5: Parallel batch upload (deferred)
  - [x] Bounded ThreadPoolExecutor with per-file DB sessions
  - [x] Ordered results preservation
  - [x] Note: Main bottleneck (CPU blocking event loop) already fixed by P2

- [x] Ticket P6: GPU auto-detect with CPU fallback
  - [x] Probe CUDA availability in embedding model loading
  - [x] Probe CUDA availability in reranker model loading
  - [x] Graceful fallback to CPU on any GPU failure
  - [x] Structured logging for GPU status
  - [x] Verify all existing tests pass

- [x] Ticket P7: Gates + docs + review
  - [x] Update docs/task.md with performance tickets
  - [x] Run full test suite to verify no regressions
  - [x] Document performance improvements

## Completed Tickets

- [x] Ticket 01: Missing Unit & Edge-Case Test Coverage
- [x] Ticket 02: Algorithmic & In-Memory Performance Optimization
- [x] Ticket 03: Database Batch Queries & Async Event-Loop Unblocking
- [x] Ticket 04: Security Hardening (FTS Query Sanitization & CORS Restrictions)
- [x] Ticket 05: Code Simplification & Long Function Decomposition
- [x] Ticket 06: PDF Parser OCR Fallback & Final Verification

## Soft Search Filters (Issue #36)

- [x] Extract clean natural language strings from structured title and location filters for FTS, vector search, and AI reranking
- [x] Replace hard SQL YoE exclusion (`WHERE candidates.total_yoe >= :yoe`) with smooth Sigmoid S-curve score penalty (zero penalty for overqualified)
- [x] Add score bonuses in rank fusion for exact candidate `current_title` and `current_city` matches
- [x] Pass clean natural text query to Cross-Encoder reranker
- [x] Update `MatchParameters` and match explanation scorecard with soft penalty / bonus details
- [x] Update test suite and verify all unit and integration search tests pass

## Soft Semantic Job Title Search (Issue #38)

- [x] AST parser: `title:'...'` no longer emits exclusionary `LIKE` SQL; the title value feeds clean text (vector search / reranking) so related titles surface; `title_exact:'...'` emits strict verbatim case-insensitive equality
- [x] Hybrid searcher: soft title requires no strict prefilter (vector pool unrestricted unless exact); strict descriptor + pool restriction only for `title_exact`/location
- [x] RRF: verified +20% verbatim title bonus is applied and reachable (exact matches outrank related matches)
- [x] Scorecard: `title_match` badge (`exact` | `semantic` | `none`) added to `MatchParameters` and rationale output
- [x] API: `exact_title` flag on `SearchQueryRequest`; route builds `title_exact:'...'` DSL when set (incl. job-ad suffix path)
- [x] UI: “Exact Match Only” checkbox next to the Job Title input; enables `exact_title` flag; “Exact Title Match +20%” / “Related Title Match” badges rendered on result cards
- [x] Tests: soft-by-default parser, strict verbatim parser, soft search surfaces related titles with badges, exact mode restricts vector pool, RRF exact-first ordering, API DSL flag; full suite green (235 passed)

## Repo Audit P1 - P5 (Issue #40)

- [x] P1 — Correctness: backup manifest vector count uses `candidate_vectors` table instead of dead `candidate_sections`
- [x] P2 — Robustness: add `Settings.max_upload_size_mb` (default 50 MB, env `CIP_MAX_UPLOAD_SIZE_MB`); reject oversized files with HTTP 413 on `/upload` and FAILED SSE event on `/upload-stream`
- [x] P3 — Settings singleton: add `get_settings()` with `@lru_cache(maxsize=1)` to `config/settings.py`; update all production `Settings()` call sites to `get_settings()`; env file parsed exactly once per process
- [x] P3 — Test isolation: add global `clear_settings_cache` autouse fixture in `conftest.py`; verify cache semantics in `tests/test_settings.py`
- [x] P4 — Centralize location/title SQL: rewrite `_build_strict_filter_clause` in `hybrid_searcher.py` to derive WHERE predicates by iterating `FILTER_SPECS` from `ast_parser.py`
- [x] P5 — Performance: cap FTS keyword result set to `rerank_pool_size` via `execute_fts_query(..., fts_pool_size=...)` in `hybrid_searcher.py` to avoid unbounded in-memory matches
- [x] Full suite green: 261 passed, 6 skipped

## Consolidate Multi-Step LLM Prompts & Ingestion Batching (Issue #42)

- [x] Add prompt templates and builders (`build_consolidated_match_insight_prompt`, `build_batched_extraction_prompt`, `build_json_repair_prompt`) to `src/candidate_intelligence_platform/prompts.py`
- [x] Add snapshot tests in `tests/test_prompts.py`
- [x] Implement 4-stage self-healing JSON recovery in `src/candidate_intelligence_platform/extraction/local_llm_fallback.py`
- [x] Implement bounded 5-resume batching for AI fallback in `src/candidate_intelligence_platform/ingestion/intake.py`
- [x] Update candidate match insight route in `api/routes/candidates.py` to use consolidated prompt with live SSE streaming
- [x] Add and pass unit/integration tests (`tests/test_local_llm_fallback.py`, `tests/test_intake.py`, `tests/test_api_candidates.py`)

