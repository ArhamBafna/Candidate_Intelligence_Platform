# Read-Only Repository Audit — Ranked Findings

Date: 2026-08-25 · Scope: read-only pass across six reviewer areas (security,
correctness, regressions, architecture, performance, test coverage). No code was
changed during this pass. Each finding below was **verified against the actual
source** before inclusion; anything not reproducible was dropped.

**Legend**: `[severity]` P1 = broken behavior, P2 = likely bug / robustness,
P3 = smell / improvement.

---

## P1 — Correctness: backup manifest vector count is always 0 (dead table name)

- **File**: `backups/backup_manager.py:30` — `_get_lance_row_count()` checks
  `"candidate_sections" in db.table_names()`.
- **Evidence:** production code creates/opens only `candidate_vectors`:
  `api/services/candidate_service.py:84` (`create_table("candidate_vectors", …)`)
  and `search/hybrid_searcher.py:123` (`open_table("candidate_vectors")`).
  `candidate_sections` exists only in the legacy test `tests/test_vector_store.py:13`.
- **Effect:** `generate_manifest()["vector_count"]` is silently always `0` when
  the real LanceDB connection is used; backup manifests understate the store.
- **Smallest fix:** rename the check to `"candidate_vectors"` (one string) + a
  test that builds a real LanceDB table and asserts the count (the current test
  mocks `_get_lance_row_count` away, which is why this shipped).

## P2. Unbounded in-memory uploads (robustness / DoS-by-file)

- **File:** `api/routes/candidates.py:356` (`upload_resume`: `await file.read()`)
  and the `upload-stream` path (`api/routes/candidates.py:480-495`) which reads
  whole files per task (bounded concurrency = 4, but each read unbounded).
- **Evidence:** no `MAX_` size constant or content-length check anywhere in the
  router; every byte lands in RAM before hashing/`ingest_file`.
- **Risk:** local tool, low exposure, but one multi-GB file OOMs the process
  (DB/vector corruption risk mid-write).
- **Smallest fix (product decision):** cap `len(content)` (e.g. 25 MB) with a
  413 before `ingest_file`, or stream the hash + parse from disk.
- **Status:** documented only — needs product decision on the cap value.

## P3. `Settings()` re-parses the env file on every call

- **Files:** `config/settings.py` (env_file-based `BaseSettings`);
  `api/dependencies.py:17` (`get_settings()` returns a fresh `Settings()`),
  `hybrid_searcher.py` (`Settings()` inside `execute_vector_search` and again in
  `search_candidates`).
- **Effect:** per search request the `.env` file is re-read and re-parsed at
  least 3 times. Negligible for a single user, measurable on the hot path.
- **Fix:** `@lru_cache` on a `get_settings()` singleton (tests already
  override via env vars; dependency-override tests keep working).
- **Status:** documented only — caching changes global behavior; deliberate move.

## P4. Architecture: location SQL is duplicated in two places (drift risk)

- **Files:** `src/.../search/ast_parser.py:15` (location fragment inside
  `FILTER_SPECS`) and `src/.../search/hybrid_searcher.py:_build_strict_filter_clause`
  (byte-identical location fragment re-inlined).
- **Effect:** a location-filter change can be applied to one copy only and go
  unnoticed forever (this class of bug already bit the title filter in #38 —
  the strict-title copy was in the searcher while the parser shipped a different
  semantics).
- **Fix:** expose the SQL fragment from `FILTER_SPECS` (e.g. a small helper)
  and have the searcher reuse it; add a parser↔searcher consistency assertion.
- **Status:** documented only (refactor, low risk, but touches the search core).

## P5. Performance: FTS query is unbounded

- **File:** `src/.../search/hybrid_searcher.py` `execute_fts_query()` collects
  **all** FTS rows + bm25 ordering, then `_hydrate_candidates` re-fetches.
  The vector store is pool-limited (`CIP_VECTOR_POOL_SIZE`, default 100) but the
  keyword path is not.
- **Effect:** on a large corpus the FTS step grows linearly with corpus size;
  latency target (<100 ms) degrades accordingly.
- **Fix:** `LIMIT` the FTS select to `rerank_pool_size` (with bm25 order it is
  safe to truncate — lower-ranked rows rarely survive fusion).

## Security (passed, notes)

- **No secrets tracked.** `git ls-files` match for `.env`/key/cert/token files:
  zero. `.env` is gitignored (root `.gitignore`).
- **CORS** locked to `localhost:5173`/`127.0.0.1:5173` with explicit method list;
  local-first, no auth layer (by design — documented, not a defect).
- **FTS injection** mitigated: parser strips FTS5-illegal chars + unbalanced
  quotes; all SQL uses bound params (`:title`, `:location`, `:yoe`).
- **CAS path safety:** file paths are constructed from SHA-256 hashes + DB
  `file_type` (no user string in the path); `CASManager.delete` clears the
 0444 read-only bit before unlink (Windows-safe).
- `FileResponse(filename=rv.original_filename)` — a crafted filename with `\`/`"`
  could distort `Content-Disposition`; ingest-derived, negligible exposure.
- **No unsafe deserialization:** no `pickle`, `eval`, `yaml.load`, shell calls in
  `src/`, `api/`, `storage/`, `config/`. Only `tests/test_ui_build.py` uses
  `subprocess...shell=True` with a constant `npm run build` command (no user input).

## Regression pass (post-#38)

- All changed search behavior is covered: parser soft/exact, searcher strict
  pool, RRF bonus, badge labels, API flag; full suite green at commit time
  (235 passed). No regressions observed in this read-only re-check.

## Test coverage gaps (mapped for the test-debt pass, Prompt 3)

- `backups/backup_manager._get_lance_row_count()` — untested (mocked away),
  and it is the P1 bug above.
- `api/routes/candidates.py` — upload size-guard, PATCH normalize flows have
  partial coverage; `dependencies.get_settings` caching not covered (behavior
  only, not contract).
- 43 test files; worst gaps = backup-manifest vector count + hot-path settings
  caching, neither of which is "smoke-only".