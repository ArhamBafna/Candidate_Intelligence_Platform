# Graph Report - Candidate_Intelligence_Platform  (2026-08-21)

## Corpus Check
- 106 files · ~45,116 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 674 nodes · 1186 edges · 66 communities (52 shown, 14 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 131 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9f7f0f0e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- routes/candidates.py
- Settings
- CandidateSectionVector
- extract_candidate_profile_hybrid
- resolve
- devDependencies
- search_candidates
- parse_pdf
- extract_inferences
- Advanced optimization
- Changes Summary
- App.jsx
- BackupManager
- Optimization patterns
- main.py
- chunk_document
- models.py
- Issue tracker: GitHub
- Hybrid Search Architecture
- ParsedDocument
- runner.js
- test_api_main.py
- test_api_upload_stream.py
- Architecture Design Document (ADD)
- test_get_logs_endpoint_returns_recent_events
- test_search_emits_wide_event
- test_ui_build
- backups/__init__.py
- crm/__init__.py
- conftest.py
- Domain Docs
- Python Performance Optimization Skill
- Autonomous Agentic Retrieval System
- End-to-End UI Test Report
- candidate-intelligence-platform
- React + Vite
- Ollama Setup Guide (Windows)
- Environment & Tools Setup Guide (Windows)
- MockVectorStore
- test_email_parser.py
- Anti-AI Pattern Findings (Whole UI Scan)
- Task Tracker
- End-to-End Test Findings
- read docs\handoffs\h…
- Recruiter UI
- test_api_search_stream.py
- get_engine
- routes/search.py
- Async AI Candidate Insights
- structlog_middleware
- .update_vector_index

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 40 edges
2. `ParsedDocument` - 26 edges
3. `Settings` - 21 edges
4. `ResumeVersion` - 21 edges
5. `CandidateService` - 20 edges
6. `TimelineLedger` - 19 edges
7. `resolve()` - 19 edges
8. `chunk_document()` - 16 edges
9. `CandidateTimelineEvent` - 15 edges
10. `_make()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `Hero Image` --conceptually_related_to--> `Architecture Design Document (ADD)`  [INFERRED]
  ui/src/assets/hero.png → docs/architecture_design_document.md
- `lifespan()` --uses--> `Settings`  [INFERRED]
  api/main.py → config/settings.py
- `update_candidate()` --calls--> `normalize_name()`  [INFERRED]
  api/routes/candidates.py → src/candidate_intelligence_platform/extraction/hybrid_extractor.py
- `update_candidate()` --calls--> `normalize_title()`  [INFERRED]
  api/routes/candidates.py → src/candidate_intelligence_platform/extraction/hybrid_extractor.py

## Import Cycles
- None detected.

## Communities (66 total, 14 thin omitted)

### Community 0 - "routes/candidates.py"
Cohesion: 0.06
Nodes (84): batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_insight(), get_candidate_timeline(), list_candidates() (+76 more)

### Community 1 - "Settings"
Cohesion: 0.24
Nodes (12): get_db(), _get_sessionmaker(), get_settings(), get_vector_db(), Session, BaseSettings, Settings, test_get_db() (+4 more)

### Community 2 - "CandidateSectionVector"
Cohesion: 0.18
Nodes (14): DBConnection, LanceModel, CandidateSectionVector, get_lancedb_connection(), Connect to the embedded LanceDB instance at the specified path., patch, Session, TestClient (+6 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.11
Nodes (30): skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), assess_tier1(), calculate_tier1_confidence(), extract_candidate_profile_hybrid(), _extract_deterministic_profile() (+22 more)

### Community 4 - "resolve"
Cohesion: 0.10
Nodes (27): Enum, CandidateIdentifiers, _normalize(), ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (39): autoprefixer, lucide-react, oxlint, @phosphor-icons/react, postcss, react, react-dom, react-router-dom (+31 more)

### Community 6 - "search_candidates"
Cohesion: 0.07
Nodes (41): _check_gpu_available(), generate_embeddings(), generate_single_embedding(), _get_embedding_model(), Lazy-loaded embedding model for vector search with GPU auto-detect. Model:…, Check if GPU (CUDA) is available for acceleration., Lazy-load the embedding model on first use (thread-safe, GPU with CPU fallback)., Generate a single embedding vector (cached for repeated queries). (+33 more)

### Community 7 - "parse_pdf"
Cohesion: 0.19
Nodes (14): _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when…, _make_minimal_pdf(), Path (+6 more)

### Community 8 - "extract_inferences"
Cohesion: 0.16
Nodes (12): ollama, extract_inferences(), Extract AI inferences from text using a local LLM via Ollama. Defaults to…, Test when LLM returns null claim_value and entity in claim_key., test_llm_claim_value_null_logs_warning_and_repairs(), test_llm_extraction_failure_logs_ai_warning(), test_vector_search_failure_logs_ai_warning(), Live integration test against running Ollama instance. (+4 more)

### Community 9 - "Advanced optimization"
Cohesion: 0.11
Nodes (17): Advanced optimization, Benchmarking tools, Custom benchmark decorator, Database optimization, Memory optimization, Pattern 11: NumPy for numerical operations, Pattern 12: Caching with functools.lru_cache, Pattern 13: Using __slots__ for memory (+9 more)

### Community 10 - "Changes Summary"
Cohesion: 0.13
Nodes (14): Changes Summary, Deferred Work, Files Changed, Overview, Quality Guardrails, Session Handoff: Performance Optimization (August 2026), T0: Benchmark Harness, T1: Kill Double spaCy Pass + Truncate NER Input (+6 more)

### Community 11 - "App.jsx"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 12 - "BackupManager"
Cohesion: 0.18
Nodes (10): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, test_cas_storage_sync() (+2 more)

### Community 13 - "Optimization patterns"
Cohesion: 0.14
Nodes (13): Optimization patterns, Pattern 10: Function Call Overhead, Pattern 1: cProfile — CPU profiling, Pattern 2: line_profiler — line-by-line profiling, Pattern 3: memory_profiler — memory usage, Pattern 4: py-spy — running-process profiling, Pattern 5: List Comprehensions vs Loops, Pattern 6: Generator Expressions for Memory (+5 more)

### Community 14 - "main.py"
Cohesion: 0.23
Nodes (12): health_check(), lifespan(), get, fetch_system_logs(), get, get_recent_logs(), memory_buffer_processor(), setup_logging() (+4 more)

### Community 15 - "chunk_document"
Cohesion: 0.16
Nodes (21): chunk_document(), Section-aware text chunker with context injection. Public interface:…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, TextChunk, _make_doc(), Tests for ingestion/chunker.py Seam under test: chunk_document( doc:…, An empty document must yield an empty list (no ghost chunks). (+13 more)

### Community 16 - "models.py"
Cohesion: 0.20
Nodes (11): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, Shared data model for all ingestion parsers., _make_docx(), Path, Tests for ingestion/parsers/docx_parser.py Seam under test: parse_docx(path:… (+3 more)

### Community 17 - "Issue tracker: GitHub"
Cohesion: 0.33
Nodes (5): Issue tracker: GitHub, Issue workflow, Pull requests as a triage surface, Shared routing, Wayfinding operations

### Community 19 - "ParsedDocument"
Cohesion: 0.26
Nodes (12): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+4 more)

### Community 20 - "runner.js"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 21 - "test_api_main.py"
Cohesion: 0.60
Nodes (4): TestClient, test_404_handler(), test_cors_headers(), test_health_check()

### Community 22 - "test_api_upload_stream.py"
Cohesion: 0.60
Nodes (4): TestClient, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume(), test_upload_stream_transparency_events()

### Community 30 - "conftest.py"
Cohesion: 0.18
Nodes (12): client(), db_engine(), db_session(), isolate_test_environment(), mock_vector_db(), fixture, Provides a clean database session for tests., Provides isolated settings for tests. (+4 more)

### Community 31 - "Domain Docs"
Cohesion: 0.40
Nodes (4): Domain Docs, Exploration gate, File structure, Flag ADR conflicts

### Community 45 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + Vite

### Community 46 - "Ollama Setup Guide (Windows)"
Cohesion: 0.20
Nodes (9): 1. Install Ollama on Windows, 2. Pull Required LLM Model, 3. Verify Ollama Setup, 4. Configuration Options (Optional), Ollama Setup Guide (Windows), Option A: Official Installer (Recommended), Option B: Windows Package Manager (winget), Step A: Test Ollama CLI (+1 more)

### Community 47 - "Environment & Tools Setup Guide (Windows)"
Cohesion: 0.22
Nodes (8): 1. Tool Checklist & Current Status, 2. Setting Up PATH (Required for `uv` & `python`), 3. Installing `uv` (If setting up on a clean machine), 4. Install Project Dependencies (`uv sync`), 5. Verify Full Environment & Tests, Environment & Tools Setup Guide (Windows), Option A: Via PowerShell (Automated), Option B: Via GUI

### Community 49 - "test_email_parser.py"
Cohesion: 0.32
Nodes (7): _make_eml(), Path, Tests for ingestion/parsers/email_parser.py Seam under test: parse_email(path:…, Write a minimal plain-text .eml file and return its path., # NOTE: RFC-2822 requires headers to start at column 0 (no leading whitespace)., parse_email must return ParsedDocument, extract body text, pages, and metadata…, test_parse_email_functional_flow()

### Community 50 - "Anti-AI Pattern Findings (Whole UI Scan)"
Cohesion: 0.33
Nodes (5): 1. Hallmark Audit, 2. Design-Taste-Frontend Audit, 3. Impeccable Critique & Layout Structure, 4. Humanise-Text Review (docs/architecture_design_document.md), Anti-AI Pattern Findings (Whole UI Scan)

### Community 51 - "Task Tracker"
Cohesion: 0.50
Nodes (3): Completed Tickets, Performance Optimization Tickets, Task Tracker

### Community 52 - "End-to-End Test Findings"
Cohesion: 0.40
Nodes (4): Bug / Blocker, E2E Run: August 19, 2026, End-to-End Test Findings, System Configuration

### Community 53 - "read docs\handoffs\h…"
Cohesion: 0.33
Nodes (5): 1. Where is the "Strict Syntax" coming from?, 2. Why "Early Termination" is (usually) the right move, read docs\handoffs\h…, **The Verdict**, **Why this changes everything for your "Paris" search:**

### Community 60 - "test_api_search_stream.py"
Cohesion: 0.40
Nodes (5): TestClient, Test that the search stream yields the expected stage events., Test that the POST /search/stream endpoint exists and accepts valid requests., test_search_stream_emits_progress_events(), test_search_stream_endpoint_exists()

### Community 61 - "get_engine"
Cohesion: 0.21
Nodes (11): get_engine(), Engine, Create a SQLAlchemy engine configured for SQLite with WAL mode., init_db(), Engine, Creates all declarative tables, FTS5 virtual tables, and performance indexes., Verify that the database engine connects and sets WAL mode correctly., test_engine_connect_event_non_sqlite() (+3 more)

### Community 62 - "routes/search.py"
Cohesion: 0.37
Nodes (11): _build_search_query(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), post, Session, BaseModel (+3 more)

### Community 63 - "Async AI Candidate Insights"
Cohesion: 0.18
Nodes (10): 1. API & Transport Design, 2. Cancellation Lifecycle, Architecture & Technical Decisions, Async AI Candidate Insights, CRITICAL: IMPLEMENTATION SKILLS TO USE, Key Assumptions to Validate, MVP Scope, Not Doing (and Why) (+2 more)

### Community 64 - "structlog_middleware"
Cohesion: 0.67
Nodes (3): structlog_middleware(), middleware, Request

## Knowledge Gaps
- **111 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `oxc` (+106 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ParsedDocument` connect `ParsedDocument` to `routes/candidates.py`, `.update_vector_index`, `parse_pdf`, `chunk_document`, `models.py`, `test_email_parser.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `ResumeVersion` connect `routes/candidates.py` to `search_candidates`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings` to `routes/candidates.py`, `extract_inferences`, `main.py`, `conftest.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Candidate` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate()`) actually correct?**
  _`Candidate` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ParsedDocument` (e.g. with `upload_resume()` and `upload_stream_resumes()`) actually correct?**
  _`ParsedDocument` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Settings` (e.g. with `lifespan()` and `batch_reprocess_candidate_stream()`) actually correct?**
  _`Settings` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `ResumeVersion` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_file()`) actually correct?**
  _`ResumeVersion` has 9 INFERRED edges - model-reasoned connections that need verification._