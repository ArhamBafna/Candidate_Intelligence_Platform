# Graph Report - Candidate_Intelligence_Platform  (2026-08-21)

## Corpus Check
- 119 files · ~53,505 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 802 nodes · 1448 edges · 56 communities (44 shown, 12 thin omitted)
- Extraction: 84% EXTRACTED · 15% INFERRED · 1% AMBIGUOUS · INFERRED: 224 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Candidates API Routes
- Agent Rules and Governance
- Embeddings and Intelligence
- Deterministic NER Extraction
- Search API Dependencies
- Entity Resolution
- Frontend Dependencies
- App Core and Logging
- Task Tracker Tickets
- Architecture Design Concepts
- Bulk Ingestion Handoff
- Document Chunking
- Email Parsing
- Vector Store and LanceDB
- Oxlint Configuration
- Environment Setup Docs
- Bulk Ingest Script
- Backup Manager
- PDF Parsing
- UI Entry Point
- DOCX Parsing
- Domain Docs and ADRs
- Test Mocks and Fixtures
- Icon Sprite Assets
- Issue Tracker Workflow
- Hero Branding Assets
- E2E Test Runner
- API Main Tests
- Upload Stream Tests
- Favicon Branding
- Logs API Tests
- Search Logging Tests
- UI Build Test
- Vite Boilerplate Assets
- Backups Package Init
- CRM Package Init
- Perf Handoff Notes
- Shared Routing Note
- GPU Auto-Detect Note
- spaCy Truncation Note
- Package Distribution Meta
- React Logo Asset

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 42 edges
2. `ParsedDocument` - 28 edges
3. `process_single_file()` - 24 edges
4. `Settings` - 23 edges
5. `ResumeVersion` - 23 edges
6. `resolve()` - 21 edges
7. `CandidateService` - 20 edges
8. `TimelineLedger` - 19 edges
9. `chunk_document()` - 18 edges
10. `CandidateTimelineEvent` - 17 edges

## Surprising Connections (you probably didn't know these)
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `Mission: privacy-first local-first candidate intelligence` --semantically_similar_to--> `Privacy-first local-first principle`  [INFERRED] [semantically similar]
  AGENTS.md → README.md
- `lifespan()` --uses--> `Settings`  [INFERRED]
  api/main.py → config/settings.py
- `update_candidate()` --calls--> `normalize_name()`  [INFERRED]
  api/routes/candidates.py → src/candidate_intelligence_platform/extraction/hybrid_extractor.py
- `update_candidate()` --calls--> `normalize_title()`  [INFERRED]
  api/routes/candidates.py → src/candidate_intelligence_platform/extraction/hybrid_extractor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Measure-before-and-after optimization workflow** — agents_skills_python_performance_optimization_references_advanced_patterns, references_advanced_custom_benchmark_decorator, references_advanced_pytest_benchmark_testing [INFERRED 0.85]
- **Five-step performance optimization workflow** — agents_skills_python_performance_optimization_skill_workflow_measure, agents_skills_python_performance_optimization_skill_workflow_profile, agents_skills_python_performance_optimization_skill_workflow_choose, agents_skills_python_performance_optimization_skill_workflow_change, agents_skills_python_performance_optimization_skill_workflow_verify [EXTRACTED 1.00]
- **CIP ingestion-to-retrieval pipeline** — readme_content_addressable_store, readme_document_parsers, readme_section_aware_chunker, readme_entity_resolution_engine, readme_sqlite_wal_database, readme_lancedb_vector_store, readme_fastapi_rest_backend, readme_react_tailwind_ui [EXTRACTED 1.00]
- **Wayfinding Ticket Lifecycle** — docs_agents_issue_tracker_wayfinder_map_issue, docs_agents_issue_tracker_blocking_dependencies, docs_agents_issue_tracker_gh_cli [EXTRACTED 0.95]
- **CIP Hybrid Search Pipeline Flow** — docs_architecture_design_document_ast_parser_stage, docs_architecture_design_document_hybrid_search_rrf, docs_architecture_design_document_cross_encoder_reranker, docs_architecture_design_document_match_rationale_explainer [EXTRACTED 1.00]
- **CIP Ingestion Dedup Flow** — docs_how_candidate_intelligence_works_sha256_fingerprinting_dedup, docs_architecture_design_document_immutable_evidence_cas, docs_architecture_design_document_multi_stage_parsers, docs_architecture_design_document_two_tier_entity_resolution [EXTRACTED 0.95]
- **Agentic Retrieval MVP Toolset Flow** — docs_ideas_agentic_retrieval_agentic_search_pipeline, docs_ideas_agentic_retrieval_filter_by_metadata_tool, docs_ideas_agentic_retrieval_vector_search_tool, docs_ideas_agentic_retrieval_read_raw_resume_tool, docs_ideas_agentic_retrieval_ten_candidate_guard [EXTRACTED 1.00]
- **AI Insight Generation-Cancellation Flow** — docs_ideas_async_ai_insights_async_ai_candidate_insights, docs_ideas_async_ai_insights_insight_sse_endpoint, docs_ideas_async_ai_insights_cancellation_lifecycle, docs_ideas_async_ai_insights_top3_only_rationale [EXTRACTED 1.00]
- **Performance Optimization Program (P0-P7)** — docs_task_performance_optimization_tickets, docs_task_ticket_p0_benchmark_harness, docs_task_ticket_p1_spacy_double_pass_elimination, docs_task_ticket_p2_thread_offload_cpu_io, docs_task_ticket_p3_db_indexes_single_transaction, docs_task_ticket_p4_lazy_model_loading, docs_task_ticket_p6_gpu_auto_detect_cpu_fallback [INFERRED]
- **Browser Automation Approaches for UI E2E Testing** — docs_tests_test_findings_agent_browser_subagent, docs_tests_test_findings_playwright_driver_download_failure, docs_tests_test_findings_blocked_e2e_run_aug19, docs_tests_end_to_end_ui_test_report_playwriter_direct_cdp_driver, docs_tests_end_to_end_ui_test_report_ui_test_report [INFERRED]
- **Bulk Ingestion Parsing & Filtering Stack** — ingestion_reports_bulk_ingest_summary_pymupdf_parser, ingestion_reports_bulk_ingest_summary_docx_parser, ingestion_reports_bulk_ingest_summary_scanned_image_requires_ocr, ingestion_reports_bulk_ingest_summary_ai_classification_not_resume, ingestion_reports_bulk_ingest_summary_duplicate_detection [INFERRED]
- **Product visual identity system (dark + violet isometric stack)** — ui_src_assets_hero_heroshot, ui_src_assets_hero_stacked_slabs, ui_src_assets_hero_purple_rim_lighting, ui_src_assets_hero_dark_theme_branding [INFERRED 0.95]

## Communities (56 total, 12 thin omitted)

### Community 0 - "Candidates API Routes"
Cohesion: 0.06
Nodes (85): _get_sessionmaker(), batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_insight(), get_candidate_timeline() (+77 more)

### Community 1 - "Agent Rules and Governance"
Cohesion: 0.06
Nodes (52): AGENTS.md - CIP agent guidelines, Implementation rules, Keep candidate data and processing local rule, Mission: privacy-first local-first candidate intelligence, Mock heavy ML models in tests rule, Python Performance Optimization - advanced reference, Python Performance Optimization - standard reference, Pattern 10: Function Call Overhead (+44 more)

### Community 2 - "Embeddings and Intelligence"
Cohesion: 0.07
Nodes (42): _check_gpu_available(), generate_embeddings(), generate_single_embedding(), _get_embedding_model(), Lazy-loaded embedding model for vector search with GPU auto-detect. Model:…, Check if GPU (CUDA) is available for acceleration., Lazy-load the embedding model on first use (thread-safe, GPU with CPU fallback)., Generate a single embedding vector (cached for repeated queries). (+34 more)

### Community 3 - "Deterministic NER Extraction"
Cohesion: 0.07
Nodes (42): ollama, skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), assess_tier1(), calculate_tier1_confidence(), extract_candidate_profile_hybrid() (+34 more)

### Community 4 - "Search API Dependencies"
Cohesion: 0.09
Nodes (34): get_db(), get_settings(), get_vector_db(), Session, _build_search_query(), _format_search_results(), _hydrate_candidates(), perform_search() (+26 more)

### Community 5 - "Entity Resolution"
Cohesion: 0.10
Nodes (27): Enum, CandidateIdentifiers, _normalize(), ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 6 - "Frontend Dependencies"
Cohesion: 0.05
Nodes (39): autoprefixer, lucide-react, oxlint, @phosphor-icons/react, postcss, react, react-dom, react-router-dom (+31 more)

### Community 7 - "App Core and Logging"
Cohesion: 0.08
Nodes (31): health_check(), lifespan(), get, structlog_middleware(), fetch_system_logs(), get, get_engine(), Engine (+23 more)

### Community 8 - "Task Tracker Tickets"
Cohesion: 0.06
Nodes (39): Completed Tickets (01-06), Performance Optimization Ticket Program, Task Tracker, Ticket 06: PDF Parser OCR Fallback & Final Verification, Ticket P0: Baseline & Benchmark Harness (pytest-benchmark), Ticket P1: Kill Double spaCy Pass + Truncate NER Input, Ticket P2: Thread-Offload CPU/IO + Thread-Safety Fix, Ticket P3: DB Indexes + Single-Transaction Writes + busy_timeout (+31 more)

### Community 9 - "Architecture Design Concepts"
Cohesion: 0.08
Nodes (34): AST Parser Strict Filter Stage, $0-Cost Backup & Disaster Recovery, Candidate Intelligence Platform (CIP), ONNX Cross-Encoder Re-Ranker, Deterministic First Extraction (SpaCy NER + Regex), Event-Sourced Candidate Timeline Ledger, Fact vs Inference Split (candidate_claims), fastembed ONNX bge-small Embeddings (+26 more)

### Community 10 - "Bulk Ingestion Handoff"
Cohesion: 0.07
Nodes (30): Master Audit Telemetry Log (bulk_ingest_report.json), Bulk Ingestion CLI Script (scripts/bulk_ingest.py), Checkpointing & Resumption Engine, Dry-Run Simulation Mode (--dry-run), Entity Resolution Dummy Name Guard, Full-Text Search Tables (candidate_fts, claims_fts), LanceDB Vector Store, Multi-Tier Document Classifier (classify_document) (+22 more)

### Community 11 - "Document Chunking"
Cohesion: 0.16
Nodes (21): chunk_document(), Section-aware text chunker with context injection. Public interface:…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, TextChunk, _make_doc(), Tests for ingestion/chunker.py Seam under test: chunk_document( doc:…, An empty document must yield an empty list (no ghost chunks). (+13 more)

### Community 12 - "Email Parsing"
Cohesion: 0.16
Nodes (19): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+11 more)

### Community 13 - "Vector Store and LanceDB"
Cohesion: 0.15
Nodes (15): DBConnection, LanceModel, CandidateSectionVector, get_lancedb_connection(), Helper to create a vector dictionary record from a chunk and embedding., Connect to the embedded LanceDB instance at the specified path., patch, Session (+7 more)

### Community 14 - "Oxlint Configuration"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 15 - "Environment Setup Docs"
Cohesion: 0.15
Nodes (17): Candidate Intelligence Platform (CIP), Environment & Tools Setup Guide (Windows), Full Environment & Test Verification (pytest), Git Version Control, Ollama Binary in PATH, CPython 3.14 Windows Runtime, Windows User PATH Configuration, uv Package Manager (+9 more)

### Community 16 - "Bulk Ingest Script"
Cohesion: 0.24
Nodes (15): classify_document(), generate_markdown_summary(), get_file_hash(), process_single_file(), Any, Path, Generate a clean, structured, human-readable Markdown report summarizing the…, Process a single file through the full ingestion pipeline with fine-grained… (+7 more)

### Community 17 - "Backup Manager"
Cohesion: 0.18
Nodes (10): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, test_cas_storage_sync() (+2 more)

### Community 18 - "PDF Parsing"
Cohesion: 0.19
Nodes (14): _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when…, _make_minimal_pdf(), Path (+6 more)

### Community 19 - "UI Entry Point"
Cohesion: 0.19
Nodes (16): index.html App Entry Point, Title: Candidate Intelligence Platform, /favicon.svg Asset, /src/main.jsx Module Script Entry, #root Mount Div, HMR (Hot Module Replacement), Oxc, Oxlint (+8 more)

### Community 20 - "DOCX Parsing"
Cohesion: 0.20
Nodes (11): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, Shared data model for all ingestion parsers., _make_docx(), Path, Tests for ingestion/parsers/docx_parser.py Seam under test: parse_docx(path:… (+3 more)

### Community 21 - "Domain Docs and ADRs"
Cohesion: 0.24
Nodes (10): ADR Conflict Flagging, ADRs (Architecture Decision Records), CONTEXT-MAP.md, CONTEXT.md, Domain Docs Routing, Exploration Gate, Glossary Terms Usage, /domain-modeling Skill (+2 more)

### Community 23 - "Icon Sprite Assets"
Cohesion: 0.50
Nodes (8): bluesky-icon symbol (Bluesky logo), Brand/social link iconography concept, discord-icon symbol (Discord logo), documentation-icon symbol (docs/code-lines icon), github-icon symbol (GitHub octocat mark), social-icon symbol (user + badge icon), icons.svg SVG symbol sprite sheet, x-icon symbol (X/Twitter logo)

### Community 24 - "Issue Tracker Workflow"
Cohesion: 0.38
Nodes (7): GitHub Native Issue Dependencies, gh CLI, GitHub Issue Tracker, Issue Workflow (Create/Read/List/Comment/Label/Close), PRs as Triage Surface Flag, Wayfinder Map Issue, Wayfinder Operations

### Community 25 - "Hero Branding Assets"
Cohesion: 0.53
Nodes (6): Layered Data / Storage Abstraction Motif, Landing Page Hero Section (UI), Dark-Theme Visual Branding, Hero Image, Purple Gradient Rim Lighting, Isometric Stacked Rounded-Square Slabs

### Community 26 - "E2E Test Runner"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 27 - "API Main Tests"
Cohesion: 0.60
Nodes (4): TestClient, test_404_handler(), test_cors_headers(), test_health_check()

### Community 28 - "Upload Stream Tests"
Cohesion: 0.60
Nodes (4): TestClient, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume(), test_upload_stream_transparency_events()

### Community 29 - "Favicon Branding"
Cohesion: 0.50
Nodes (5): App Favicon (Purple Lightning Bolt), Lightning Bolt Glyph, Glow Ellipses + Alpha Mask Layer, Purple Brand Palette (#863bff / #7e14ff / #ede6ff), CIP Web UI Brand Identity

### Community 34 - "Vite Boilerplate Assets"
Cohesion: 0.67
Nodes (3): Boilerplate Template Asset, Vite Framework, Vite Logo

## Ambiguous Edges - Review These
- `Workflow Step 5: Verify` → `pytest test suite`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to
- `Decision rules: profile before optimizing, preserve behavior` → `Implementation rules`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to
- `Mock heavy ML models in tests rule` → `Document Parsers (PDF, DOCX, Email)`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to
- `Local-First Execution` → `Traditional Keyword Search Limits`  [AMBIGUOUS]
  docs/how_candidate_intelligence_works.html · relation: conceptually_related_to
- `SQLite WAL RDBMS + FTS5` → `SQLAlchemy 2.0 Mapped Refactor of db_models.py`  [AMBIGUOUS]
  docs/chats/trae-chat.md · relation: conceptually_related_to
- `Thread-Offload CPU/IO + Bounded Upload Semaphore` → `Per-Candidate Insight SSE Endpoint (/candidates/{id}/insight)`  [AMBIGUOUS]
  docs/ideas/async-ai-insights.md · relation: conceptually_related_to
- `React + Vite Template` → `Title: Candidate Intelligence Platform`  [AMBIGUOUS]
  ui/index.html · relation: semantically_similar_to
- `Oxlint` → `@vitejs/plugin-react`  [AMBIGUOUS]
  ui/README.md · relation: conceptually_related_to
- `bluesky-icon symbol (Bluesky logo)` → `x-icon symbol (X/Twitter logo)`  [AMBIGUOUS]
  ui/public/icons.svg · relation: semantically_similar_to
- `discord-icon symbol (Discord logo)` → `github-icon symbol (GitHub octocat mark)`  [AMBIGUOUS]
  ui/public/icons.svg · relation: semantically_similar_to

## Knowledge Gaps
- **76 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `oxc` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Workflow Step 5: Verify` and `pytest test suite`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Decision rules: profile before optimizing, preserve behavior` and `Implementation rules`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Mock heavy ML models in tests rule` and `Document Parsers (PDF, DOCX, Email)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Local-First Execution` and `Traditional Keyword Search Limits`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `SQLite WAL RDBMS + FTS5` and `SQLAlchemy 2.0 Mapped Refactor of db_models.py`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Thread-Offload CPU/IO + Bounded Upload Semaphore` and `Per-Candidate Insight SSE Endpoint (/candidates/{id}/insight)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `React + Vite Template` and `Title: Candidate Intelligence Platform`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._