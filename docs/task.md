# Task Tracker

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

- [ ] Ticket P5: Parallel batch upload (deferred)
  - [ ] Bounded ThreadPoolExecutor with per-file DB sessions
  - [ ] Ordered results preservation
  - [ ] Note: Main bottleneck (CPU blocking event loop) already fixed by P2

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
