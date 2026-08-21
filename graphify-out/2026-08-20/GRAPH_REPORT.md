# Graph Report - Candidate_Intelligence_Platform  (2026-08-20)

## Corpus Check
- 103 files · ~37,484 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 602 nodes · 1103 edges · 52 communities (40 shown, 12 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 116 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e65005cd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CandidateSectionVector
- Settings
- routes/candidates.py
- extract_candidate_profile_hybrid
- resolve
- devDependencies
- hybrid_searcher.py
- ParsedDocument
- parse_pdf
- Advanced Optimization
- parse_docx
- App.jsx
- BackupManager
- Optimization Patterns
- test_logging.py
- schemas/candidates.py
- MockVectorStore
- Issue tracker: GitHub
- Resume Ingestion Pipeline
- test_api_search_stream.py
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
3. `TimelineLedger` - 19 edges
4. `resolve()` - 19 edges
5. `ResumeVersion` - 19 edges
6. `Settings` - 18 edges
7. `upload_resume()` - 17 edges
8. `CandidateService` - 16 edges
9. `chunk_document()` - 16 edges
10. `_make()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `Hero Image` --conceptually_related_to--> `Architecture Design Document (ADD)`  [INFERRED]
  ui/src/assets/hero.png → docs/architecture_design_document.md
- `update_candidate()` --calls--> `normalize_name()`  [INFERRED]
  api/routes/candidates.py → src/candidate_intelligence_platform/extraction/hybrid_extractor.py
- `update_candidate()` --calls--> `normalize_title()`  [INFERRED]
  api/routes/candidates.py → src/candidate_intelligence_platform/extraction/hybrid_extractor.py
- `get_candidate_file()` --uses--> `Settings`  [INFERRED]
  api/routes/candidates.py → config/settings.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **CIP Core Processing Flow** — docs_how_candidate_intelligence_works_ingestion, docs_how_candidate_intelligence_works_hybrid_search, docs_ollama_setup_windows_llama [EXTRACTED 0.95]

## Communities (52 total, 12 thin omitted)

### Community 0 - "CandidateSectionVector"
Cohesion: 0.15
Nodes (15): DBConnection, LanceModel, CandidateSectionVector, get_lancedb_connection(), Helper to create a vector dictionary record from a chunk and embedding., Connect to the embedded LanceDB instance at the specified path., patch, Session (+7 more)

### Community 1 - "Settings"
Cohesion: 0.06
Nodes (53): get_db(), _get_sessionmaker(), get_settings(), get_vector_db(), Session, health_check(), lifespan(), get (+45 more)

### Community 2 - "routes/candidates.py"
Cohesion: 0.07
Nodes (69): batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_timeline(), list_candidates(), get (+61 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.08
Nodes (37): skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), calculate_tier1_confidence(), extract_candidate_profile_hybrid(), _extract_deterministic_profile(), normalize_name() (+29 more)

### Community 4 - "resolve"
Cohesion: 0.10
Nodes (27): Enum, CandidateIdentifiers, _normalize(), ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (37): autoprefixer, lucide-react, oxlint, postcss, react, react-dom, react-router-dom, @tailwindcss/postcss (+29 more)

### Community 6 - "hybrid_searcher.py"
Cohesion: 0.10
Nodes (25): generate_embeddings(), generate_single_embedding(), Generate dense vector embeddings for a list of texts using fastembed. Returns…, build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently… (+17 more)

### Community 7 - "ParsedDocument"
Cohesion: 0.07
Nodes (47): chunk_document(), Section-aware text chunker with context injection. Public interface:…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, TextChunk, _decode_header(), parse_email(), _parse_eml() (+39 more)

### Community 8 - "parse_pdf"
Cohesion: 0.16
Nodes (20): _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when…, _make_minimal_pdf(), Path (+12 more)

### Community 9 - "Advanced Optimization"
Cohesion: 0.11
Nodes (17): Advanced Optimization, Benchmarking Tools, Custom Benchmark Decorator, Database Optimization, Memory Optimization, Pattern 11: NumPy for Numerical Operations, Pattern 12: Caching with functools.lru_cache, Pattern 13: Using __slots__ for Memory (+9 more)

### Community 10 - "parse_docx"
Cohesion: 0.18
Nodes (18): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, _make_docx(), Path, Tests for ingestion/parsers/docx_parser.py Seam under test: parse_docx(path:…, Write a .docx file with the given paragraphs (and optional table). (+10 more)

### Community 11 - "App.jsx"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 12 - "BackupManager"
Cohesion: 0.18
Nodes (10): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, test_cas_storage_sync() (+2 more)

### Community 13 - "Optimization Patterns"
Cohesion: 0.14
Nodes (13): Optimization Patterns, Pattern 10: Function Call Overhead, Pattern 1: cProfile - CPU Profiling, Pattern 2: line_profiler - Line-by-Line Profiling, Pattern 3: memory_profiler - Memory Usage, Pattern 4: py-spy - Production Profiling, Pattern 5: List Comprehensions vs Loops, Pattern 6: Generator Expressions for Memory (+5 more)

### Community 14 - "test_logging.py"
Cohesion: 0.35
Nodes (8): fetch_system_logs(), get, get_recent_logs(), memory_buffer_processor(), setup_logging(), test_get_recent_logs_truncation(), test_memory_buffer_processor(), test_setup_logging_configures_structlog()

### Community 15 - "schemas/candidates.py"
Cohesion: 0.36
Nodes (9): BatchCandidateIds, BatchReprocessRequest, CandidateBase, CandidateCreate, CandidateResponse, CandidateStatusUpdate, CandidateUpdate, BaseModel (+1 more)

### Community 17 - "Issue tracker: GitHub"
Cohesion: 0.29
Nodes (6): Conventions, Issue tracker: GitHub, Pull requests as a triage surface, Wayfinding operations, When a skill says "fetch the relevant ticket", When a skill says "publish to the issue tracker"

### Community 18 - "Resume Ingestion Pipeline"
Cohesion: 0.40
Nodes (5): uv Package Manager, Hybrid Search Architecture, Resume Ingestion Pipeline, Ollama LLM Integration, Playwright Installation Blocker

### Community 19 - "test_api_search_stream.py"
Cohesion: 0.40
Nodes (5): TestClient, Test that the search stream yields the expected stage events., Test that the POST /search/stream endpoint exists and accepts valid requests., test_search_stream_emits_progress_events(), test_search_stream_endpoint_exists()

### Community 20 - "runner.js"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 21 - "test_api_main.py"
Cohesion: 0.60
Nodes (4): TestClient, test_404_handler(), test_cors_headers(), test_health_check()

### Community 22 - "test_api_upload_stream.py"
Cohesion: 0.67
Nodes (3): TestClient, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume()

### Community 31 - "Domain Docs"
Cohesion: 0.33
Nodes (5): Before exploring, read these, Domain Docs, File structure, Flag ADR conflicts, Use the glossary's vocabulary

### Community 45 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

## Knowledge Gaps
- **69 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `oxc` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `upload_resume()` connect `routes/candidates.py` to `CandidateSectionVector`, `Settings`, `extract_candidate_profile_hybrid`, `hybrid_searcher.py`, `ParsedDocument`, `parse_pdf`, `parse_docx`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `ParsedDocument` connect `ParsedDocument` to `parse_pdf`, `routes/candidates.py`, `parse_docx`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `Candidate` connect `routes/candidates.py` to `CandidateSectionVector`, `Settings`, `ParsedDocument`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `Candidate` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate()`) actually correct?**
  _`Candidate` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ParsedDocument` (e.g. with `upload_resume()` and `upload_stream_resumes()`) actually correct?**
  _`ParsedDocument` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `TimelineLedger` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_timeline()`) actually correct?**
  _`TimelineLedger` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ResumeVersion` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_file()`) actually correct?**
  _`ResumeVersion` has 8 INFERRED edges - model-reasoned connections that need verification._