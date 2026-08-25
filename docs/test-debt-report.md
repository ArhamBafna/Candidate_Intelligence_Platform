# Test-Debt Pass — Prioritized Report

Date: 2026-08-25 · Scope: map coverage gaps, add missing high-value tests, find
flaky tests, dedupe, speed the suite up. All changes verified against the full
suite before and after.

## 1. Coverage map (blast radius ranking) — what we added

| Rank | Critical path | Was | Now |
|---|---|---|---|
| 1 | `BackupManager._get_lance_row_count` manifest vector count | Untested (mocked away) — and **wrong**: looked for the dead `candidate_sections` table, so production `vector_count` was always 0 | **Fixed** (`backups/backup_manager.py` now reads `candidate_vectors`) + real LanceDB regression test `test_lance_row_count_uses_candidate_vectors_table` |
| 2 | FastEmbed loading in "mocked" search test | `test_execute_vector_search_missing_table` hit real model each run (2.5s) | Now patches `generate_single_embedding` → instant, still asserts graceful `{}` on missing table |
| 3 | UI build smoke | Test ran a 14.22s `npm run build` subprocess on every suite run, asserting only returncode | Removed `tests/test_ui_build.py` (redundant — UI build correctness is verified by the vite build in CI/dev; violates "fast tests <2s/file" rule). Saves 14s |
| 4 | Real-embedding search path | `test_execute_vector_search_end_to_end` + `test_vector_store_embedding_search` (real FastEmbed, each 0.2–2.8s) | Verified they **are** the intended real-model integration coverage — kept, documented as deliberate |

## 2. Tests added

- `test_lance_row_count_uses_candidate_vectors_table` — regression for the P1
  bug; real LanceDB table with 3 rows → count 3; empty dir → 0 (no crash).

## 3. Tests removed

- `tests/test_ui_build.py` — duplicate of the normal `npm run build` step and
  slow (14s, subprocess). No coverage lost; build step remains in CI.

## 4. Speedup

- Suite: **~41s → ~24–32s** (removed UI-build subprocess + real-model load from
  the "mocked" test). Two remaining real-model tests are intentional
  integration coverage.

## 5. Flaky-test report

- Ran the full suite **3 consecutive times** after the changes (plus the
  `--durations` runs): **235 passed, 6 skipped** every run — **no flakes
  observed**. The three known live-only tests (`test_live_ollama_standalone.py`,
  golden-eval markers) are skipped by default, so the measured suite is
  deterministic.

## 6. Dedup / speed conclusions

- **No duplicate tests to merge** — the suite is lean per-area; the only true
  redundancy was `test_ui_build.py` (removed).
- Candidates for a future human decision (not addressed, per "save info in
  docs" directive): the two real-model tests could be merged into one shared
  fixture to save ~3s, but that changes test isolation semantics, so it's left
  documented instead.

## 7. Where human product decisions are needed (from the audit)

- Add an upload size cap (P2 audit finding) — needs a byte-limit decision.
- `Settings()` caching — behavior change; needs a deliberate go/no-go.

**Result:** run `uv run pytest` → `235 passed, 6 skipped` (~24-32s, was ~40s).