# Graph Report - Candidate_Intelligence_Platform  (2026-08-25)

## Corpus Check
- 136 files · ~76,868 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1261 nodes · 2543 edges · 91 communities (79 shown, 12 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 396 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4987e3bd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- routes/candidates.py
- Python Performance Optimization - advanced reference
- .update_vector_index
- extract_candidate_profile_hybrid
- Candidate
- resolve
- devDependencies
- is_polling_path
- End-to-End UI Test Report & Findings
- Candidate Intelligence Platform (CIP)
- Bulk Ingestion CLI Script (scripts/bulk_ingest.py)
- test_chunker.py
- ParsedDocument
- embeddings.py
- App.jsx
- Environment & Tools Setup Guide (Windows)
- CASManager
- BackupManager
- parse_pdf
- React + Vite Template
- models.py
- Exploration Gate
- logging.py
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
- get_recent_logs
- search_candidates
- build_match_rationale
- reranker.py
- conftest.py
- test_api_insight_fallback.py
- setup_logging
- execute_vector_search
- Async AI Candidate Insights
- main.py
- schemas/candidates.py
- Search Accuracy Evaluation Harness
- Settings
- reciprocal_rank_fusion
- Architecture Deepening Opportunities
- Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier)
- test_api_search_stream.py
- Deferred T5: Parallel Batch Upload Thread Pool
- extract_inferences
- DB FK Indexes + Single-Transaction Writes (busy_timeout=5000)
- translate_reprocess_progress
- Idea: Autonomous Agentic Retrieval System
- Centralized AI Prompts
- Task Tracker
- test_prompts.py
- End-to-End Test Findings
- isolate_llm_environment
- test_ai_failure_logging.py
- test_live_ollama_extraction

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 74 edges
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
- `test_llm_extraction_failure_logs_ai_warning()` --calls--> `extract_inferences()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/extraction/local_llm_fallback.py
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `test_fetch_candidate_documents_empty()` --calls--> `fetch_candidate_documents()`  [INFERRED]
  tests/test_search_engine.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `Mission: privacy-first local-first candidate intelligence` --semantically_similar_to--> `Privacy-first local-first principle`  [INFERRED] [semantically similar]
  AGENTS.md → README.md
- `test_unhandled_exception_still_logs_http_request()` --indirect_call--> `get_db()`  [INFERRED]
  tests/test_api_main.py → api/dependencies.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **CIP Ingestion Dedup Flow** — docs_how_candidate_intelligence_works_sha256_fingerprinting_dedup, docs_architecture_design_document_immutable_evidence_cas, docs_architecture_design_document_multi_stage_parsers, docs_architecture_design_document_two_tier_entity_resolution [EXTRACTED 0.95]
- **Wayfinding Ticket Lifecycle** — docs_agents_issue_tracker_wayfinder_map_issue, docs_agents_issue_tracker_blocking_dependencies, docs_agents_issue_tracker_gh_cli [EXTRACTED 0.95]
- **CIP Hybrid Search Pipeline Flow** — docs_architecture_design_document_ast_parser_stage, docs_architecture_design_document_hybrid_search_rrf, docs_architecture_design_document_cross_encoder_reranker, docs_architecture_design_document_match_rationale_explainer [EXTRACTED 1.00]
- **Five-step performance optimization workflow** — agents_skills_python_performance_optimization_skill_workflow_measure, agents_skills_python_performance_optimization_skill_workflow_profile, agents_skills_python_performance_optimization_skill_workflow_choose, agents_skills_python_performance_optimization_skill_workflow_change, agents_skills_python_performance_optimization_skill_workflow_verify [EXTRACTED 1.00]
- **CIP ingestion-to-retrieval pipeline** — readme_content_addressable_store, readme_document_parsers, readme_section_aware_chunker, readme_entity_resolution_engine, readme_sqlite_wal_database, readme_lancedb_vector_store, readme_fastapi_rest_backend, readme_react_tailwind_ui [EXTRACTED 1.00]
- **Measure-before-and-after optimization workflow** — agents_skills_python_performance_optimization_references_advanced_patterns, references_advanced_custom_benchmark_decorator, references_advanced_pytest_benchmark_testing [INFERRED 0.85]
- **Product visual identity system (dark + violet isometric stack)** — ui_src_assets_hero_heroshot, ui_src_assets_hero_stacked_slabs, ui_src_assets_hero_purple_rim_lighting, ui_src_assets_hero_dark_theme_branding [INFERRED 0.95]
- **Bulk Ingestion Parsing & Filtering Stack** — ingestion_reports_bulk_ingest_summary_pymupdf_parser, ingestion_reports_bulk_ingest_summary_docx_parser, ingestion_reports_bulk_ingest_summary_scanned_image_requires_ocr, ingestion_reports_bulk_ingest_summary_ai_classification_not_resume, ingestion_reports_bulk_ingest_summary_duplicate_detection [INFERRED]

## Communities (91 total, 12 thin omitted)

### Community 0 - "routes/candidates.py"
Cohesion: 0.18
Nodes (23): _get_sessionmaker(), batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_insight(), get_candidate_timeline() (+15 more)

### Community 1 - "Python Performance Optimization - advanced reference"
Cohesion: 0.06
Nodes (52): AGENTS.md - CIP agent guidelines, Implementation rules, Keep candidate data and processing local rule, Mission: privacy-first local-first candidate intelligence, Mock heavy ML models in tests rule, Python Performance Optimization - advanced reference, Python Performance Optimization - standard reference, Pattern 10: Function Call Overhead (+44 more)

### Community 2 - ".update_vector_index"
Cohesion: 0.08
Nodes (33): _has_candidate_vectors_table(), Any, Session, Check for the candidate_vectors table across lancedb API variants., DBConnection, LanceModel, CandidateSectionVector, get_lancedb_connection() (+25 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.10
Nodes (32): update_candidate(), put, skipif, extract_facts(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), assess_tier1(), calculate_tier1_confidence() (+24 more)

### Community 4 - "Candidate"
Cohesion: 0.06
Nodes (67): patch, update_candidate_status(), CandidateService, CandidateStateMachine, InvalidStateTransition, Transitions the candidate to a new status and logs the event., TransitionContext, Any (+59 more)

### Community 5 - "resolve"
Cohesion: 0.10
Nodes (27): CandidateIdentifiers, _normalize(), Enum, ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2() (+19 more)

### Community 6 - "devDependencies"
Cohesion: 0.05
Nodes (39): autoprefixer, lucide-react, oxlint, @phosphor-icons/react, postcss, react, react-dom, react-router-dom (+31 more)

### Community 7 - "is_polling_path"
Cohesion: 0.40
Nodes (5): structlog_middleware(), is_polling_path(), middleware, Request, test_is_polling_path()

### Community 8 - "End-to-End UI Test Report & Findings"
Cohesion: 0.09
Nodes (23): UX Recommendation: Autosave Timestamp Display, E2E-05: Candidate Detail View & Autosave, UX Recommendation: Candidate List Auto-Refresh on Route Return (fetchCandidates), E2E-01: Initial Page Load & Shell, E2E-06: Multi-Select & Batch Actions, Playwriter Direct CDP Automation Driver (Chrome 151, port 9222), E2E-03: SSE Resume Upload & Ingestion Workflow with Deduplication, UX Recommendation: Search Input Clear Icon (+15 more)

### Community 9 - "Candidate Intelligence Platform (CIP)"
Cohesion: 0.08
Nodes (34): AST Parser Strict Filter Stage, $0-Cost Backup & Disaster Recovery, Candidate Intelligence Platform (CIP), ONNX Cross-Encoder Re-Ranker, Deterministic First Extraction (SpaCy NER + Regex), Event-Sourced Candidate Timeline Ledger, Fact vs Inference Split (candidate_claims), fastembed ONNX bge-small Embeddings (+26 more)

### Community 10 - "Bulk Ingestion CLI Script (scripts/bulk_ingest.py)"
Cohesion: 0.13
Nodes (15): Master Audit Telemetry Log (bulk_ingest_report.json), Bulk Ingestion CLI Script (scripts/bulk_ingest.py), Checkpointing & Resumption Engine, Dry-Run Simulation Mode (--dry-run), Entity Resolution Dummy Name Guard, Full-Text Search Tables (candidate_fts, claims_fts), LanceDB Vector Store, Multi-Tier Document Classifier (classify_document) (+7 more)

### Community 11 - "test_chunker.py"
Cohesion: 0.11
Nodes (36): chunk_document(), chunk_resume(), _match_section_header(), Section-aware text chunker with context injection. Public interface:…, Return the canonical section name if the line is a section header., Split raw resume text into (section_name, section_text) pairs. Lines that…, Split a resume into section-aware chunks with true section labels. The document…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4… (+28 more)

### Community 12 - "ParsedDocument"
Cohesion: 0.16
Nodes (19): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+11 more)

### Community 13 - "embeddings.py"
Cohesion: 0.15
Nodes (17): _check_gpu_available(), generate_embeddings(), generate_single_embedding(), _get_embedding_model(), get_embedding_model_name(), _load_text_embedding(), Any, Lazy-loaded embedding model for vector search with GPU auto-detect. Default… (+9 more)

### Community 14 - "App.jsx"
Cohesion: 0.16
Nodes (12): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+4 more)

### Community 15 - "Environment & Tools Setup Guide (Windows)"
Cohesion: 0.15
Nodes (17): Candidate Intelligence Platform (CIP), Environment & Tools Setup Guide (Windows), Full Environment & Test Verification (pytest), Git Version Control, Ollama Binary in PATH, CPython 3.14 Windows Runtime, Windows User PATH Configuration, uv Package Manager (+9 more)

### Community 16 - "CASManager"
Cohesion: 0.06
Nodes (47): classify_document(), ingest_file(), IntakeProgress, IntakeResult, IntakeSource, IntakeStatus, Any, Enum (+39 more)

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

### Community 22 - "logging.py"
Cohesion: 0.37
Nodes (17): console_renderer(), _fallback_phrase(), _gpu_detail(), json_renderer(), _local_time(), _model_device_detail(), _paint(), _render_block() (+9 more)

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
Cohesion: 0.18
Nodes (20): _resolve_format(), PR #25 review: /logs buffer drops PII; the console card keeps it., _render(), test_buffer_redacts_candidate_identity_but_console_keeps_it(), test_console_batch_delete_block(), test_console_duplicate_skip_block(), test_console_failed_upload_block(), test_console_gpu_unavailable_providers() (+12 more)

### Community 33 - "ingest_file"
Cohesion: 0.07
Nodes (81): _acquire_cas_ref(), _bind_release_on_commit(), _build_audit_criteria(), classify_document(), _emit(), _has_committed_reference(), ingest_file(), IntakeResult (+73 more)

### Community 34 - "Vite Logo"
Cohesion: 0.67
Nodes (3): Boilerplate Template Asset, Vite Framework, Vite Logo

### Community 56 - "routes/search.py"
Cohesion: 0.15
Nodes (27): _ai_explanation_warning(), _build_search_query(), _build_structured_filter_suffix(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), _prepare_query() (+19 more)

### Community 57 - "resolve_chat_model"
Cohesion: 0.13
Nodes (22): chat_retry_candidates(), _installed_ollama_model_names(), normalize_model_name(), Return an available chat model name, or None when none is usable., Clear the cached resolution (used by tests)., Strip the tag suffix so 'llama3.2' matches 'llama3.2:latest'., Ordered chat models to try after the primary fails., Return normalized names of models installed in the local Ollama instance. (+14 more)

### Community 58 - "job_ad_distiller.py"
Cohesion: 0.09
Nodes (38): build_job_ad_distill_prompt(), Job-ad parsing prompt for the given (already truncated) advertisement text., _ai_distill(), _ai_distill_ollama(), _ai_distill_openrouter(), build_search_dsl(), _build_summary(), _coerce_recipe() (+30 more)

### Community 59 - "test_model_fallbacks.py"
Cohesion: 0.16
Nodes (9): clean_model_env(), fixture, Reset lazy-loaded model singletons so every test starts fresh., Stands in for the module-level structlog logger (which may already be cached-…, reset_lazy_model_globals(), SentinelModel, SpyLogger, test_invalid_embedding_model_falls_back_to_default_with_warning() (+1 more)

### Community 60 - "test_search_engine.py"
Cohesion: 0.11
Nodes (24): parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently…, rrf_k / weights / rerank_pool_size come from settings with env overrides., Run search_candidates with mocked stores; return the embedded text., Direct DSL query: only free text reaches the embedding step., Structured API request flattened to DSL still embeds free text only., No free text at all: nothing gets embedded., _run_pipeline() (+16 more)

### Community 61 - "get_recent_logs"
Cohesion: 0.20
Nodes (10): fetch_system_logs(), get, get_recent_logs(), memory_buffer_processor(), Any, test_get_recent_logs_truncation(), test_memory_buffer_processor(), TestClient (+2 more)

### Community 62 - "search_candidates"
Cohesion: 0.32
Nodes (12): _describe_strict_filters(), execute_fts_query(), execute_strict_filter_query(), fetch_candidate_documents(), _keyword_hits(), Any, Session, Turn parsed query filter params into scorecard descriptors. (+4 more)

### Community 63 - "build_match_rationale"
Cohesion: 0.31
Nodes (11): build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, _params(), Tests for candidate_intelligence_platform/intelligence/explainer.py Focus…, test_extreme_rerank_score_does_not_crash_or_default_to_50(), test_missing_rerank_score_derives_percentage_from_rrf(), test_missing_rerank_score_never_fabricates_50_percent() (+3 more)

### Community 64 - "reranker.py"
Cohesion: 0.21
Nodes (12): _check_gpu_available(), _get_reranker(), get_reranker_model_name(), _load_text_cross_encoder(), Any, Lazy-loaded cross-encoder reranker for search results with GPU auto-detect.…, Reranks a list of documents based on a query using a cross-encoder model.…, Check if GPU (CUDA) is available for acceleration. (+4 more)

### Community 65 - "conftest.py"
Cohesion: 0.13
Nodes (21): get_db(), get_settings(), get_vector_db(), Session, client(), db_engine(), db_session(), isolate_test_environment() (+13 more)

### Community 66 - "test_api_insight_fallback.py"
Cohesion: 0.40
Nodes (10): candidate_id(), _parse_events(), fixture, Session, TestClient, _stream_insight(), test_insight_emits_visible_message_when_no_chat_model(), test_insight_invalid_model_retries_fallback_before_giving_up() (+2 more)

### Community 67 - "setup_logging"
Cohesion: 0.20
Nodes (8): _DynamicStdoutLogger, _enable_windows_ansi(), setup_logging(), UvicornAccessFilter, LogRecord, test_setup_logging_configures_structlog(), test_setup_logging_json_mode_renders_parseable_json(), test_uvicorn_access_filter_silences_all_access_lines()

### Community 68 - "execute_vector_search"
Cohesion: 0.20
Nodes (10): execute_vector_search(), Execute vector search., candidate restriction is applied inside the vector store before the limit., No keyword matches means no restriction: global search unchanged., Real LanceDB store: filtered candidate must survive even when it falls outside…, test_execute_vector_search_missing_table(), test_execute_vector_search_no_restriction_for_pure_semantic(), test_execute_vector_search_prefilter_end_to_end() (+2 more)

### Community 69 - "Async AI Candidate Insights"
Cohesion: 0.18
Nodes (10): 1. API & Transport Design, 2. Cancellation Lifecycle, Architecture & Technical Decisions, Async AI Candidate Insights, CRITICAL: IMPLEMENTATION SKILLS TO USE, Key Assumptions to Validate, MVP Scope, Not Doing (and Why) (+2 more)

### Community 70 - "main.py"
Cohesion: 0.16
Nodes (15): health_check(), lifespan(), get, get_engine(), Engine, Create a SQLAlchemy engine configured for SQLite with WAL mode., FastAPI, init_db() (+7 more)

### Community 71 - "schemas/candidates.py"
Cohesion: 0.36
Nodes (9): BatchCandidateIds, BatchReprocessRequest, CandidateBase, CandidateCreate, CandidateResponse, CandidateStatusUpdate, CandidateUpdate, BaseModel (+1 more)

### Community 72 - "Search Accuracy Evaluation Harness"
Cohesion: 0.22
Nodes (8): Design, Goal, Golden set, Metrics, Problem, Regression gate, Search Accuracy Evaluation Harness, Success criteria

### Community 73 - "Settings"
Cohesion: 0.32
Nodes (7): BaseSettings, Settings, clean_model_env(), fixture, Verify that default settings conform to the architectural directives., test_default_settings(), test_model_and_tuning_settings_support_env_overrides()

### Community 74 - "reciprocal_rank_fusion"
Cohesion: 0.40
Nodes (4): Computes weighted Reciprocal Rank Fusion (RRF) for two sets of candidate ranks.…, reciprocal_rank_fusion(), test_reciprocal_rank_fusion(), test_reciprocal_rank_fusion_weights()

### Community 75 - "Architecture Deepening Opportunities"
Cohesion: 0.25
Nodes (7): 1. Resume intake pipeline copied 4 times — and the copies disagree, 2. Search has a weird round-trip that loses information, 3. Database housekeeping knowledge scattered across 7+ files, 4. Name/email extractor exports its internals and has no test seam, 5. CandidateService — shallow helper that would dissolve into the deepened modules, Architecture Deepening Opportunities, Recommendation

### Community 77 - "Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier)"
Cohesion: 0.25
Nodes (7): Current Ollama Usage Points, Decision, Idea: Switch LLM Backend to OpenRouter OX Alpha (Free Tier), Implementation Requirements, Problem Statement, Proposed Change, Risks

### Community 78 - "test_api_search_stream.py"
Cohesion: 0.40
Nodes (5): TestClient, Test that the search stream yields the expected stage events., Test that the POST /search/stream endpoint exists and accepts valid requests., test_search_stream_emits_progress_events(), test_search_stream_endpoint_exists()

### Community 80 - "extract_inferences"
Cohesion: 0.12
Nodes (22): stream_openrouter_generate(), RuntimeError, _call_ollama(), _call_openrouter(), extract_inferences(), Call OpenRouter API for inference. Never calls paid models., Call local Ollama for inference., Extract AI inferences from text using a local LLM via Ollama or remote via… (+14 more)

### Community 82 - "translate_reprocess_progress"
Cohesion: 0.29
Nodes (6): Canonical pipeline stages -> reprocess contracted stage names/progress., translate_reprocess_progress(), IntakeProgress, label_for_model(), Recruiter-friendly AI status messages shown in the interface. Keep every string…, Human name for a model id. 'vendor/model' ids read as Cloud AI.

### Community 83 - "Idea: Autonomous Agentic Retrieval System"
Cohesion: 0.29
Nodes (6): Idea: Autonomous Agentic Retrieval System, Key Assumptions to Validate, MVP Scope, Not doing (and why), Problem Statement, Recommended Direction

### Community 84 - "Centralized AI Prompts"
Cohesion: 0.29
Nodes (6): Benefits, Centralized AI Prompts, Goal, Open questions, Problem, Sketch

### Community 85 - "Task Tracker"
Cohesion: 0.29
Nodes (6): Centralized AI Prompts (Issue #24), Completed Tickets, Performance Optimization Tickets, Soft Search Filters (Issue #36), Task Tracker, Unified Intake Pipeline (Issue #12)

### Community 86 - "test_prompts.py"
Cohesion: 0.33
Nodes (6): build_match_insight_prompt(), Match-rationale prompt for the given resume text and search query., Guard tests: prompts moved into candidate_intelligence_platform.prompts must…, test_fact_extraction_prompt_is_byte_identical(), test_match_insight_prompt_is_byte_identical(), test_match_insight_prompt_tolerates_braces_in_inputs()

### Community 87 - "End-to-End Test Findings"
Cohesion: 0.40
Nodes (4): Bug / Blocker, E2E Run: August 19, 2026, End-to-End Test Findings, System Configuration

### Community 88 - "isolate_llm_environment"
Cohesion: 0.40
Nodes (5): MonkeyPatch, Clear cached pricing verdicts (used by tests)., reset_openrouter_pricing_cache(), isolate_llm_environment(), Ensure all tests default to offline Ollama, avoiding OpenRouter network calls.

### Community 89 - "test_ai_failure_logging.py"
Cohesion: 0.40
Nodes (4): Test when LLM returns null claim_value and entity in claim_key., test_llm_claim_value_null_logs_warning_and_repairs(), test_llm_extraction_failure_logs_ai_warning(), test_vector_search_failure_logs_ai_warning()

### Community 90 - "test_live_ollama_extraction"
Cohesion: 0.50
Nodes (3): ollama, Live integration test against running Ollama instance., test_live_ollama_extraction()

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
- `Oxlint` → `@vitejs/plugin-react`  [AMBIGUOUS]
  ui/README.md · relation: conceptually_related_to
- `React + Vite Template` → `Title: Candidate Intelligence Platform`  [AMBIGUOUS]
  ui/index.html · relation: semantically_similar_to
- `bluesky-icon symbol (Bluesky logo)` → `x-icon symbol (X/Twitter logo)`  [AMBIGUOUS]
  ui/public/icons.svg · relation: semantically_similar_to
- `discord-icon symbol (Discord logo)` → `github-icon symbol (GitHub octocat mark)`  [AMBIGUOUS]
  ui/public/icons.svg · relation: semantically_similar_to

## Knowledge Gaps
- **119 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `SentinelModel`, `$schema` (+114 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

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
- **What is the exact relationship between `Oxlint` and `@vitejs/plugin-react`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `React + Vite Template` and `Title: Candidate Intelligence Platform`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._