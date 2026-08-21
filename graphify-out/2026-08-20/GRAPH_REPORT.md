# Graph Report - Candidate_Intelligence_Platform  (2026-08-20)

## Corpus Check
- 103 files · ~39,488 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 662 nodes · 1169 edges · 59 communities (46 shown, 13 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 126 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b4ac64f0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_api_candidates.py
- test_performance.py
- CandidateSectionVector
- extract_candidate_profile_hybrid
- resolve
- devDependencies
- hybrid_searcher.py
- ParsedDocument
- routes/candidates.py
- Advanced Optimization
- extract_inferences
- App.jsx
- BackupManager
- Optimization Patterns
- main.py
- chunk_document
- models.py
- Issue tracker: GitHub
- Hybrid Search Architecture
- email_parser.py
- runner.js
- test_api_main.py
- test_api_upload_stream.py
- Architecture Design Document (ADD)
- test_get_logs_endpoint_returns_recent_events
- test_search_emits_wide_event
- test_ui_build
- backups/__init__.py
- crm/__init__.py
- TestSearchBenchmarks
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
- test_api_search_stream.py
- End-to-End Test Findings
- Recruiter UI

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 38 edges
2. `ParsedDocument` - 28 edges
3. `Settings` - 22 edges
4. `TimelineLedger` - 19 edges
5. `resolve()` - 19 edges
6. `ResumeVersion` - 19 edges
7. `chunk_document()` - 18 edges
8. `CandidateService` - 16 edges
9. `_make()` - 15 edges
10. `extract_candidate_profile_hybrid()` - 14 edges

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

## Communities (59 total, 13 thin omitted)

### Community 0 - "test_api_candidates.py"
Cohesion: 0.11
Nodes (23): MockVectorStore, CASManager, Path, Store content in the CAS file structure. Returns (sha256_hash,…, MockVectorStore, Mock LanceDB vector store connection for isolated test runs., parametrize, Session (+15 more)

### Community 1 - "test_performance.py"
Cohesion: 0.07
Nodes (39): get_db(), _get_sessionmaker(), get_settings(), get_vector_db(), Session, BaseSettings, Settings, client() (+31 more)

### Community 2 - "CandidateSectionVector"
Cohesion: 0.15
Nodes (15): DBConnection, LanceModel, CandidateSectionVector, get_lancedb_connection(), Helper to create a vector dictionary record from a chunk and embedding., Connect to the embedded LanceDB instance at the specified path., patch, Session (+7 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.11
Nodes (30): skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), assess_tier1(), calculate_tier1_confidence(), extract_candidate_profile_hybrid(), _extract_deterministic_profile() (+22 more)

### Community 4 - "resolve"
Cohesion: 0.10
Nodes (27): Enum, CandidateIdentifiers, _normalize(), ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (39): autoprefixer, lucide-react, oxlint, @phosphor-icons/react, postcss, react, react-dom, react-router-dom (+31 more)

### Community 6 - "hybrid_searcher.py"
Cohesion: 0.09
Nodes (29): generate_embeddings(), generate_single_embedding(), Generate dense vector embeddings for a list of texts using fastembed. Returns…, build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently… (+21 more)

### Community 7 - "ParsedDocument"
Cohesion: 0.15
Nodes (18): ParsedDocument, Canonical output of every parser. Attributes: text: Full extracted plain-text,…, _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when… (+10 more)

### Community 8 - "routes/candidates.py"
Cohesion: 0.08
Nodes (58): batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_timeline(), list_candidates(), get (+50 more)

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
Nodes (37): health_check(), lifespan(), get, structlog_middleware(), fetch_system_logs(), get, _build_search_query(), _format_search_results() (+29 more)

### Community 15 - "chunk_document"
Cohesion: 0.16
Nodes (21): chunk_document(), Section-aware text chunker with context injection. Public interface:…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, TextChunk, _make_doc(), Tests for ingestion/chunker.py Seam under test: chunk_document( doc:…, An empty document must yield an empty list (no ghost chunks). (+13 more)

### Community 16 - "models.py"
Cohesion: 0.20
Nodes (11): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, Shared data model for all ingestion parsers., _make_docx(), Path, Tests for ingestion/parsers/docx_parser.py Seam under test: parse_docx(path:… (+3 more)

### Community 17 - "Issue tracker: GitHub"
Cohesion: 0.29
Nodes (6): Conventions, Issue tracker: GitHub, Pull requests as a triage surface, Wayfinding operations, When a skill says "fetch the relevant ticket", When a skill says "publish to the issue tracker"

### Community 19 - "email_parser.py"
Cohesion: 0.27
Nodes (10): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+2 more)

### Community 20 - "runner.js"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 21 - "test_api_main.py"
Cohesion: 0.60
Nodes (4): TestClient, test_404_handler(), test_cors_headers(), test_health_check()

### Community 22 - "test_api_upload_stream.py"
Cohesion: 0.60
Nodes (4): TestClient, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume(), test_upload_stream_transparency_events()

### Community 30 - "TestSearchBenchmarks"
Cohesion: 0.20
Nodes (6): Benchmarks for hybrid search pipeline., Upload resumes to create a searchable corpus., Benchmark keyword-only search., Benchmark search with location + title filters., Benchmark streaming search endpoint., TestSearchBenchmarks

### Community 31 - "Domain Docs"
Cohesion: 0.33
Nodes (5): Before exploring, read these, Domain Docs, File structure, Flag ADR conflicts, Use the glossary's vocabulary

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

### Community 51 - "test_api_search_stream.py"
Cohesion: 0.40
Nodes (5): TestClient, Test that the search stream yields the expected stage events., Test that the POST /search/stream endpoint exists and accepts valid requests., test_search_stream_emits_progress_events(), test_search_stream_endpoint_exists()

### Community 52 - "End-to-End Test Findings"
Cohesion: 0.40
Nodes (4): Bug / Blocker, E2E Run: August 19, 2026, End-to-End Test Findings, System Configuration

## Knowledge Gaps
- **87 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `oxc` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ParsedDocument` connect `ParsedDocument` to `test_performance.py`, `routes/candidates.py`, `chunk_document`, `models.py`, `test_email_parser.py`, `email_parser.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `Settings` connect `test_performance.py` to `routes/candidates.py`, `extract_inferences`, `main.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `Candidate` connect `routes/candidates.py` to `test_api_candidates.py`, `CandidateSectionVector`, `main.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Candidate` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate()`) actually correct?**
  _`Candidate` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ParsedDocument` (e.g. with `upload_resume()` and `upload_stream_resumes()`) actually correct?**
  _`ParsedDocument` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Settings` (e.g. with `lifespan()` and `batch_reprocess_candidate_stream()`) actually correct?**
  _`Settings` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `TimelineLedger` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_timeline()`) actually correct?**
  _`TimelineLedger` has 9 INFERRED edges - model-reasoned connections that need verification._