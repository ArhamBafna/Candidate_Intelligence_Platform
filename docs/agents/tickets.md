# Tickets: CIP Fixes & Refactoring Plan

Tracer-bullet implementation tickets generated from the approved implementation plan.

---

## Ticket 01: Missing Unit & Edge-Case Test Coverage

**What to build:**
Comprehensive unit tests covering all identified blind spots across logging, search AST, vector search, LLM fallback parsing, and database engine connection events.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] Test `get_recent_logs(limit=N)` verifies truncation when buffer has more items than limit (`config/logging.py:15`).
- [ ] Test `memory_buffer_processor` verifies log entries are prepended with buffer lock acquired (`config/logging.py:10`).
- [ ] Test `extract_inferences` mocks `ollama.chat` to return malformed JSON / throw exception, asserting empty list returned and warning emitted (`local_llm_fallback.py:42`).
- [ ] Test `parse_query_to_sql` handles free-text queries without `location:` or `yoe >=` filters (`ast_parser.py:3`).
- [ ] Test `fetch_candidate_documents` short-circuits to empty list when `candidate_ids` is empty (`hybrid_searcher.py:72`).
- [ ] Test database engine connect event ignores non-sqlite DBAPI connections without executing PRAGMAs (`config/database.py:12`).
- [ ] Test `execute_vector_search` handles missing `candidate_vectors` table gracefully by recording warning and returning empty dict (`hybrid_searcher.py:37`).
- [ ] `uv run pytest tests/` passes with all new tests green.

---

## Ticket 02: Algorithmic & In-Memory Performance Optimization

**What to build:**
Eliminate repeated O(N) linear scans, repeated regex compilations, and repeated ONNX embedding calculations by introducing caching, sets, pre-compiled patterns, and dict lookups.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] Add `@functools.lru_cache(maxsize=1024)` to single-query embedding generation in `embeddings.py:6`.
- [ ] Convert `candidate_ids` to `set` in `execute_vector_search` in `hybrid_searcher.py:64` for O(1) membership checks.
- [ ] Precompile `KNOWN_SKILLS` regular expressions at module level in `deterministic_ner.py:47`.
- [ ] Convert `rrf_results` into dictionary lookup in `search_candidates` in `hybrid_searcher.py:137`.
- [ ] Use `collections.defaultdict(float)` in `reciprocal_rank_fusion` in `rank_fusion.py:8`.
- [ ] `uv run pytest tests/` passes.

---

## Ticket 03: Database Batch Queries & Async Event-Loop Unblocking

**What to build:**
Resolve N+1 database queries in search endpoints using bulk `in_()` queries, and prevent blocking the asyncio event loop during upload and reprocess streaming by delegating blocking operations to threadpools.

**Blocked by:** Ticket 02.

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] `/search` endpoint in `api/routes/search.py:47` fetches candidate details in a single bulk query using `Candidate.id.in_(top_ids)`.
- [ ] `/search/stream` endpoint in `api/routes/search.py:138` uses bulk candidate retrieval.
- [ ] `stream_upload_generator` in `api/routes/candidates.py:517` runs file hashing and DB queries via `asyncio.to_thread`.
- [ ] `batch_stream_generator` in `api/routes/candidates.py:705` runs DB queries via `asyncio.to_thread`.
- [ ] Confirm `candidate_id` is set on vector chunks in `api/routes/candidates.py:612`.
- [ ] `uv run pytest tests/` passes.

---

## Ticket 04: Security Hardening (FTS Query Sanitization & CORS Restrictions)

**What to build:**
Sanitize user-provided search terms against FTS5 special character syntax injection and restrict CORS methods while preserving allowable headers.

**Blocked by:** Ticket 01.

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] `parse_query_to_sql` in `ast_parser.py:35` strips or escapes unbalanced quotes and illegal FTS5 operators before building match clause.
- [ ] CORS middleware in `api/main.py:44` sets `allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]` and `allow_headers=["*"]`.
- [ ] `uv run pytest tests/` passes.

---

## Ticket 05: Code Simplification & Long Function Decomposition

**What to build:**
Decompose monolithic functions (>100 lines) into small, readable units and replace excessive parameter lists with typed data structures.

**Blocked by:** Ticket 02, Ticket 03.

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] Refactor `build_match_rationale` in `explainer.py:3` to accept a structured dataclass or Pydantic model (`MatchParameters`) and update callers in `hybrid_searcher.py`.
- [ ] Split `extract_candidate_profile_hybrid` in `hybrid_extractor.py:44` into discrete helper functions (deterministic extraction, LLM fallback, score consolidation).
- [ ] Split `perform_search_stream` in `api/routes/search.py:90` into cohesive modular pipeline steps.
- [ ] `uv run pytest tests/` passes without breaking existing API contracts.

---

## Ticket 06: PDF Parser OCR Fallback & Final Verification

**What to build:**
Integrate Tesseract OCR as a fallback text extraction mechanism for image-only or scanned PDFs when PyMuPDF and pdfplumber return insufficient text, followed by full repository verification.

**Blocked by:** Ticket 01, Ticket 04, Ticket 05.

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] Add `pytesseract` fallback in `ingestion/parsers/pdf_parser.py:44` when extracted text length is below threshold.
- [ ] Add unit test verifying OCR fallback execution with a mocked image page.
- [ ] Run full test suite: `uv run pytest`.
- [ ] Run `/code-review` across all changed files.
