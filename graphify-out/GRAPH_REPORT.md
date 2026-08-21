# Graph Report - Candidate_Intelligence_Platform  (2026-08-20)

## Corpus Check
- 103 files · ~38,828 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 590 nodes · 1071 edges · 50 communities (39 shown, 11 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 124 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dd7b364a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Settings
- routes/candidates.py
- extract_candidate_profile_hybrid
- resolve
- devDependencies
- hybrid_searcher.py
- ParsedDocument
- Candidate
- Advanced Optimization
- extract_inferences
- App.jsx
- BackupManager
- Optimization Patterns
- main.py
- chunk_document
- routes/search.py
- Issue tracker: GitHub
- Resume Ingestion Pipeline
- runner.js
- test_api_main.py
- test_api_upload_stream.py
- Architecture Design Document (ADD)
- test_get_logs_endpoint_returns_recent_events
- test_search_emits_wide_event
- test_ui_build
- backups/__init__.py
- crm/__init__.py
- Domain Docs
- Python Performance Optimization Skill
- Autonomous Agentic Retrieval System
- End-to-End UI Test Report
- candidate-intelligence-platform
- React + Vite
- Recruiter UI

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 38 edges
2. `ParsedDocument` - 26 edges
3. `Settings` - 20 edges
4. `TimelineLedger` - 19 edges
5. `resolve()` - 19 edges
6. `ResumeVersion` - 19 edges
7. `upload_resume()` - 17 edges
8. `CandidateService` - 16 edges
9. `chunk_document()` - 16 edges
10. `extract_candidate_profile_hybrid()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `Hero Image` --conceptually_related_to--> `Architecture Design Document (ADD)`  [INFERRED]
  ui/src/assets/hero.png → docs/architecture_design_document.md
- `lifespan()` --uses--> `Settings`  [INFERRED]
  api/main.py → config/settings.py
- `list_candidates()` --uses--> `Candidate`  [INFERRED]
  api/routes/candidates.py → storage/db_models.py
- `get_candidate()` --uses--> `Candidate`  [INFERRED]
  api/routes/candidates.py → storage/db_models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **CIP Core Processing Flow** — docs_how_candidate_intelligence_works_ingestion, docs_how_candidate_intelligence_works_hybrid_search, docs_ollama_setup_windows_llama [EXTRACTED 0.95]

## Communities (50 total, 11 thin omitted)

### Community 1 - "Settings"
Cohesion: 0.09
Nodes (26): get_db(), _get_sessionmaker(), get_settings(), get_vector_db(), Session, BaseSettings, Settings, client() (+18 more)

### Community 2 - "routes/candidates.py"
Cohesion: 0.07
Nodes (46): batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_timeline(), list_candidates(), get (+38 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.11
Nodes (28): skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), calculate_tier1_confidence(), extract_candidate_profile_hybrid(), _extract_deterministic_profile(), is_noise_header_line() (+20 more)

### Community 4 - "resolve"
Cohesion: 0.10
Nodes (27): Enum, CandidateIdentifiers, _normalize(), ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (37): autoprefixer, lucide-react, oxlint, postcss, react, react-dom, react-router-dom, @tailwindcss/postcss (+29 more)

### Community 6 - "hybrid_searcher.py"
Cohesion: 0.10
Nodes (27): generate_embeddings(), generate_single_embedding(), Generate dense vector embeddings for a list of texts using fastembed. Returns…, build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently… (+19 more)

### Community 7 - "ParsedDocument"
Cohesion: 0.07
Nodes (44): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, _decode_header(), parse_email(), _parse_eml(), _parse_msg() (+36 more)

### Community 8 - "Candidate"
Cohesion: 0.09
Nodes (47): Base, CandidateStateMachine, InvalidStateTransition, Transitions the candidate to a new status and logs the event., TransitionContext, Any, Session, Logs a new event in the candidate's timeline. (+39 more)

### Community 9 - "Advanced Optimization"
Cohesion: 0.11
Nodes (17): Advanced Optimization, Benchmarking Tools, Custom Benchmark Decorator, Database Optimization, Memory Optimization, Pattern 11: NumPy for Numerical Operations, Pattern 12: Caching with functools.lru_cache, Pattern 13: Using __slots__ for Memory (+9 more)

### Community 10 - "extract_inferences"
Cohesion: 0.16
Nodes (12): ollama, extract_inferences(), Extract AI inferences from text using a local LLM via Ollama. Defaults to…, Test when LLM returns null claim_value and entity in claim_key., test_llm_claim_value_null_logs_warning_and_repairs(), test_llm_extraction_failure_logs_ai_warning(), test_vector_search_failure_logs_ai_warning(), Live integration test against running Ollama instance. (+4 more)

### Community 11 - "App.jsx"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 12 - "BackupManager"
Cohesion: 0.18
Nodes (10): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, test_cas_storage_sync() (+2 more)

### Community 13 - "Optimization Patterns"
Cohesion: 0.14
Nodes (13): Optimization Patterns, Pattern 10: Function Call Overhead, Pattern 1: cProfile - CPU Profiling, Pattern 2: line_profiler - Line-by-Line Profiling, Pattern 3: memory_profiler - Memory Usage, Pattern 4: py-spy - Production Profiling, Pattern 5: List Comprehensions vs Loops, Pattern 6: Generator Expressions for Memory (+5 more)

### Community 14 - "main.py"
Cohesion: 0.08
Nodes (31): health_check(), lifespan(), get, structlog_middleware(), fetch_system_logs(), get, get_engine(), Engine (+23 more)

### Community 15 - "chunk_document"
Cohesion: 0.16
Nodes (21): chunk_document(), Section-aware text chunker with context injection. Public interface:…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, TextChunk, _make_doc(), Tests for ingestion/chunker.py Seam under test: chunk_document( doc:…, An empty document must yield an empty list (no ghost chunks). (+13 more)

### Community 16 - "routes/search.py"
Cohesion: 0.37
Nodes (11): _build_search_query(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), post, Session, BaseModel (+3 more)

### Community 17 - "Issue tracker: GitHub"
Cohesion: 0.29
Nodes (6): Conventions, Issue tracker: GitHub, Pull requests as a triage surface, Wayfinding operations, When a skill says "fetch the relevant ticket", When a skill says "publish to the issue tracker"

### Community 18 - "Resume Ingestion Pipeline"
Cohesion: 0.40
Nodes (5): uv Package Manager, Hybrid Search Architecture, Resume Ingestion Pipeline, Ollama LLM Integration, Playwright Installation Blocker

### Community 20 - "runner.js"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 21 - "test_api_main.py"
Cohesion: 0.60
Nodes (4): TestClient, test_404_handler(), test_cors_headers(), test_health_check()

### Community 22 - "test_api_upload_stream.py"
Cohesion: 0.60
Nodes (4): TestClient, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume(), test_upload_stream_transparency_events()

### Community 31 - "Domain Docs"
Cohesion: 0.33
Nodes (5): Before exploring, read these, Domain Docs, File structure, Flag ADR conflicts, Use the glossary's vocabulary

### Community 45 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

## Knowledge Gaps
- **69 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `oxc` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `upload_resume()` connect `routes/candidates.py` to `Settings`, `extract_candidate_profile_hybrid`, `hybrid_searcher.py`, `ParsedDocument`, `Candidate`, `chunk_document`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `ParsedDocument` connect `ParsedDocument` to `Candidate`, `routes/candidates.py`, `chunk_document`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Candidate` to `routes/search.py`, `routes/candidates.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Candidate` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate()`) actually correct?**
  _`Candidate` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ParsedDocument` (e.g. with `upload_resume()` and `upload_stream_resumes()`) actually correct?**
  _`ParsedDocument` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `Settings` (e.g. with `lifespan()` and `batch_reprocess_candidate_stream()`) actually correct?**
  _`Settings` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `TimelineLedger` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_timeline()`) actually correct?**
  _`TimelineLedger` has 9 INFERRED edges - model-reasoned connections that need verification._