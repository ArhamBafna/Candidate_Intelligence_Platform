# Graph Report - Candidate_Intelligence_Platform  (2026-08-20)

## Corpus Check
- Corpus is ~37,473 words - fits in a single context window. You may not need a graph.

## Summary
- 565 nodes · 1061 edges · 60 communities (38 shown, 22 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 118 edges (avg confidence: 0.91)
- Token cost: 34,046 input · 1,506 output

## Community Hubs (Navigation)
- Upload & Ingestion
- App Bootstrap & Settings
- Candidate Data Models
- Hybrid Profile Extraction
- Entity Resolution
- UI Dependencies
- Hybrid Candidate Search
- Email Parsing
- PDF Parsing
- Document Chunking
- DOCX Parsing
- React UI Shell
- Backup Management
- Search API Routes
- Logging System
- CAS Storage
- Vector Store Tests
- Timeline Ledger
- Architecture & Setup Docs
- Search Stream Tests
- E2E Test Runner
- API Health Tests
- Upload Stream Tests
- Project Overview Docs
- Logs Endpoint Tests
- Search Logging Tests
- UI Build Tests
- Backups Module
- CRM Module
- Profiling Techniques
- Performance Skill
- Agentic Retrieval Idea
- UI Test Report
- Project Package
- Database Optimization
- LRU Caching
- Parallel Processing
- Vectorization
- Slots Optimization
- Memory Leak Detection
- Weakref Caching
- Line Profiling
- Memory Profiling
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
- `list_candidates()` --uses--> `Candidate`  [INFERRED]
  api/routes/candidates.py → storage/db_models.py
- `get_candidate()` --uses--> `Candidate`  [INFERRED]
  api/routes/candidates.py → storage/db_models.py
- `update_candidate_status()` --uses--> `CandidateStateMachine`  [INFERRED]
  api/routes/candidates.py → crm/state_machine.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Python Performance Optimization Stack** — references_details_cprofile, references_details_line_profiler, references_details_memory_profiler, references_advanced_patterns_tracemalloc [EXTRACTED 1.00]
- **CIP Core Processing Flow** — docs_how_candidate_intelligence_works_ingestion, docs_how_candidate_intelligence_works_hybrid_search, docs_ollama_setup_windows_llama [EXTRACTED 0.95]

## Communities (60 total, 22 thin omitted)

### Community 0 - "Upload & Ingestion"
Cohesion: 0.08
Nodes (48): batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_timeline(), list_candidates(), get (+40 more)

### Community 1 - "App Bootstrap & Settings"
Cohesion: 0.07
Nodes (42): get_db(), _get_sessionmaker(), get_settings(), get_vector_db(), Session, health_check(), lifespan(), get (+34 more)

### Community 2 - "Candidate Data Models"
Cohesion: 0.11
Nodes (40): Base, CandidateStateMachine, InvalidStateTransition, Transitions the candidate to a new status and logs the event., TransitionContext, Exception, Candidate, CandidateTimelineEvent (+32 more)

### Community 3 - "Hybrid Profile Extraction"
Cohesion: 0.08
Nodes (37): skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), calculate_tier1_confidence(), extract_candidate_profile_hybrid(), _extract_deterministic_profile(), normalize_name() (+29 more)

### Community 4 - "Entity Resolution"
Cohesion: 0.10
Nodes (27): Enum, CandidateIdentifiers, _normalize(), ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 5 - "UI Dependencies"
Cohesion: 0.05
Nodes (37): autoprefixer, lucide-react, oxlint, postcss, react, react-dom, react-router-dom, @tailwindcss/postcss (+29 more)

### Community 6 - "Hybrid Candidate Search"
Cohesion: 0.10
Nodes (25): generate_embeddings(), generate_single_embedding(), Generate dense vector embeddings for a list of texts using fastembed. Returns…, build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently… (+17 more)

### Community 7 - "Email Parsing"
Cohesion: 0.14
Nodes (23): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+15 more)

### Community 8 - "PDF Parsing"
Cohesion: 0.16
Nodes (20): _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when…, _make_minimal_pdf(), Path (+12 more)

### Community 9 - "Document Chunking"
Cohesion: 0.17
Nodes (20): chunk_document(), A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, TextChunk, _make_doc(), Tests for ingestion/chunker.py Seam under test: chunk_document( doc:…, An empty document must yield an empty list (no ghost chunks)., chunk_document must return a list of TextChunk instances. (+12 more)

### Community 10 - "DOCX Parsing"
Cohesion: 0.18
Nodes (18): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, _make_docx(), Path, Tests for ingestion/parsers/docx_parser.py Seam under test: parse_docx(path:…, Write a .docx file with the given paragraphs (and optional table). (+10 more)

### Community 11 - "React UI Shell"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 12 - "Backup Management"
Cohesion: 0.18
Nodes (10): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, test_cas_storage_sync() (+2 more)

### Community 13 - "Search API Routes"
Cohesion: 0.37
Nodes (11): _build_search_query(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), post, Session, BaseModel (+3 more)

### Community 14 - "Logging System"
Cohesion: 0.35
Nodes (8): fetch_system_logs(), get, get_recent_logs(), memory_buffer_processor(), setup_logging(), test_get_recent_logs_truncation(), test_memory_buffer_processor(), test_setup_logging_configures_structlog()

### Community 15 - "CAS Storage"
Cohesion: 0.28
Nodes (5): CASManager, Path, Store content in the CAS file structure. Returns (sha256_hash,…, Verify CAS saves files at the correct sharded paths and deduplicates identical…, test_cas_storage()

### Community 17 - "Timeline Ledger"
Cohesion: 0.33
Nodes (4): Any, Session, Logs a new event in the candidate's timeline., Retrieves all timeline events for a candidate, ordered by creation date…

### Community 18 - "Architecture & Setup Docs"
Cohesion: 0.33
Nodes (6): uv Package Manager, Hybrid Search Architecture, Resume Ingestion Pipeline, Ollama LLM Integration, Playwright Installation Blocker, Async I/O

### Community 19 - "Search Stream Tests"
Cohesion: 0.40
Nodes (5): TestClient, Test that the search stream yields the expected stage events., Test that the POST /search/stream endpoint exists and accepts valid requests., test_search_stream_emits_progress_events(), test_search_stream_endpoint_exists()

### Community 20 - "E2E Test Runner"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 21 - "API Health Tests"
Cohesion: 0.60
Nodes (4): TestClient, test_404_handler(), test_cors_headers(), test_health_check()

### Community 22 - "Upload Stream Tests"
Cohesion: 0.67
Nodes (3): TestClient, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume()

## Knowledge Gaps
- **48 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `oxc` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `upload_resume()` connect `Upload & Ingestion` to `App Bootstrap & Settings`, `Candidate Data Models`, `Hybrid Profile Extraction`, `Hybrid Candidate Search`, `PDF Parsing`, `Document Chunking`, `DOCX Parsing`, `CAS Storage`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `ParsedDocument` connect `Upload & Ingestion` to `PDF Parsing`, `Document Chunking`, `DOCX Parsing`, `Email Parsing`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Candidate Data Models` to `Upload & Ingestion`, `Search API Routes`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `Candidate` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate()`) actually correct?**
  _`Candidate` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ParsedDocument` (e.g. with `upload_resume()` and `upload_stream_resumes()`) actually correct?**
  _`ParsedDocument` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `TimelineLedger` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_timeline()`) actually correct?**
  _`TimelineLedger` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ResumeVersion` (e.g. with `batch_reprocess_candidate_stream()` and `get_candidate_file()`) actually correct?**
  _`ResumeVersion` has 8 INFERRED edges - model-reasoned connections that need verification._