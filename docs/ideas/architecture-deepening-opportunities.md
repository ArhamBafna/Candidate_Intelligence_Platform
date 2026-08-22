# Architecture Deepening Opportunities

5 problems found in the Candidate Intelligence Platform codebase, ordered by leverage. Branch `refactor/deepen-modules` exists for changes.

---

## 1. Resume intake pipeline copied 4 times — and the copies disagree

When a resume arrives (via website upload, batch upload, reprocess, or the bulk-import script), the app does the same ~8 steps: save file → check for duplicates → read text → check it's really a resume → pull out name/email/phone → merge with existing people → store in database → make it searchable. That recipe is copy-pasted in four places with no shared module:

| Entry point | What it does |
|---|---|
| **Single upload** (`api/routes/candidates.py`, line 334) | CAS dedup → parse → extract → persist → FTS via CandidateService → vectors via CandidateService → timeline. No resume classification. No entity merging. |
| **Bulk upload** (`api/routes/candidates.py`, line 443) | Same pipeline but inlines FTS INSERT as raw SQL (different from CandidateService's copy). Still no classification or merging. |
| **Reprocess** (`api/routes/candidates.py`, lines 161, 221, 659) — three nearly identical variants: sync, SSE-stream, batch-SSE | Extract → apply fields to Candidate → FTS → vectors → timeline. Re-implements the extract→assess→branch logic from hybrid_extractor. Threshold 0.40 hardcoded in all three. |
| **Bulk import script** (`scripts/bulk_ingest.py`, line 213) | CAS dedup → parse → **classify** (skips contracts, visas, study guides) → extract → **entity merge** (finds existing Candidate by email/phone/name, merges instead of creating duplicate) → persist → FTS → vectors. Skips timeline via TimelineLedger (uses ORM directly). |

The divergence is real: uploading the same person's resume twice through the website creates two separate Candidate entries. Uploading through the bulk script correctly merges them. Fix: write the recipe once in a deep ingestion module, have all 4 entry points use it.

**Strength:** Strong | **Category:** in-process

**Key file paths:**
- `api/routes/candidates.py` — where upload, upload-stream, reprocess, reprocess-stream, batch-reprocess-stream are defined (843 lines total)
- `scripts/bulk_ingest.py` — standalone CLI for bulk import (726 lines)
- `api/services/candidate_service.py` — thin helper with 3 static methods (79 lines)
- `ingestion/entity_resolution.py` — the merge logic (only called from bulk_ingest.py, never from routes)
- `ingestion/chunker.py` — document chunking for vector indexing

**What goes wrong without this fix:**
- Duplicate Candidate entries for the same person when uploaded through the website
- FTS INSERT SQL copy-pasted 3 times (different syntax in upload-stream vs CandidateService)
- Threshold 0.40 hardcoded in 5 places vs module default 0.70
- `assess_tier1` runs twice per document in streaming paths (once for progress message, once inside extract)
- SSE event plumbing (asyncio.Queue + closer + stream generator) copy-pasted 3 times

---

## 2. Search has a weird round-trip that loses information

Your search page collects structured filters (city, years of experience, job title), converts them into a text string like `location:'New York' AND yoe >= 5 AND title:'Engineer'`, then another module (`ast_parser.py`) uses regex to parse that string back into structured SQL. This string seam causes two bugs:

1. **Job title filter silently stops working.** The route builds `title:'Engineer'` into the DSL string, but `parse_query_to_sql` has no title branch — the title filter silently falls through into free-text matching where quotes get stripped. The filter degrades without any error.

2. **City/title with special characters breaks the parse.** A city like `O'Brien` would break the regex `location:'([^']+)'`. Same bug class as the FTS special-character fix (commit 343a426) but still open on the filter path.

Additionally, `/search` and `/search/stream` duplicate the hydrate/format logic line-for-line. The stream endpoint also hardcodes knowledge of the searcher's internal generator protocol (checking for `stage == "COMPLETE"`).

Fix: pass a structured search request across the seam once; the searcher returns results + warnings; both endpoints become thin adapters.

**Strength:** Strong | **Category:** in-process

**Key file paths:**
- `api/routes/search.py` — builds the DSL string (line 14–24), calls `search_candidates`, hydrates/format results (lines 62–140). Two nearly identical endpoints.
- `src/candidate_intelligence_platform/search/hybrid_searcher.py` — `search_candidates` function: parses query, runs FTS, runs vector search, fuses results, reranks, explains (lines 86–138)
- `src/candidate_intelligence_platform/search/ast_parser.py` — regex-parses DSL string back into SQL (lines 5–56). Also hand-builds raw SQL with hardcoded table/column names.
- `src/candidate_intelligence_platform/search/reranker.py` — lazy-loads cross-encoder model, returns bare `list[float]` that caller must re-zip with ids
- `src/candidate_intelligence_platform/search/rank_fusion.py` — reciprocal rank fusion (small, genuinely deep module)
- `src/candidate_intelligence_platform/intelligence/explainer.py` — `MatchParameters` has 8 fields but production only sets 4; the other 4 are always empty in API responses

**What goes wrong without this fix:**
- Users searching for "Engineer" in title get results that just have "Engineer" as a keyword anywhere, not a title match
- `O'Brien` in city field causes a parse error
- Every new search feature must be written twice (stream + non-stream)
- Tests monkeypatch 7 module globals to test the searcher (no injection seam)

---

## 3. Database housekeeping knowledge scattered across 7+ files

The details of how resumes get indexed for searching — table names, column names, record shapes, AI model names — are written out by hand in many different files with no single owner. Every time you change a table name, add a column, or switch embedding models, you must find and update all of them.

Concrete examples of duplication:

| Detail | Appears in |
|---|---|
| `"candidate_vectors"` table literal | `candidate_service.py` (3 places), `candidates.py` (2 places), `bulk_ingest.py`, `hybrid_searcher.py` |
| FTS INSERT SQL with 5 columns | `candidate_service.py:47`, `candidates.py:569` (raw SQL, different from service), `bulk_ingest.py:441` (another raw SQL copy) |
| FTS DELETE SQL | `candidate_service.py:17` |
| FTS table columns (candidate_id, full_name, current_title, current_company, resume_content) | `db_models.py:98`, `conftest.py:83` (copy-pasted DDL) |
| `BAAI/bge-small-en-v1.5` embedding model | `embeddings.py:51,56,61` (hardcoded 3×, ignores `settings.embedding_model` which is dead config) |
| `Xenova/ms-marco-MiniLM-L-6-v2` reranker model | `reranker.py:50,55,60` (hardcoded 3×, not in settings at all) |
| CAS shard path (`root / hash[:2] / hash[2:4] / hash+ext`) | `cas.py:21` and `candidates.py:147` (rebuilt by hand) |

Fix: one index writer module owns table names, record shapes, and model wiring. Two adapters justify the seam: real SQLite/LanceDB in production, in-memory fake in tests.

**Strength:** Worth exploring | **Category:** ports & adapters

**Key file paths:**
- `api/services/candidate_service.py` — 3 static methods doing FTS write, vector write, cascade delete
- `api/routes/candidates.py` — inline FTS/vector logic in upload-stream (lines 420–438, 569–581)
- `scripts/bulk_ingest.py` — inline FTS/vector logic (lines 439–493)
- `src/candidate_intelligence_platform/search/hybrid_searcher.py` — reads from `"candidate_vectors"` table (line 43)
- `storage/vector_store.py` — defines `CandidateSectionVector` schema but not the table name
- `src/candidate_intelligence_platform/intelligence/embeddings.py` — hardcoded model name ignores settings
- `src/candidate_intelligence_platform/search/reranker.py` — hardcoded model name, no settings
- `config/settings.py` — has `embedding_model` setting but it's never read

**What goes wrong without this fix:**
- Changing a table name requires grep-and-replace across 7+ files
- `settings.embedding_model` is dead code; switching models requires editing Python files
- Tests must monkeypatch private module globals (`_get_reranker`, `_get_embedding_model`) instead of using a clean fake
- `bulk_ingest.py:478` bypasses `CandidateSectionVector.create_record` and hand-builds the record dict — if the schema changes, this one breaks silently

---

## 4. Name/email extractor exports its internals and has no test seam

The hybrid extraction module (`hybrid_extractor.py`) is the "brain" that pulls names, emails, phones, and job titles from resume text. It has one natural front door (`extract_candidate_profile_hybrid`) but exports 8 callables plus private helpers that other modules import:

| Exported function | Used outside? | Purpose |
|---|---|---|
| `extract_candidate_profile_hybrid` | Yes — routes, bulk_ingest | Main entry: orchestrate Tier-1 (deterministic NER) → Tier-2 (local LLM) |
| `assess_tier1` | Yes — routes (3 copies) | Decide if Tier-1 is confident enough or needs AI |
| `calculate_tier1_confidence` | Imported by routes but never called there | Dead import |
| `normalize_name` | Yes — routes for manual edits | Title-case a name |
| `normalize_title` | Yes — routes for manual edits | Title-case a job title |
| `is_noise_header_line` | No — only internal | Detect noisy resume headers |
| `_extract_deterministic_profile` | Yes — routes import it (dead import) | Private helper, should not cross the boundary |
| `EMAIL_REGEX`, `PHONE_REGEX` constants | Yes — imported by `deterministic_ner.py` | Regex patterns leak across module seam |

The routes re-implement the Tier-1 → Tier-2 branching three times (lines 248–265, 509–525, 705–719 in `candidates.py`) with this pattern: `extract_facts(raw_text)` → `assess_tier1(raw_text, facts, threshold=0.40)` → decide AI-vs-NER → `extract_candidate_profile_hybrid(raw_text, threshold=0.40, facts=facts)`. The threshold 0.40 is hardcoded in 5 places vs the module default of 0.70.

Also: `deterministic_ner.py:5` loads spaCy at import time (`nlp = spacy.load("en_core_web_sm")`). Any test importing `hybrid_extractor` (which imports `deterministic_ner`) triggers this load. There's no seam to inject a fake NER model, which is why `tests/test_hybrid_extractor.py` exercises real spaCy unmocked — violating the repo's own rule about mocking heavy ML models.

Fix: one `extract_profile(raw_text) → ExtractionOutcome` interface absorbing facts, assessment, and LLM fallback; model loading moves behind an injectable loader; routes emit SSE stages from the outcome.

**Strength:** Worth exploring | **Category:** local-substitutable

**Key file paths:**
- `src/candidate_intelligence_platform/extraction/hybrid_extractor.py` — 8 exported callables, 277 lines total
- `src/candidate_intelligence_platform/extraction/deterministic_ner.py` — spaCy NER at import time (line 5), `extract_facts` is the real entry point
- `src/candidate_intelligence_platform/extraction/local_llm_fallback.py` — Ollama inference with prompt construction (164 lines, genuinely deep)
- `api/routes/candidates.py` — three re-implementations of the assess→branch→extract pattern
- `tests/test_hybrid_extractor.py` — exercises real spaCy NER unmocked (lines 50–116)

**What goes wrong without this fix:**
- Route imports `_extract_deterministic_profile` (private, dead) — one wrong change there breaks a caller that shouldn't exist
- `assess_tier1` runs twice per document in streaming paths
- Every new entry point (upload, reprocess, batch) must re-implement the branching logic
- Tests load spaCy every run, violating the repo rule about mocking heavy ML models
- Switching NER models requires changing imports in multiple files

---

## 5. CandidateService — shallow helper that would dissolve into the deepened modules

`api/services/candidate_service.py` has 3 static methods on a stateless class: `delete_candidate` (cascade delete + FTS delete + vector delete), `update_fts_index` (raw SQL DELETE + INSERT), `update_vector_index` (vector delete + chunk + embed + store). It is shallower than its callers:

- **Commits:** it never commits; every caller commits around it (a deliberate choice per `docs/task.md` ticket P3). But this leaks commit policy outward.
- **Bypassed:** the newest upload paths (`upload-stream` line 569, `upload` line 420) inline the FTS/vector logic instead of calling it.
- **Error handling:** bare `except: pass` on lines 19–20 and 40–41 — failures are silently swallowed.
- **Internal duplication:** the LanceDB delete fallback (try `delete_candidate_vectors`, fall back to `open_table` + string filter) appears twice within the same file (lines 32–41 and 61–67).

Fix: its responsibilities dissolve into the deepened modules — index writing goes behind the index-writer seam (candidate 3), removal becomes one deep operation owning cascade + indexes + commit policy. Low priority — only makes sense after candidates 1 and 3 land.

**Strength:** Speculative | **Category:** in-process

**Key file paths:**
- `api/services/candidate_service.py` — 79 lines, 3 static methods
- `api/routes/candidates.py` — all 9 call sites (lines 64, 194, 202, 286, 300, 421, 645, 736, 747)

---

## Recommendation

Start with **#1** — biggest payoff (4 call sites), hottest area (bulk ingest is the most recent work), passes the deletion test (deleting the route-level copies concentrates complexity into one module), and creates the seam that #3 and #4 sit behind. Do it first and the rest get cheaper.

Note: unifying the divergent copies (#1) changes behavior — the UI upload would gain classification and entity merging. This is probably the right thing, but your "functionality must not change" constraint makes it a decision point, not a given. Worth confirming during grilling.
