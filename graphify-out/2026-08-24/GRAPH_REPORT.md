# Graph Report - Candidate_Intelligence_Platform  (2026-08-24)

## Corpus Check
- 136 files · ~76,459 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1252 nodes · 2523 edges · 80 communities (69 shown, 11 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 402 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cf1d8949`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Candidate
- Python Performance Optimization - advanced reference
- embeddings.py
- extract_candidate_profile_hybrid
- _run_pipeline_capturing_embedding
- resolve
- devDependencies
- main.py
- End-to-End UI Test Report & Findings
- Candidate Intelligence Platform (CIP)
- Bulk Ingestion CLI Script (scripts/bulk_ingest.py)
- test_chunker.py
- ParsedDocument
- CandidateService
- App.jsx
- Environment & Tools Setup Guide (Windows)
- CASManager
- BackupManager
- parse_pdf
- React + Vite Template
- models.py
- Exploration Gate
- translate_reprocess_progress
- icons.svg SVG symbol sprite sheet
- gh CLI
- Hero Image
- runner.js
- test_api_main.py
- test_api_upload_stream.py
- App Favicon (Purple Lightning Bolt)
- test_get_logs_endpoint_returns_recent_events
- test_logging.py
- test_ui_build
- ingest_file
- Vite Logo
- backups/__init__.py
- crm/__init__.py
- Performance Benchmark Harness (tests/test_performance.py)
- Shared Routing Phrases
- GPU Auto-Detect with CPU Fallback
- Single spaCy Pass + NER Input Truncation (5000 chars)
- candidate-intelligence-platform
- React Logo
- routes/search.py
- resolve_chat_model
- job_ad_distiller.py
- test_model_fallbacks.py
- test_search_engine.py
- Session
- search_candidates
- build_match_rationale
- reranker.py
- conftest.py
- test_api_insight_fallback.py
- execute_vector_search
- Search Accuracy Evaluation Harness
- Architecture Deepening Opportunities
- Anti-AI Pattern Findings (Whole UI Scan)
- reciprocal_rank_fusion
- wayfinder-open-questions.md
- routes/candidates.py
- Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier)
- Centralized AI Prompts
- Settings
- extract_inferences
- test_ingestion_concurrency.py

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 72 edges
2. `Settings` - 63 edges
3. `ingest_file()` - 56 edges
4. `IntakeStatus` - 33 edges
5. `IntakeSource` - 33 edges
6. `TimelineMode` - 31 edges
7. `ResumeVersion` - 30 edges
8. `CASManager` - 29 edges
9. `CandidateService` - 28 edges
10. `ParsedDocument` - 24 edges

## Surprising Connections (you probably didn't know these)
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `test_fetch_candidate_documents_empty()` --calls--> `fetch_candidate_documents()`  [INFERRED]
  tests/test_search_engine.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `Mission: privacy-first local-first candidate intelligence` --semantically_similar_to--> `Privacy-first local-first principle`  [INFERRED] [semantically similar]
  AGENTS.md → README.md
- `test_unhandled_exception_still_logs_http_request()` --indirect_call--> `get_db()`  [INFERRED]
  tests/test_api_main.py → api/dependencies.py
- `lifespan()` --uses--> `Settings`  [INFERRED]
  api/main.py → config/settings.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **CIP Ingestion Dedup Flow** — docs_how_candidate_intelligence_works_sha256_fingerprinting_dedup, docs_architecture_design_document_immutable_evidence_cas, docs_architecture_design_document_multi_stage_parsers, docs_architecture_design_document_two_tier_entity_resolution [EXTRACTED 0.95]
- **Wayfinding Ticket Lifecycle** — docs_agents_issue_tracker_wayfinder_map_issue, docs_agents_issue_tracker_blocking_dependencies, docs_agents_issue_tracker_gh_cli [EXTRACTED 0.95]
- **Agentic Retrieval MVP Toolset Flow** — docs_ideas_agentic_retrieval_agentic_search_pipeline, docs_ideas_agentic_retrieval_filter_by_metadata_tool, docs_ideas_agentic_retrieval_vector_search_tool, docs_ideas_agentic_retrieval_read_raw_resume_tool, docs_ideas_agentic_retrieval_ten_candidate_guard [EXTRACTED 1.00]
- **AI Insight Generation-Cancellation Flow** — docs_ideas_async_ai_insights_async_ai_candidate_insights, docs_ideas_async_ai_insights_insight_sse_endpoint, docs_ideas_async_ai_insights_cancellation_lifecycle, docs_ideas_async_ai_insights_top3_only_rationale [EXTRACTED 1.00]
- **CIP Hybrid Search Pipeline Flow** — docs_architecture_design_document_ast_parser_stage, docs_architecture_design_document_hybrid_search_rrf, docs_architecture_design_document_cross_encoder_reranker, docs_architecture_design_document_match_rationale_explainer [EXTRACTED 1.00]
- **Five-step performance optimization workflow** — agents_skills_python_performance_optimization_skill_workflow_measure, agents_skills_python_performance_optimization_skill_workflow_profile, agents_skills_python_performance_optimization_skill_workflow_choose, agents_skills_python_performance_optimization_skill_workflow_change, agents_skills_python_performance_optimization_skill_workflow_verify [EXTRACTED 1.00]
- **CIP ingestion-to-retrieval pipeline** — readme_content_addressable_store, readme_document_parsers, readme_section_aware_chunker, readme_entity_resolution_engine, readme_sqlite_wal_database, readme_lancedb_vector_store, readme_fastapi_rest_backend, readme_react_tailwind_ui [EXTRACTED 1.00]
- **Measure-before-and-after optimization workflow** — agents_skills_python_performance_optimization_references_advanced_patterns, references_advanced_custom_benchmark_decorator, references_advanced_pytest_benchmark_testing [INFERRED 0.85]
- **Product visual identity system (dark + violet isometric stack)** — ui_src_assets_hero_heroshot, ui_src_assets_hero_stacked_slabs, ui_src_assets_hero_purple_rim_lighting, ui_src_assets_hero_dark_theme_branding [INFERRED 0.95]
- **Performance Optimization Program (P0-P7)** — docs_task_performance_optimization_tickets, docs_task_ticket_p0_benchmark_harness, docs_task_ticket_p1_spacy_double_pass_elimination, docs_task_ticket_p2_thread_offload_cpu_io, docs_task_ticket_p3_db_indexes_single_transaction, docs_task_ticket_p4_lazy_model_loading, docs_task_ticket_p6_gpu_auto_detect_cpu_fallback [INFERRED]
- **Bulk Ingestion Parsing & Filtering Stack** — ingestion_reports_bulk_ingest_summary_pymupdf_parser, ingestion_reports_bulk_ingest_summary_docx_parser, ingestion_reports_bulk_ingest_summary_scanned_image_requires_ocr, ingestion_reports_bulk_ingest_summary_ai_classification_not_resume, ingestion_reports_bulk_ingest_summary_duplicate_detection [INFERRED]
- **Browser Automation Approaches for UI E2E Testing** — docs_tests_test_findings_agent_browser_subagent, docs_tests_test_findings_playwright_driver_download_failure, docs_tests_test_findings_blocked_e2e_run_aug19, docs_tests_end_to_end_ui_test_report_playwriter_direct_cdp_driver, docs_tests_end_to_end_ui_test_report_ui_test_report [INFERRED]

## Communities (80 total, 11 thin omitted)

### Community 0 - "Candidate"
Cohesion: 0.08
Nodes (47): patch, update_candidate_status(), CandidateStateMachine, InvalidStateTransition, Transitions the candidate to a new status and logs the event., TransitionContext, Any, Session (+39 more)

### Community 1 - "Python Performance Optimization - advanced reference"
Cohesion: 0.06
Nodes (52): AGENTS.md - CIP agent guidelines, Implementation rules, Keep candidate data and processing local rule, Mission: privacy-first local-first candidate intelligence, Mock heavy ML models in tests rule, Python Performance Optimization - advanced reference, Python Performance Optimization - standard reference, Pattern 10: Function Call Overhead (+44 more)

### Community 2 - "embeddings.py"
Cohesion: 0.15
Nodes (17): _check_gpu_available(), generate_embeddings(), generate_single_embedding(), _get_embedding_model(), get_embedding_model_name(), _load_text_embedding(), Any, Lazy-loaded embedding model for vector search with GPU auto-detect. Default… (+9 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.10
Nodes (32): update_candidate(), put, skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), assess_tier1(), calculate_tier1_confidence() (+24 more)

### Community 4 - "_run_pipeline_capturing_embedding"
Cohesion: 0.25
Nodes (8): Run search_candidates with mocked stores; return the embedded text., Direct DSL query: only free text reaches the embedding step., Structured API request flattened to DSL still embeds free text only., No free text at all: nothing gets embedded., _run_pipeline_capturing_embedding(), test_embedding_input_clean_for_structured_api_flatten(), test_embedding_input_excludes_filter_values(), test_pure_filter_query_skips_embedding()

### Community 5 - "resolve"
Cohesion: 0.06
Nodes (48): classify_document(), ingest_file(), IntakeProgress, IntakeResult, IntakeSource, IntakeStatus, Any, Enum (+40 more)

### Community 6 - "devDependencies"
Cohesion: 0.05
Nodes (39): autoprefixer, lucide-react, oxlint, @phosphor-icons/react, postcss, react, react-dom, react-router-dom (+31 more)

### Community 7 - "main.py"
Cohesion: 0.07
Nodes (36): health_check(), lifespan(), get, structlog_middleware(), fetch_system_logs(), get, get_engine(), Engine (+28 more)

### Community 8 - "End-to-End UI Test Report & Findings"
Cohesion: 0.06
Nodes (39): Completed Tickets (01-06), Performance Optimization Ticket Program, Task Tracker, Ticket 06: PDF Parser OCR Fallback & Final Verification, Ticket P0: Baseline & Benchmark Harness (pytest-benchmark), Ticket P1: Kill Double spaCy Pass + Truncate NER Input, Ticket P2: Thread-Offload CPU/IO + Thread-Safety Fix, Ticket P3: DB Indexes + Single-Transaction Writes + busy_timeout (+31 more)

### Community 9 - "Candidate Intelligence Platform (CIP)"
Cohesion: 0.08
Nodes (34): AST Parser Strict Filter Stage, $0-Cost Backup & Disaster Recovery, Candidate Intelligence Platform (CIP), ONNX Cross-Encoder Re-Ranker, Deterministic First Extraction (SpaCy NER + Regex), Event-Sourced Candidate Timeline Ledger, Fact vs Inference Split (candidate_claims), fastembed ONNX bge-small Embeddings (+26 more)

### Community 10 - "Bulk Ingestion CLI Script (scripts/bulk_ingest.py)"
Cohesion: 0.07
Nodes (30): Master Audit Telemetry Log (bulk_ingest_report.json), Bulk Ingestion CLI Script (scripts/bulk_ingest.py), Checkpointing & Resumption Engine, Dry-Run Simulation Mode (--dry-run), Entity Resolution Dummy Name Guard, Full-Text Search Tables (candidate_fts, claims_fts), LanceDB Vector Store, Multi-Tier Document Classifier (classify_document) (+22 more)

### Community 11 - "test_chunker.py"
Cohesion: 0.11
Nodes (36): chunk_document(), chunk_resume(), _match_section_header(), Section-aware text chunker with context injection. Public interface:…, Return the canonical section name if the line is a section header., Split raw resume text into (section_name, section_text) pairs. Lines that…, Split a resume into section-aware chunks with true section labels. The document…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4… (+28 more)

### Community 12 - "ParsedDocument"
Cohesion: 0.16
Nodes (19): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+11 more)

### Community 13 - "CandidateService"
Cohesion: 0.09
Nodes (34): CandidateService, _has_candidate_vectors_table(), Any, Session, Check for the candidate_vectors table across lancedb API variants., DBConnection, LanceModel, CandidateSectionVector (+26 more)

### Community 14 - "App.jsx"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 15 - "Environment & Tools Setup Guide (Windows)"
Cohesion: 0.15
Nodes (17): Candidate Intelligence Platform (CIP), Environment & Tools Setup Guide (Windows), Full Environment & Test Verification (pytest), Git Version Control, Ollama Binary in PATH, CPython 3.14 Windows Runtime, Windows User PATH Configuration, uv Package Manager (+9 more)

### Community 16 - "CASManager"
Cohesion: 0.11
Nodes (26): _derive_how_processed(), generate_markdown_summary(), get_file_hash(), process_single_file(), Any, Path, Map extension (+ parser-fallback warning) to the legacy how_processed label., Process a single file through the unified intake pipeline (issue #12), adapting… (+18 more)

### Community 17 - "BackupManager"
Cohesion: 0.18
Nodes (10): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, test_cas_storage_sync() (+2 more)

### Community 18 - "parse_pdf"
Cohesion: 0.19
Nodes (14): _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when…, _make_minimal_pdf(), Path (+6 more)

### Community 19 - "React + Vite Template"
Cohesion: 0.19
Nodes (16): index.html App Entry Point, Title: Candidate Intelligence Platform, /favicon.svg Asset, /src/main.jsx Module Script Entry, #root Mount Div, HMR (Hot Module Replacement), Oxc, Oxlint (+8 more)

### Community 20 - "models.py"
Cohesion: 0.20
Nodes (11): parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1. All…, Shared data model for all ingestion parsers., _make_docx(), Path, Tests for ingestion/parsers/docx_parser.py Seam under test: parse_docx(path:… (+3 more)

### Community 21 - "Exploration Gate"
Cohesion: 0.24
Nodes (10): ADR Conflict Flagging, ADRs (Architecture Decision Records), CONTEXT-MAP.md, CONTEXT.md, Domain Docs Routing, Exploration Gate, Glossary Terms Usage, /domain-modeling Skill (+2 more)

### Community 22 - "translate_reprocess_progress"
Cohesion: 0.29
Nodes (6): Canonical pipeline stages -> reprocess contracted stage names/progress., translate_reprocess_progress(), IntakeProgress, label_for_model(), Recruiter-friendly AI status messages shown in the interface. Keep every string…, Human name for a model id. 'vendor/model' ids read as Cloud AI.

### Community 23 - "icons.svg SVG symbol sprite sheet"
Cohesion: 0.50
Nodes (8): bluesky-icon symbol (Bluesky logo), Brand/social link iconography concept, discord-icon symbol (Discord logo), documentation-icon symbol (docs/code-lines icon), github-icon symbol (GitHub octocat mark), social-icon symbol (user + badge icon), icons.svg SVG symbol sprite sheet, x-icon symbol (X/Twitter logo)

### Community 24 - "gh CLI"
Cohesion: 0.38
Nodes (7): GitHub Native Issue Dependencies, gh CLI, GitHub Issue Tracker, Issue Workflow (Create/Read/List/Comment/Label/Close), PRs as Triage Surface Flag, Wayfinder Map Issue, Wayfinder Operations

### Community 25 - "Hero Image"
Cohesion: 0.53
Nodes (6): Layered Data / Storage Abstraction Motif, Landing Page Hero Section (UI), Dark-Theme Visual Branding, Hero Image, Purple Gradient Rim Lighting, Isometric Stacked Rounded-Square Slabs

### Community 26 - "runner.js"
Cohesion: 0.40
Nodes (3): fs, path, runE2ETests()

### Community 27 - "test_api_main.py"
Cohesion: 0.38
Nodes (6): TestClient, PR #25 review: failed requests keep an access record (path/status/duration)., test_404_handler(), test_cors_headers(), test_health_check(), test_unhandled_exception_still_logs_http_request()

### Community 28 - "test_api_upload_stream.py"
Cohesion: 0.47
Nodes (8): _patch_extractor(), TestClient, REVIEW band COMPLETED event carries resolution_action + matched_candidate_id…, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume(), test_upload_stream_non_resume_rejected(), test_upload_stream_review_exposes_duplicate_hint_fields(), test_upload_stream_transparency_events()

### Community 29 - "App Favicon (Purple Lightning Bolt)"
Cohesion: 0.50
Nodes (5): App Favicon (Purple Lightning Bolt), Lightning Bolt Glyph, Glow Ellipses + Alpha Mask Layer, Purple Brand Palette (#863bff / #7e14ff / #ede6ff), CIP Web UI Brand Identity

### Community 31 - "test_logging.py"
Cohesion: 0.08
Nodes (55): console_renderer(), _DynamicStdoutLogger, _enable_windows_ansi(), _fallback_phrase(), get_recent_logs(), _gpu_detail(), is_polling_path(), json_renderer() (+47 more)

### Community 33 - "ingest_file"
Cohesion: 0.06
Nodes (85): _acquire_cas_ref(), _bind_release_on_commit(), _build_audit_criteria(), classify_document(), _emit(), _has_committed_reference(), ingest_file(), IntakeProgress (+77 more)

### Community 34 - "Vite Logo"
Cohesion: 0.67
Nodes (3): Boilerplate Template Asset, Vite Framework, Vite Logo

### Community 56 - "routes/search.py"
Cohesion: 0.15
Nodes (27): _ai_explanation_warning(), _build_search_query(), _build_structured_filter_suffix(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), _prepare_query() (+19 more)

### Community 57 - "resolve_chat_model"
Cohesion: 0.12
Nodes (22): chat_retry_candidates(), _installed_ollama_model_names(), normalize_model_name(), Return an available chat model name, or None when none is usable., Clear the cached resolution (used by tests)., Strip the tag suffix so 'llama3.2' matches 'llama3.2:latest'., Ordered chat models to try after the primary fails., Return normalized names of models installed in the local Ollama instance. (+14 more)

### Community 58 - "job_ad_distiller.py"
Cohesion: 0.10
Nodes (35): _ai_distill(), _ai_distill_ollama(), _ai_distill_openrouter(), build_search_dsl(), _build_summary(), _coerce_recipe(), distill_job_ad(), _extract_title_phrase() (+27 more)

### Community 59 - "test_model_fallbacks.py"
Cohesion: 0.16
Nodes (9): clean_model_env(), fixture, Reset lazy-loaded model singletons so every test starts fresh., Stands in for the module-level structlog logger (which may already be cached-…, reset_lazy_model_globals(), SentinelModel, SpyLogger, test_invalid_embedding_model_falls_back_to_default_with_warning() (+1 more)

### Community 60 - "test_search_engine.py"
Cohesion: 0.16
Nodes (16): parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently…, rrf_k / weights / rerank_pool_size come from settings with env overrides., _run_pipeline(), test_fetch_candidate_documents_empty(), test_hybrid_search_candidates(), test_hybrid_search_candidates_applies_tuning_knobs(), test_keyword_only_query_orders_by_bm25() (+8 more)

### Community 61 - "Session"
Cohesion: 0.21
Nodes (18): batch_delete_candidates(), batch_reprocess_candidate_stream(), get_candidate(), get_candidate_file(), get_candidate_insight(), get_candidate_timeline(), list_candidates(), Any (+10 more)

### Community 62 - "search_candidates"
Cohesion: 0.24
Nodes (15): _describe_strict_filters(), execute_fts_query(), execute_strict_filter_query(), fetch_candidate_documents(), _keyword_hits(), Any, Session, Turn parsed query filter params into scorecard descriptors. (+7 more)

### Community 63 - "build_match_rationale"
Cohesion: 0.31
Nodes (11): build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, _params(), Tests for candidate_intelligence_platform/intelligence/explainer.py Focus…, test_extreme_rerank_score_does_not_crash_or_default_to_50(), test_missing_rerank_score_derives_percentage_from_rrf(), test_missing_rerank_score_never_fabricates_50_percent() (+3 more)

### Community 64 - "reranker.py"
Cohesion: 0.27
Nodes (9): _check_gpu_available(), _get_reranker(), get_reranker_model_name(), _load_text_cross_encoder(), Any, Lazy-loaded cross-encoder reranker for search results with GPU auto-detect.…, Check if GPU (CUDA) is available for acceleration., Lazy-load the cross-encoder model on first use (thread-safe). Loads the… (+1 more)

### Community 65 - "conftest.py"
Cohesion: 0.13
Nodes (22): get_db(), _get_sessionmaker(), get_settings(), get_vector_db(), Session, client(), db_engine(), db_session() (+14 more)

### Community 66 - "test_api_insight_fallback.py"
Cohesion: 0.40
Nodes (10): candidate_id(), _parse_events(), fixture, Session, TestClient, _stream_insight(), test_insight_emits_visible_message_when_no_chat_model(), test_insight_invalid_model_retries_fallback_before_giving_up() (+2 more)

### Community 68 - "execute_vector_search"
Cohesion: 0.20
Nodes (10): execute_vector_search(), Execute vector search., candidate restriction is applied inside the vector store before the limit., No keyword matches means no restriction: global search unchanged., Real LanceDB store: filtered candidate must survive even when it falls outside…, test_execute_vector_search_missing_table(), test_execute_vector_search_no_restriction_for_pure_semantic(), test_execute_vector_search_prefilter_end_to_end() (+2 more)

### Community 69 - "Search Accuracy Evaluation Harness"
Cohesion: 0.22
Nodes (8): Design, Goal, Golden set, Metrics, Problem, Regression gate, Search Accuracy Evaluation Harness, Success criteria

### Community 70 - "Architecture Deepening Opportunities"
Cohesion: 0.25
Nodes (7): 1. Resume intake pipeline copied 4 times — and the copies disagree, 2. Search has a weird round-trip that loses information, 3. Database housekeeping knowledge scattered across 7+ files, 4. Name/email extractor exports its internals and has no test seam, 5. CandidateService — shallow helper that would dissolve into the deepened modules, Architecture Deepening Opportunities, Recommendation

### Community 72 - "Anti-AI Pattern Findings (Whole UI Scan)"
Cohesion: 0.29
Nodes (6): 1. Hallmark Audit, 2. Design-Taste-Frontend Audit, 3. Impeccable Critique & Layout Structure, 4. Humanise-Text Review (docs + UI copy), 5. Implementation Agent Prompt, Anti-AI Pattern Findings (Whole UI Scan)

### Community 74 - "reciprocal_rank_fusion"
Cohesion: 0.40
Nodes (4): Computes weighted Reciprocal Rank Fusion (RRF) for two sets of candidate ranks.…, reciprocal_rank_fusion(), test_reciprocal_rank_fusion(), test_reciprocal_rank_fusion_weights()

### Community 77 - "routes/candidates.py"
Cohesion: 0.29
Nodes (11): delete_candidate(), BatchCandidateIds, BatchReprocessRequest, CandidateBase, CandidateCreate, CandidateResponse, CandidateStatusUpdate, CandidateUpdate (+3 more)

### Community 78 - "Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier)"
Cohesion: 0.25
Nodes (7): Current Ollama Usage Points, Decision, Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier), Implementation Requirements, Problem Statement, Proposed Change, Risks

### Community 79 - "Centralized AI Prompts"
Cohesion: 0.29
Nodes (6): Benefits, Centralized AI Prompts, Goal, Open questions, Problem, Sketch

### Community 80 - "Settings"
Cohesion: 0.12
Nodes (24): stream_openrouter_generate(), BaseSettings, Settings, RuntimeError, _call_ollama(), _call_openrouter(), Call OpenRouter API for inference. Never calls paid models., Call local Ollama for inference. (+16 more)

### Community 83 - "extract_inferences"
Cohesion: 0.16
Nodes (12): ollama, extract_inferences(), Extract AI inferences from text using a local LLM via Ollama or remote via…, Test when LLM returns null claim_value and entity in claim_key., test_llm_claim_value_null_logs_warning_and_repairs(), test_llm_extraction_failure_logs_ai_warning(), test_vector_search_failure_logs_ai_warning(), Live integration test against running Ollama instance. (+4 more)

### Community 84 - "test_ingestion_concurrency.py"
Cohesion: 0.38
Nodes (6): concurrency_env(), make_engine(), Any, fixture, Regression: parallel ingest_file must not fail with 'database is locked'.…, Same pragma set as config.database.get_engine but short busy_timeout.

## Ambiguous Edges - Review These
- `SQLite WAL RDBMS + FTS5` → `SQLAlchemy 2.0 Mapped Refactor of db_models.py`  [AMBIGUOUS]
  docs/chats/trae-chat.md · relation: conceptually_related_to
- `Local-First Execution` → `Traditional Keyword Search Limits`  [AMBIGUOUS]
  docs/how_candidate_intelligence_works.html · relation: conceptually_related_to
- `Document Parsers (PDF, DOCX, Email)` → `Mock heavy ML models in tests rule`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to
- `Workflow Step 5: Verify` → `pytest test suite`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to
- `Implementation rules` → `Decision rules: profile before optimizing, preserve behavior`  [AMBIGUOUS]
  AGENTS.md · relation: conceptually_related_to
- `Per-Candidate Insight SSE Endpoint (/candidates/{id}/insight)` → `Thread-Offload CPU/IO + Bounded Upload Semaphore`  [AMBIGUOUS]
  docs/ideas/async-ai-insights.md · relation: conceptually_related_to
- `Oxlint` → `@vitejs/plugin-react`  [AMBIGUOUS]
  ui/README.md · relation: conceptually_related_to
- `React + Vite Template` → `Title: Candidate Intelligence Platform`  [AMBIGUOUS]
  ui/index.html · relation: semantically_similar_to
- `bluesky-icon symbol (Bluesky logo)` → `x-icon symbol (X/Twitter logo)`  [AMBIGUOUS]
  ui/public/icons.svg · relation: semantically_similar_to
- `discord-icon symbol (Discord logo)` → `github-icon symbol (GitHub octocat mark)`  [AMBIGUOUS]
  ui/public/icons.svg · relation: semantically_similar_to

## Knowledge Gaps
- **106 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `SentinelModel`, `$schema` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `SQLite WAL RDBMS + FTS5` and `SQLAlchemy 2.0 Mapped Refactor of db_models.py`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Local-First Execution` and `Traditional Keyword Search Limits`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Document Parsers (PDF, DOCX, Email)` and `Mock heavy ML models in tests rule`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Workflow Step 5: Verify` and `pytest test suite`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Implementation rules` and `Decision rules: profile before optimizing, preserve behavior`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Per-Candidate Insight SSE Endpoint (/candidates/{id}/insight)` and `Thread-Offload CPU/IO + Bounded Upload Semaphore`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Oxlint` and `@vitejs/plugin-react`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._