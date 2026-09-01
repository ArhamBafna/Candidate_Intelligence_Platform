# Graph Report - Candidate_Intelligence_Platform  (2026-09-01)

## Corpus Check
- 135 files · ~79,403 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1372 nodes · 2746 edges · 93 communities (80 shown, 13 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 412 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `86d4ee92`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MockVectorStore
- Python Performance Optimization - advanced reference
- get_db
- extract_candidate_profile_hybrid
- Candidate
- resolve
- devDependencies
- intake.py
- End-to-End UI Test Report & Findings
- Candidate Intelligence Platform (CIP)
- Bulk Ingestion CLI Script (scripts/bulk_ingest.py)
- test_chunker.py
- parse_email
- BackupManager
- App.jsx
- Environment & Tools Setup Guide (Windows)
- bulk_ingest.py
- routes/search.py
- ParsedDocument
- React + Vite Template
- parse_docx
- Exploration Gate
- intake_module_sketch.py
- icons.svg SVG symbol sprite sheet
- gh CLI
- Hero Image
- runner.js
- CandidateSectionVector
- test_api_upload_stream.py
- App Favicon (Purple Lightning Bolt)
- test_get_logs_endpoint_returns_recent_events
- test_logging.py
- StorageIndexWriter
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
- generate_embeddings
- resolve_chat_model
- job_ad_distiller.py
- test_model_fallbacks.py
- test_search_engine.py
- 2. Open-Source Landscape & Library Evaluation
- search_candidates
- build_match_rationale
- reranker.py
- conftest.py
- test_api_insight_fallback.py
- _run_pipeline_capturing_embedding
- execute_vector_search
- Specification: Robust Multi-Stage Anchored Candidate Name Extraction
- Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction
- Display Extracted Skills in Candidate Profile UI
- reciprocal_rank_fusion
- 3. Detailed Technical Specification
- Deferred T5: Parallel Batch Upload Thread Pool
- local_llm_fallback.py
- DB FK Indexes + Single-Transaction Writes (busy_timeout=5000)
- Task Tracker
- prompts.py
- End-to-End Test Findings
- test_job_ad_distiller.py
- extract_inferences
- CASManager
- test_search_ai_availability.py
- mock_extraction
- RuntimeError
- classify_document
- test_parse_query_to_sql
- test_ui_duplicate_chip_wired
- Session Handoff — 2026-08-27
- Settings
- main.py

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 80 edges
2. `ingest_file()` - 59 edges
3. `Settings` - 44 edges
4. `get_settings()` - 36 edges
5. `IntakeStatus` - 34 edges
6. `IntakeSource` - 34 edges
7. `TimelineMode` - 32 edges
8. `StorageIndexWriter` - 32 edges
9. `ResumeVersion` - 31 edges
10. `CASManager` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_vector_search_failure_logs_ai_warning()` --calls--> `execute_vector_search()`  [INFERRED]
  tests/test_ai_failure_logging.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `test_fetch_candidate_documents_empty()` --calls--> `fetch_candidate_documents()`  [INFERRED]
  tests/test_search_engine.py → src/candidate_intelligence_platform/search/hybrid_searcher.py
- `test_recipe_metadata_shape()` --uses--> `JobAdRecipe`  [INFERRED]
  tests/test_job_ad_distiller.py → src/candidate_intelligence_platform/search/job_ad_distiller.py
- `test_ai_garbage_json_falls_back_to_heuristics()` --calls--> `distill_job_ad()`  [INFERRED]
  tests/test_job_ad_distiller.py → src/candidate_intelligence_platform/search/job_ad_distiller.py
- `test_ai_unavailable_uses_non_ai_extraction()` --calls--> `distill_job_ad()`  [INFERRED]
  tests/test_job_ad_distiller.py → src/candidate_intelligence_platform/search/job_ad_distiller.py

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

## Communities (93 total, 13 thin omitted)

### Community 0 - "MockVectorStore"
Cohesion: 0.16
Nodes (9): MockVectorStore, Mock LanceDB vector store connection for isolated test runs., concurrency_env(), make_engine(), Any, fixture, Regression: parallel ingest_file must not fail with 'database is locked'.…, Same pragma set as config.database.get_engine but short busy_timeout. (+1 more)

### Community 1 - "Python Performance Optimization - advanced reference"
Cohesion: 0.06
Nodes (52): AGENTS.md - CIP agent guidelines, Implementation rules, Keep candidate data and processing local rule, Mission: privacy-first local-first candidate intelligence, Mock heavy ML models in tests rule, Python Performance Optimization - advanced reference, Python Performance Optimization - standard reference, Pattern 10: Function Call Overhead (+44 more)

### Community 2 - "get_db"
Cohesion: 0.27
Nodes (9): get_db(), Session, TestClient, PR #25 review: failed requests keep an access record (path/status/duration)., test_404_handler(), test_cors_headers(), test_health_check(), test_unhandled_exception_still_logs_http_request() (+1 more)

### Community 3 - "extract_candidate_profile_hybrid"
Cohesion: 0.07
Nodes (41): update_candidate(), put, skipif, extract_facts(), get_nlp(), Extract deterministic facts (emails, phones, locations, names, skills) from…, _apply_llm_fallback(), assess_tier1() (+33 more)

### Community 4 - "Candidate"
Cohesion: 0.05
Nodes (90): _get_sessionmaker(), batch_delete_candidates(), batch_reprocess_candidate_stream(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_insight(), get_candidate_timeline() (+82 more)

### Community 5 - "resolve"
Cohesion: 0.10
Nodes (25): CandidateIdentifiers, _normalize(), ResolutionResult, resolve(), _resolve_tier_1(), _resolve_tier_2(), similarity_score(), _make() (+17 more)

### Community 6 - "devDependencies"
Cohesion: 0.05
Nodes (43): autoprefixer, lucide-react, oxlint, @phosphor-icons/react, postcss, react, react-dom, react-markdown (+35 more)

### Community 7 - "intake.py"
Cohesion: 0.11
Nodes (27): _acquire_cas_ref(), _bind_release_on_commit(), _build_audit_criteria(), _emit(), _has_committed_reference(), IntakeProgress, IntakeResult, _is_dummy_profile() (+19 more)

### Community 8 - "End-to-End UI Test Report & Findings"
Cohesion: 0.14
Nodes (14): UX Recommendation: Autosave Timestamp Display, E2E-05: Candidate Detail View & Autosave, UX Recommendation: Candidate List Auto-Refresh on Route Return (fetchCandidates), E2E-01: Initial Page Load & Shell, E2E-06: Multi-Select & Batch Actions, Playwriter Direct CDP Automation Driver (Chrome 151, port 9222), E2E-03: SSE Resume Upload & Ingestion Workflow with Deduplication, UX Recommendation: Search Input Clear Icon (+6 more)

### Community 9 - "Candidate Intelligence Platform (CIP)"
Cohesion: 0.08
Nodes (34): AST Parser Strict Filter Stage, $0-Cost Backup & Disaster Recovery, Candidate Intelligence Platform (CIP), ONNX Cross-Encoder Re-Ranker, Deterministic First Extraction (SpaCy NER + Regex), Event-Sourced Candidate Timeline Ledger, Fact vs Inference Split (candidate_claims), fastembed ONNX bge-small Embeddings (+26 more)

### Community 10 - "Bulk Ingestion CLI Script (scripts/bulk_ingest.py)"
Cohesion: 0.13
Nodes (15): Master Audit Telemetry Log (bulk_ingest_report.json), Bulk Ingestion CLI Script (scripts/bulk_ingest.py), Checkpointing & Resumption Engine, Dry-Run Simulation Mode (--dry-run), Entity Resolution Dummy Name Guard, Full-Text Search Tables (candidate_fts, claims_fts), LanceDB Vector Store, Multi-Tier Document Classifier (classify_document) (+7 more)

### Community 11 - "test_chunker.py"
Cohesion: 0.11
Nodes (36): chunk_document(), chunk_resume(), _match_section_header(), Section-aware text chunker with context injection. Public interface:…, Return the canonical section name if the line is a section header., Split raw resume text into (section_name, section_text) pairs. Lines that…, Split a resume into section-aware chunks with true section labels. The document…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4… (+28 more)

### Community 12 - "parse_email"
Cohesion: 0.16
Nodes (17): _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public…, Parse an Outlook .msg file using the extract_msg library., Extract body text and header metadata from an email file. Dispatch: - ``.msg``… (+9 more)

### Community 13 - "BackupManager"
Cohesion: 0.17
Nodes (12): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., Path, Regression test for the P1 audit finding: the manifest row count previously… (+4 more)

### Community 14 - "App.jsx"
Cohesion: 0.10
Nodes (14): oxc, react, warn, plugins, rules, react/only-export-components, react/rules-of-hooks, $schema (+6 more)

### Community 15 - "Environment & Tools Setup Guide (Windows)"
Cohesion: 0.15
Nodes (17): Candidate Intelligence Platform (CIP), Environment & Tools Setup Guide (Windows), Full Environment & Test Verification (pytest), Git Version Control, Ollama Binary in PATH, CPython 3.14 Windows Runtime, Windows User PATH Configuration, uv Package Manager (+9 more)

### Community 16 - "bulk_ingest.py"
Cohesion: 0.18
Nodes (17): _derive_how_processed(), generate_markdown_summary(), get_file_hash(), process_single_file(), Any, Path, Map extension (+ parser-fallback warning) to the legacy how_processed label., Process a single file through the unified intake pipeline (issue #12), adapting… (+9 more)

### Community 17 - "routes/search.py"
Cohesion: 0.11
Nodes (35): _ai_explanation_warning(), _build_search_query(), _build_structured_filter_suffix(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), _prepare_query() (+27 more)

### Community 18 - "ParsedDocument"
Cohesion: 0.17
Nodes (17): ParsedDocument, Shared data model for all ingestion parsers., Canonical output of every parser. Attributes: text: Full extracted plain-text,…, _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF… (+9 more)

### Community 19 - "React + Vite Template"
Cohesion: 0.19
Nodes (16): index.html App Entry Point, Title: Candidate Intelligence Platform, /favicon.svg Asset, /src/main.jsx Module Script Entry, #root Mount Div, HMR (Hot Module Replacement), Oxc, Oxlint (+8 more)

### Community 20 - "parse_docx"
Cohesion: 0.19
Nodes (13): DocxDocument, _extract_from_elements(), parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1.…, _parse_raw_text(), _make_docx() (+5 more)

### Community 21 - "Exploration Gate"
Cohesion: 0.24
Nodes (10): ADR Conflict Flagging, ADRs (Architecture Decision Records), CONTEXT-MAP.md, CONTEXT.md, Domain Docs Routing, Exploration Gate, Glossary Terms Usage, /domain-modeling Skill (+2 more)

### Community 22 - "intake_module_sketch.py"
Cohesion: 0.14
Nodes (21): classify_document(), ingest_file(), IntakeProgress, IntakeResult, IntakeSource, IntakeStatus, Any, Enum (+13 more)

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

### Community 27 - "CandidateSectionVector"
Cohesion: 0.23
Nodes (10): DBConnection, LanceModel, CandidateSectionVector, get_lancedb_connection(), Helper to create a vector dictionary record from a chunk and embedding., Connect to the embedded LanceDB instance at the specified path., End-to-end test verifying embedding generation, LanceDB storage, and vector…, Verify LanceDB connection and table initialization. (+2 more)

### Community 28 - "test_api_upload_stream.py"
Cohesion: 0.47
Nodes (8): _patch_extractor(), TestClient, REVIEW band COMPLETED event carries resolution_action + matched_candidate_id…, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume(), test_upload_stream_non_resume_rejected(), test_upload_stream_review_exposes_duplicate_hint_fields(), test_upload_stream_transparency_events()

### Community 29 - "App Favicon (Purple Lightning Bolt)"
Cohesion: 0.50
Nodes (5): App Favicon (Purple Lightning Bolt), Lightning Bolt Glyph, Glow Ellipses + Alpha Mask Layer, Purple Brand Palette (#863bff / #7e14ff / #ede6ff), CIP Web UI Brand Identity

### Community 31 - "test_logging.py"
Cohesion: 0.08
Nodes (55): console_renderer(), _DynamicStdoutLogger, _enable_windows_ansi(), _fallback_phrase(), get_recent_logs(), _gpu_detail(), is_polling_path(), json_renderer() (+47 more)

### Community 32 - "StorageIndexWriter"
Cohesion: 0.08
Nodes (25): _has_candidate_vectors_table(), Any, Session, Check for the candidate_vectors table across lancedb API variants., Single owner of SQLite FTS5 and LanceDB vector index synchronization., Atomic write to SQLite FTS5 table and LanceDB vector chunks., Atomic deletion from both search stores., StorageIndexWriter (+17 more)

### Community 33 - "ingest_file"
Cohesion: 0.16
Nodes (43): ingest_file(), IntakeSource, IntakeStatus, Enum, str, File-bytes door shared by /upload, /upload-stream and the bulk script. Stage…, Terminal outcome of one document through the pipeline., D3 parameter switch: web doors write the ledger, bulk keeps its own diary. (+35 more)

### Community 34 - "Vite Logo"
Cohesion: 0.67
Nodes (3): Boilerplate Template Asset, Vite Framework, Vite Logo

### Community 56 - "generate_embeddings"
Cohesion: 0.15
Nodes (17): _check_gpu_available(), generate_embeddings(), generate_single_embedding(), _get_embedding_model(), get_embedding_model_name(), _load_text_embedding(), Any, Lazy-loaded embedding model for vector search with GPU auto-detect. Default… (+9 more)

### Community 57 - "resolve_chat_model"
Cohesion: 0.13
Nodes (23): chat_retry_candidates(), _installed_ollama_model_names(), normalize_model_name(), Resolve the configured chat/explainer LLM to an actually available model.…, Return an available chat model name, or None when none is usable., Clear the cached resolution (used by tests)., Strip the tag suffix so 'llama3.2' matches 'llama3.2:latest'., Ordered chat models to try after the primary fails. (+15 more)

### Community 58 - "job_ad_distiller.py"
Cohesion: 0.19
Nodes (20): _ai_distill(), _ai_distill_ollama(), _ai_distill_openrouter(), _build_summary(), _coerce_recipe(), distill_job_ad(), _extract_title_phrase(), _fallback_distill() (+12 more)

### Community 59 - "test_model_fallbacks.py"
Cohesion: 0.16
Nodes (9): clean_model_env(), fixture, Reset lazy-loaded model singletons so every test starts fresh., Stands in for the module-level structlog logger (which may already be cached-…, reset_lazy_model_globals(), SentinelModel, SpyLogger, test_invalid_embedding_model_falls_back_to_default_with_warning() (+1 more)

### Community 60 - "test_search_engine.py"
Cohesion: 0.09
Nodes (27): parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently…, rrf_k / weights / rerank_pool_size come from settings with env overrides., Issue #38: default title filter never emits exclusionary SQL; the title value…, Issue #38: title_exact:'...' compiles to strict case-insensitive verbatim…, Issue #38 user story 1: searching 'ai engineer' must not drop "ML Engineer"…, execute_fts_query truncates to fts_pool_size when provided., When fts_pool_size is None, all rows are returned (backwards compat). (+19 more)

### Community 61 - "2. Open-Source Landscape & Library Evaluation"
Cohesion: 0.17
Nodes (11): 1. Overview & Motivation, 2. Open-Source Landscape & Library Evaluation, 3. Proposed CIP Target Architecture, 4. Implementation Steps & Roadmap, A. Dedicated Resume Parsers, B. Next-Gen Document & Layout Analyzers (Foundation Layer), C. Constrained Structured Extraction Frameworks, D. All-in-One Vector DB Ingestion Frameworks (Automatic Extract + Vector Store) (+3 more)

### Community 62 - "search_candidates"
Cohesion: 0.16
Nodes (22): _build_strict_filter_clause(), _describe_strict_filters(), execute_fts_query(), execute_strict_filter_query(), fetch_candidate_documents(), _keyword_hits(), Any, Session (+14 more)

### Community 63 - "build_match_rationale"
Cohesion: 0.31
Nodes (11): build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, _params(), Tests for candidate_intelligence_platform/intelligence/explainer.py Focus…, test_extreme_rerank_score_does_not_crash_or_default_to_50(), test_missing_rerank_score_derives_percentage_from_rrf(), test_missing_rerank_score_never_fabricates_50_percent() (+3 more)

### Community 64 - "reranker.py"
Cohesion: 0.27
Nodes (9): _check_gpu_available(), _get_reranker(), get_reranker_model_name(), _load_text_cross_encoder(), Any, Lazy-loaded cross-encoder reranker for search results with GPU auto-detect.…, Check if GPU (CUDA) is available for acceleration., Lazy-load the cross-encoder model on first use (thread-safe). Loads the… (+1 more)

### Community 65 - "conftest.py"
Cohesion: 0.11
Nodes (21): MonkeyPatch, Clear cached pricing verdicts (used by tests)., reset_openrouter_pricing_cache(), clear_settings_cache(), client(), db_engine(), db_session(), isolate_llm_environment() (+13 more)

### Community 66 - "test_api_insight_fallback.py"
Cohesion: 0.38
Nodes (11): candidate_id(), _parse_events(), fixture, Session, TestClient, _stream_insight(), test_insight_emits_visible_message_when_no_chat_model(), test_insight_invalid_model_retries_fallback_before_giving_up() (+3 more)

### Community 67 - "_run_pipeline_capturing_embedding"
Cohesion: 0.33
Nodes (6): Run search_candidates with mocked stores; return the embedded text., Direct DSL query: only free text reaches the embedding step., No free text at all: nothing gets embedded., _run_pipeline_capturing_embedding(), test_embedding_input_excludes_filter_values(), test_pure_filter_query_skips_embedding()

### Community 68 - "execute_vector_search"
Cohesion: 0.20
Nodes (10): execute_vector_search(), Execute vector search., candidate restriction is applied inside the vector store before the limit., No keyword matches means no restriction: global search unchanged., Real LanceDB store: filtered candidate must survive even when it falls outside…, test_execute_vector_search_missing_table(), test_execute_vector_search_no_restriction_for_pure_semantic(), test_execute_vector_search_prefilter_end_to_end() (+2 more)

### Community 69 - "Specification: Robust Multi-Stage Anchored Candidate Name Extraction"
Cohesion: 0.22
Nodes (8): Further Notes, Implementation Decisions, Out of Scope, Problem Statement, Solution, Specification: Robust Multi-Stage Anchored Candidate Name Extraction, Testing Decisions, User Stories

### Community 70 - "Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction"
Cohesion: 0.25
Nodes (7): 1. Concept Overview, 2. Problem Statement, 3. Proposed Solution, 4. Expected Benefits, A. Filename-Based Visa & Metadata Extractor, B. Google Sheets / CSV Ingestion Pipeline, Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction

### Community 73 - "Display Extracted Skills in Candidate Profile UI"
Cohesion: 0.33
Nodes (5): 1. Overview & Problem, 2. Proposed UI/UX Experience, 3. Backend & API Integration, 4. Implementation Steps, Display Extracted Skills in Candidate Profile UI

### Community 74 - "reciprocal_rank_fusion"
Cohesion: 0.29
Nodes (6): Computes weighted Reciprocal Rank Fusion (RRF) for two sets of candidate ranks.…, reciprocal_rank_fusion(), Issue #38 user story 4: +20% RRF bonus guarantees verbatim title matches…, test_reciprocal_rank_fusion(), test_reciprocal_rank_fusion_exact_title_bonus_ranks_exact_first(), test_reciprocal_rank_fusion_weights()

### Community 78 - "3. Detailed Technical Specification"
Cohesion: 0.17
Nodes (11): 1. Problem Statement, 2. Target Files & Architecture, 3.1 Section-Weighted Confidence Scoring, 3.2 Syntactic Prefix Stripper, 3.3 Role Grammar Anchor Pattern, 3.4 Discard Filter (Verbs & Degrees), 3.5 Title Selection Algorithm, 3. Detailed Technical Specification (+3 more)

### Community 80 - "local_llm_fallback.py"
Cohesion: 0.16
Nodes (18): stream_openrouter_generate(), _call_ollama(), _call_openrouter(), classify_document_llm(), _clean_and_parse_json(), Safely parse JSON from LLM output, stripping code blocks and markdown fences if…, Use local LLM to classify if document is a resume., Call OpenRouter API for inference. Never calls paid models. (+10 more)

### Community 85 - "Task Tracker"
Cohesion: 0.20
Nodes (9): Centralized AI Prompts (Issue #24), Completed Tickets, Consolidate Multi-Step LLM Prompts & Ingestion Batching (Issue #42), Performance Optimization Tickets, Repo Audit P1 - P5 (Issue #40), Soft Search Filters (Issue #36), Soft Semantic Job Title Search (Issue #38), Task Tracker (+1 more)

### Community 86 - "prompts.py"
Cohesion: 0.15
Nodes (12): build_fact_extraction_prompt(), build_job_ad_distill_prompt(), build_match_insight_prompt(), Match-rationale prompt for the given resume text, search query, and optional…, Job-ad parsing prompt for the given (already truncated) advertisement text., Full fact-extraction prompt for the given (already truncated) resume text., Guard tests: prompts moved into candidate_intelligence_platform.prompts must…, test_fact_extraction_prompt_is_byte_identical() (+4 more)

### Community 87 - "End-to-End Test Findings"
Cohesion: 0.40
Nodes (4): Bug / Blocker, E2E Run: August 19, 2026, End-to-End Test Findings, System Configuration

### Community 88 - "test_job_ad_distiller.py"
Cohesion: 0.14
Nodes (15): build_search_dsl(), looks_like_job_ad(), Compose the distilled recipe into parser-compatible DSL., Heuristic: a long multi-line paste is treated as a full job ad., _ai_response(), Tests for candidate_intelligence_platform/search/job_ad_distiller.py Paste-a-…, test_ai_distill_parses_recipe(), test_ai_garbage_json_falls_back_to_heuristics() (+7 more)

### Community 89 - "extract_inferences"
Cohesion: 0.16
Nodes (12): ollama, extract_inferences(), Extract AI inferences from text using a local LLM via Ollama or remote via…, Test when LLM returns null claim_value and entity in claim_key., test_llm_claim_value_null_logs_warning_and_repairs(), test_llm_extraction_failure_logs_ai_warning(), test_vector_search_failure_logs_ai_warning(), Live integration test against running Ollama instance. (+4 more)

### Community 91 - "CASManager"
Cohesion: 0.15
Nodes (12): CASManager, Path, Store content in the CAS file structure. Returns (sha256_hash,…, Remove one stored object (issue #14). store() marks files read-only; the read-…, Adapter maps IntakeResult to legacy telemetry strings; adds resolution_action., test_process_single_file_delegates_to_intake(), Issue #14: delete() clears the read-only attribute store() sets, then unlinks., Deleting an already-absent object counts as purged (idempotent cleanup). (+4 more)

### Community 92 - "test_search_ai_availability.py"
Cohesion: 0.64
Nodes (7): _patch_search(), Session, TestClient, _seed_candidate(), test_search_response_carries_ai_unavailable_warning(), test_search_response_clean_when_chat_model_available(), test_stream_search_response_carries_ai_unavailable_warning()

### Community 93 - "mock_extraction"
Cohesion: 0.25
Nodes (8): cas_mgr(), mock_extraction(), Any, fixture, Success paths pin their hash until the caller commits; tests that skip the…, Patch facts + hybrid extractor at the intake seam. Ollama never live., reset_cas_ref_registry(), vector_db()

### Community 94 - "RuntimeError"
Cohesion: 0.40
Nodes (5): RuntimeError, When CASManager.delete() raises, _purge_cas_object catches it, appends a…, When the structured parser raises, _parse_raw_text catches it, appends a…, test_parse_raw_text_falls_back_on_parser_exception(), test_purge_cas_object_on_delete_exception()

### Community 95 - "classify_document"
Cohesion: 0.50
Nodes (4): classify_document(), Classify whether a document is a genuine candidate resume or a non-resume file.…, test_classify_document(), test_classify_document_moved_and_public()

### Community 99 - "Session Handoff — 2026-08-27"
Cohesion: 0.17
Nodes (11): Change 1: SQL injection fix in `_delete_vectors`, Change 2: AST parser test suite, Change 3: Index writer test suite, Change 4: Intake error path tests, Commit, Files Changed, Pushed, Review Cycles (+3 more)

### Community 100 - "Settings"
Cohesion: 0.16
Nodes (18): get_vector_db(), BaseSettings, get_settings(), Return the process-wide Settings singleton. Cached after the first call so the…, Settings, Oversized file emits FAILED SSE event; stream endpoint stays alive for other…, test_upload_stream_rejects_oversized_file(), test_get_settings() (+10 more)

### Community 102 - "main.py"
Cohesion: 0.07
Nodes (36): health_check(), lifespan(), get, structlog_middleware(), fetch_system_logs(), get, get_engine(), Engine (+28 more)

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
- **127 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `SentinelModel`, `$schema` (+122 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

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