# Graph Report - Candidate_Intelligence_Platform  (2026-10-09)

## Corpus Check
- 125 files · ~69,513 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .bat 1)

## Summary
- 1471 nodes · 3171 edges · 96 communities (71 shown, 25 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 484 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `54edc783`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- reranker.py
- Python Performance Optimization - advanced reference
- TimelineLedger
- hybrid_extractor.py
- upload_stream_resumes
- resolve
- devDependencies
- intake.py
- End-to-End UI Test Report & Findings
- Traditional Keyword Search Limits
- pytest
- test_chunker.py
- ParsedDocument
- CandidateSectionVector
- App.jsx
- bulk_ingest.py
- Candidate
- routes/search.py
- test_pdf_parser.py
- React + Vite Template
- docx_parser.py
- Exploration Gate
- routes/candidates.py
- icons.svg SVG symbol sprite sheet
- gh CLI
- Hero Image
- runner.js
- get_settings
- Settings
- App Favicon (Purple Lightning Bolt)
- test_hybrid_search_candidates_applies_tuning_knobs
- logging.py
- test_index_writer.py
- ingest_file
- Vite Logo
- backups/__init__.py
- crm/__init__.py
- test_prompts.py
- json
- Shared Routing Phrases
- distill_job_ad
- MarkdownRenderer.jsx
- candidate-intelligence-platform
- Entity Resolution Auto-Merge
- React Logo
- package.json
- local_llm_fallback.py
- chat_model.py
- job_ad_distiller.py
- test_model_fallbacks.py
- test_search_engine.py
- 2. Open-Source Landscape & Library Evaluation
- hybrid_searcher.py
- build_match_rationale
- dependencies.py
- conftest.py
- test_api_insight_fallback.py
- _run_pipeline_capturing_embedding
- embeddings.py
- _run_pipeline
- Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction
- Hybrid Ranking Search Flow
- StorageIndexWriter
- Display Extracted Skills in Candidate Profile UI
- reciprocal_rank_fusion
- LanceDB Meaning Map Analogy
- SHA-256 Fingerprinting Dedup Before Parsing
- 3. Detailed Technical Specification
- dependencies
- test_execute_vector_search_prefilters_before_limit
- test_execute_vector_search_no_restriction_for_pure_semantic
- CASManager
- .oxlintrc.json
- test_execute_vector_search_respects_pool_size
- scripts
- chunker.py
- End-to-End Test Findings
- vector_db
- extract_inferences
- classify_document
- test_bulk_ingest.py
- test_search_ai_availability.py
- test_ui_duplicate_chip_wired
- test_exact_title_mode_restricts_vector_pool_to_verbatim_matches
- test_golden_eval.py

## God Nodes (most connected - your core abstractions)
1. `Candidate` - 81 edges
2. `ingest_file()` - 62 edges
3. `Settings` - 43 edges
4. `get_settings()` - 40 edges
5. `IntakeStatus` - 34 edges
6. `IntakeSource` - 34 edges
7. `TimelineMode` - 32 edges
8. `ResumeVersion` - 32 edges
9. `StorageIndexWriter` - 32 edges
10. `CASManager` - 29 edges

## Surprising Connections (you probably didn't know these)
- `3. Backend & API Integration` --references--> `CandidateResponse`  [INFERRED]
  docs/ideas/structured-claims-and-skills-pipeline.md → api/schemas/candidates.py
- `Testing Decisions` --references--> `ExtractionOutcome`  [INFERRED]
  docs/ideas/robust-name-extraction.md → src/candidate_intelligence_platform/extraction/hybrid_extractor.py
- `Implementation Decisions` --references--> `extract_inferences()`  [INFERRED]
  docs/ideas/robust-name-extraction.md → src/candidate_intelligence_platform/extraction/local_llm_fallback.py
- `Implementation Decisions` --references--> `ExtractionOutcome`  [INFERRED]
  docs/ideas/robust-name-extraction.md → src/candidate_intelligence_platform/extraction/hybrid_extractor.py
- `Implementation Decisions` --references--> `extract_candidate_profile_hybrid()`  [INFERRED]
  docs/ideas/robust-name-extraction.md → src/candidate_intelligence_platform/extraction/hybrid_extractor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Wayfinding Ticket Lifecycle** — docs_agents_issue_tracker_wayfinder_map_issue, docs_agents_issue_tracker_blocking_dependencies, docs_agents_issue_tracker_gh_cli [EXTRACTED 0.95]
- **Five-step performance optimization workflow** — agents_skills_python_performance_optimization_skill_workflow_measure, agents_skills_python_performance_optimization_skill_workflow_profile, agents_skills_python_performance_optimization_skill_workflow_choose, agents_skills_python_performance_optimization_skill_workflow_change, agents_skills_python_performance_optimization_skill_workflow_verify [EXTRACTED 1.00]
- **CIP ingestion-to-retrieval pipeline** — readme_content_addressable_store, readme_document_parsers, readme_section_aware_chunker, readme_entity_resolution_engine, readme_sqlite_wal_database, readme_lancedb_vector_store, readme_fastapi_rest_backend, readme_react_tailwind_ui [EXTRACTED 1.00]
- **Measure-before-and-after optimization workflow** — agents_skills_python_performance_optimization_references_advanced_patterns, references_advanced_custom_benchmark_decorator, references_advanced_pytest_benchmark_testing [INFERRED 0.85]
- **Product visual identity system (dark + violet isometric stack)** — ui_src_assets_hero_heroshot, ui_src_assets_hero_stacked_slabs, ui_src_assets_hero_purple_rim_lighting, ui_src_assets_hero_dark_theme_branding [INFERRED 0.95]

## Communities (96 total, 25 thin omitted)

### Community 0 - "reranker.py"
Cohesion: 0.17
Nodes (13): _check_gpu_available(), _get_reranker(), get_reranker_model_name(), _load_text_cross_encoder(), Any, Lazy-loaded cross-encoder reranker for search results with GPU auto-detect.…, Reranks a list of documents based on a query using a cross-encoder model.…, Check if GPU (CUDA) is available for acceleration. (+5 more)

### Community 1 - "Python Performance Optimization - advanced reference"
Cohesion: 0.06
Nodes (52): AGENTS.md - CIP agent guidelines, Implementation rules, Keep candidate data and processing local rule, Mission: privacy-first local-first candidate intelligence, Mock heavy ML models in tests rule, Python Performance Optimization - advanced reference, Python Performance Optimization - standard reference, Pattern 10: Function Call Overhead (+44 more)

### Community 2 - "TimelineLedger"
Cohesion: 0.14
Nodes (15): CandidateStateMachine, Transitions the candidate to a new status and logs the event., TransitionContext, Any, Session, Logs a new event in the candidate's timeline., Retrieves all timeline events for a candidate, ordered by creation date…, Event-sourced logger for candidate timeline events. (+7 more)

### Community 3 - "hybrid_extractor.py"
Cohesion: 0.05
Nodes (53): update_candidate(), candidate_intelligence_platform_extraction_deterministic_ner, candidate_intelligence_platform_extraction_hybrid_extractor, Further Notes, Implementation Decisions, Out of Scope, Problem Statement, Solution (+45 more)

### Community 4 - "upload_stream_resumes"
Cohesion: 0.21
Nodes (9): batch_reprocess_candidate_stream(), Any, post, StreamingResponse, reprocess_candidate(), reprocess_candidate_stream(), upload_resume(), upload_stream_resumes() (+1 more)

### Community 5 - "resolve"
Cohesion: 0.10
Nodes (28): difflib, CandidateIdentifiers, _normalize(), Enum, ResolutionAction, ResolutionResult, resolve(), _resolve_tier_1() (+20 more)

### Community 6 - "devDependencies"
Cohesion: 0.20
Nodes (10): devDependencies, autoprefixer, oxlint, postcss, tailwindcss, @tailwindcss/postcss, @types/react, @types/react-dom (+2 more)

### Community 7 - "intake.py"
Cohesion: 0.10
Nodes (29): ProgressCallback, _bind_release_on_commit(), _release(), _build_audit_criteria(), _emit(), _has_committed_reference(), IntakeProgress, IntakeResult (+21 more)

### Community 8 - "End-to-End UI Test Report & Findings"
Cohesion: 0.14
Nodes (14): UX Recommendation: Autosave Timestamp Display, E2E-05: Candidate Detail View & Autosave, UX Recommendation: Candidate List Auto-Refresh on Route Return (fetchCandidates), E2E-01: Initial Page Load & Shell, E2E-06: Multi-Select & Batch Actions, Playwriter Direct CDP Automation Driver (Chrome 151, port 9222), E2E-03: SSE Resume Upload & Ingestion Workflow with Deduplication, UX Recommendation: Search Input Clear Icon (+6 more)

### Community 10 - "pytest"
Cohesion: 0.21
Nodes (17): InvalidStateTransition, Exception, DeclarativeBase, pytest, sqlalchemy, sqlalchemy_orm, sqlalchemy_sql, Base (+9 more)

### Community 11 - "test_chunker.py"
Cohesion: 0.12
Nodes (33): chunk_document(), chunk_resume(), Split raw resume text into (section_name, section_text) pairs. Lines that…, Split a resume into section-aware chunks with true section labels. The document…, A single text chunk produced by the chunker. Attributes: chunk_id: UUIDv4…, Split a ParsedDocument's text into overlapping fixed-size chunks. Strategy: -…, split_resume_sections(), TextChunk (+25 more)

### Community 12 - "ParsedDocument"
Cohesion: 0.15
Nodes (21): email, email_header, _decode_header(), parse_email(), _parse_eml(), _parse_msg(), Path, Email parser supporting .eml (RFC-2822) and .msg (Outlook) files. Public… (+13 more)

### Community 13 - "CandidateSectionVector"
Cohesion: 0.09
Nodes (26): BackupManager, Executes a live hot backup using sqlite3.backup API., Copies any new files from the source CAS directory to the backup CAS directory.…, Attempts to read row count from LanceDB. Returns 0 if missing., Generates a JSON manifest containing SHA256 of the backup DB, CAS file count,…, Handles live backups of the SQLite database and syncing the CAS storage., DBConnection, lancedb (+18 more)

### Community 14 - "App.jsx"
Cohesion: 0.24
Nodes (9): @phosphor-icons/react, react, react-dom, react-router-dom, App(), SystemLogDrawer(), ui_src_index, CandidateDetail() (+1 more)

### Community 15 - "bulk_ingest.py"
Cohesion: 0.14
Nodes (15): argparse, _derive_how_processed(), Map extension (+ parser-fallback warning) to the legacy how_processed label., datetime, hashlib, os, pathlib, stat (+7 more)

### Community 16 - "Candidate"
Cohesion: 0.17
Nodes (27): Candidate, ResumeVersion, parametrize, Session, TestClient, POST /candidates/upload returns 413 when file exceeds max_upload_size_mb., POST /candidates/upload succeeds (not 413) when file is within the limit., test_batch_delete_candidates() (+19 more)

### Community 17 - "routes/search.py"
Cohesion: 0.10
Nodes (38): _ai_explanation_warning(), _build_search_query(), _build_structured_filter_suffix(), _format_search_results(), _hydrate_candidates(), perform_search(), perform_search_stream(), event_generator() (+30 more)

### Community 18 - "test_pdf_parser.py"
Cohesion: 0.14
Nodes (17): _extract_with_pdfplumber(), parse_pdf(), Path, PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).…, Extract text and metadata from a PDF file. Strategy: 1. Open with PyMuPDF…, Extract text from a single page using pdfplumber. Used as a fallback when…, io, pymupdf (+9 more)

### Community 19 - "React + Vite Template"
Cohesion: 0.19
Nodes (16): index.html App Entry Point, Title: Candidate Intelligence Platform, /favicon.svg Asset, /src/main.jsx Module Script Entry, #root Mount Div, HMR (Hot Module Replacement), Oxc, Oxlint (+8 more)

### Community 20 - "docx_parser.py"
Cohesion: 0.17
Nodes (14): docx, docx_table, DocxDocument, _extract_from_elements(), parse_docx(), Path, DOCX parser using python-docx. Public interface: parse_docx(path: Path) ->…, Extract text and metadata from a Word (.docx) file. Extraction order: 1.… (+6 more)

### Community 21 - "Exploration Gate"
Cohesion: 0.24
Nodes (10): ADR Conflict Flagging, ADRs (Architecture Decision Records), CONTEXT-MAP.md, CONTEXT.md, Domain Docs Routing, Exploration Gate, Glossary Terms Usage, /domain-modeling Skill (+2 more)

### Community 22 - "routes/candidates.py"
Cohesion: 0.12
Nodes (29): batch_delete_candidates(), delete_candidate(), get_candidate(), get_candidate_file(), get_candidate_insight(), _unavailable_event(), get_candidate_timeline(), list_candidates() (+21 more)

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
Cohesion: 0.29
Nodes (5): fs, path, runE2ETests(), ref_fs, ref_path

### Community 27 - "get_settings"
Cohesion: 0.10
Nodes (23): health_check(), lifespan(), get, get_settings(), Return the process-wide Settings singleton. Cached after the first call so the…, contextlib, FastAPI, fastapi_middleware_cors (+15 more)

### Community 28 - "Settings"
Cohesion: 0.12
Nodes (21): BaseSettings, Settings, _patch_extractor(), TestClient, Oversized file emits FAILED SSE event; stream endpoint stays alive for other…, REVIEW band COMPLETED event carries resolution_action + matched_candidate_id…, test_upload_stream_duplicate_resume(), test_upload_stream_multi_resume() (+13 more)

### Community 29 - "App Favicon (Purple Lightning Bolt)"
Cohesion: 0.50
Nodes (5): App Favicon (Purple Lightning Bolt), Lightning Bolt Glyph, Glow Ellipses + Alpha Mask Layer, Purple Brand Palette (#863bff / #7e14ff / #ede6ff), CIP Web UI Brand Identity

### Community 30 - "test_hybrid_search_candidates_applies_tuning_knobs"
Cohesion: 0.14
Nodes (10): rrf_k / weights / rerank_pool_size come from settings with env overrides., search_candidates wires rerank_pool_size into execute_fts_query., test_hybrid_search_candidates(), test_hybrid_search_candidates_applies_tuning_knobs(), mock_db_fts(), mock_explainer(), mock_fusion(), mock_parse() (+2 more)

### Community 31 - "logging.py"
Cohesion: 0.07
Nodes (60): structlog_middleware(), fetch_system_logs(), get, console_renderer(), _DynamicStdoutLogger, _enable_windows_ansi(), _fallback_phrase(), get_recent_logs() (+52 more)

### Community 32 - "test_index_writer.py"
Cohesion: 0.07
Nodes (21): _has_candidate_vectors_table(), Check for the candidate_vectors table across lancedb API variants., delete(), search(), MockTable, Session, Vector DB that has delete_candidate_vectors method (modern API)., Vector DB without delete_candidate_vectors — falls back to table.delete(). (+13 more)

### Community 33 - "ingest_file"
Cohesion: 0.13
Nodes (47): process_single_file(), Process a single file through the unified intake pipeline (issue #12), adapting…, _acquire_cas_ref(), ingest_file(), IntakeSource, IntakeStatus, Enum, Register this pipeline as an active holder of the shared CAS object. (+39 more)

### Community 34 - "Vite Logo"
Cohesion: 0.67
Nodes (3): Boilerplate Template Asset, Vite Framework, Vite Logo

### Community 37 - "test_prompts.py"
Cohesion: 0.13
Nodes (22): build_batched_extraction_prompt(), build_consolidated_match_insight_prompt(), build_fact_extraction_prompt(), build_json_repair_prompt(), build_match_insight_prompt(), Match-rationale prompt for the given resume text, search query, and optional…, Build consolidated match insight prompt. Handles optional criteria including…, Full fact-extraction prompt for the given (already truncated) resume text. (+14 more)

### Community 43 - "json"
Cohesion: 0.18
Nodes (10): candidate_intelligence_platform_extraction_local_llm_fallback, json, ollama, TestClient, Test that the search stream yields the expected stage events., Test that the POST /search/stream endpoint exists and accepts valid requests., test_search_stream_emits_progress_events(), test_search_stream_endpoint_exists() (+2 more)

### Community 45 - "distill_job_ad"
Cohesion: 0.13
Nodes (19): candidate_intelligence_platform_search, candidate_intelligence_platform_search_job_ad_distiller, build_search_dsl(), distill_job_ad(), looks_like_job_ad(), Distill a pasted job ad: configured provider first, local Ollama second,…, Compose the distilled recipe into parser-compatible DSL., Heuristic: a long multi-line paste is treated as a full job ad. (+11 more)

### Community 46 - "MarkdownRenderer.jsx"
Cohesion: 0.22
Nodes (4): react-markdown, remark-gfm, ErrorBoundary, MarkdownRenderer()

### Community 55 - "package.json"
Cohesion: 0.13
Nodes (14): autoprefixer, lucide-react, oxlint, postcss, tailwindcss, @tailwindcss/postcss, @types/react, @types/react-dom (+6 more)

### Community 56 - "local_llm_fallback.py"
Cohesion: 0.11
Nodes (25): stream_openrouter_generate(), concurrent_futures, re, RuntimeError, _call_ollama(), _call_openrouter(), classify_document_llm(), _clean_and_parse_json() (+17 more)

### Community 57 - "chat_model.py"
Cohesion: 0.10
Nodes (29): event_generator(), stream_tokens(), stream_ollama_generate(), candidate_intelligence_platform_intelligence_chat_model, chat_retry_candidates(), _installed_ollama_model_names(), normalize_model_name(), Resolve the configured chat/explainer LLM to an actually available model.… (+21 more)

### Community 58 - "job_ad_distiller.py"
Cohesion: 0.15
Nodes (21): build_job_ad_distill_prompt(), Job-ad parsing prompt for the given (already truncated) advertisement text., _ai_distill(), _ai_distill_ollama(), _ai_distill_openrouter(), _build_summary(), _coerce_recipe(), _extract_title_phrase() (+13 more)

### Community 59 - "test_model_fallbacks.py"
Cohesion: 0.16
Nodes (15): clean_model_env(), fixture, Reset lazy-loaded model singletons so every test starts fresh., Stands in for the module-level structlog logger (which may already be cached-…, reset_lazy_model_globals(), SentinelModel, SpyLogger, test_embedding_model_loaded_from_settings() (+7 more)

### Community 60 - "test_search_engine.py"
Cohesion: 0.09
Nodes (25): candidate_intelligence_platform_search_ast_parser, candidate_intelligence_platform_search_rank_fusion, candidate_intelligence_platform_search_reranker, parse_query_to_sql(), Parses a strict query string into a SQL query and parameters. Currently…, parametrize, test_parse_query_to_sql(), Issue #38: default title filter never emits exclusionary SQL; the title value… (+17 more)

### Community 61 - "2. Open-Source Landscape & Library Evaluation"
Cohesion: 0.17
Nodes (11): 1. Overview & Motivation, 2. Open-Source Landscape & Library Evaluation, 3. Proposed CIP Target Architecture, 4. Implementation Steps & Roadmap, A. Dedicated Resume Parsers, B. Next-Gen Document & Layout Analyzers (Foundation Layer), C. Constrained Structured Extraction Frameworks, D. All-in-One Vector DB Ingestion Frameworks (Automatic Extract + Vector Store) (+3 more)

### Community 62 - "hybrid_searcher.py"
Cohesion: 0.20
Nodes (19): _build_strict_filter_clause(), _describe_strict_filters(), execute_fts_query(), execute_strict_filter_query(), execute_vector_search(), fetch_candidate_documents(), _keyword_hits(), Any (+11 more)

### Community 63 - "build_match_rationale"
Cohesion: 0.31
Nodes (11): build_match_rationale(), MatchParameters, Builds the Match Rationale scorecard for a candidate search result, including a…, _params(), Tests for candidate_intelligence_platform/intelligence/explainer.py Focus…, test_extreme_rerank_score_does_not_crash_or_default_to_50(), test_missing_rerank_score_derives_percentage_from_rrf(), test_missing_rerank_score_never_fabricates_50_percent() (+3 more)

### Community 64 - "dependencies.py"
Cohesion: 0.15
Nodes (13): get_db(), _get_sessionmaker(), get_vector_db(), Session, get_engine(), Engine, Create a SQLAlchemy engine configured for SQLite with WAL mode., sqlalchemy_engine (+5 more)

### Community 65 - "conftest.py"
Cohesion: 0.10
Nodes (24): MonkeyPatch, sqlalchemy_pool, Clear cached pricing verdicts (used by tests)., reset_openrouter_pricing_cache(), clear_settings_cache(), client(), override_get_settings(), override_get_vector_db() (+16 more)

### Community 66 - "test_api_insight_fallback.py"
Cohesion: 0.12
Nodes (21): process_candidate(), on_progress_bridge(), Canonical pipeline stages -> reprocess contracted stage names/progress., stream_generator(), on_progress_bridge(), translate_reprocess_progress(), label_for_model(), Recruiter-friendly AI status messages shown in the interface. Keep every string… (+13 more)

### Community 67 - "_run_pipeline_capturing_embedding"
Cohesion: 0.17
Nodes (6): Run search_candidates with mocked stores; return the embedded text., Direct DSL query: only free text reaches the embedding step., No free text at all: nothing gets embedded., _run_pipeline_capturing_embedding(), test_embedding_input_excludes_filter_values(), test_pure_filter_query_skips_embedding()

### Community 68 - "embeddings.py"
Cohesion: 0.11
Nodes (20): candidate_intelligence_platform_intelligence_embeddings, candidate_intelligence_platform_intelligence_explainer, functools, _check_gpu_available(), generate_embeddings(), generate_single_embedding(), _get_embedding_model(), get_embedding_model_name() (+12 more)

### Community 69 - "_run_pipeline"
Cohesion: 0.22
Nodes (3): _run_pipeline(), test_match_scorecards_populated_from_query_and_data(), test_reranker_failure_preserves_fusion_order_and_warns()

### Community 70 - "Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction"
Cohesion: 0.25
Nodes (7): 1. Concept Overview, 2. Problem Statement, 3. Proposed Solution, 4. Expected Benefits, A. Filename-Based Visa & Metadata Extractor, B. Google Sheets / CSV Ingestion Pipeline, Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction

### Community 72 - "StorageIndexWriter"
Cohesion: 0.24
Nodes (6): Any, Session, Single owner of SQLite FTS5 and LanceDB vector index synchronization., Atomic write to SQLite FTS5 table and LanceDB vector chunks., Atomic deletion from both search stores., StorageIndexWriter

### Community 73 - "Display Extracted Skills in Candidate Profile UI"
Cohesion: 0.33
Nodes (5): 1. Overview & Problem, 2. Proposed UI/UX Experience, 3. Backend & API Integration, 4. Implementation Steps, Display Extracted Skills in Candidate Profile UI

### Community 74 - "reciprocal_rank_fusion"
Cohesion: 0.22
Nodes (8): collections, math, Computes weighted Reciprocal Rank Fusion (RRF) for two sets of candidate ranks.…, reciprocal_rank_fusion(), Issue #38 user story 4: +20% RRF bonus guarantees verbatim title matches…, test_reciprocal_rank_fusion(), test_reciprocal_rank_fusion_exact_title_bonus_ranks_exact_first(), test_reciprocal_rank_fusion_weights()

### Community 78 - "3. Detailed Technical Specification"
Cohesion: 0.17
Nodes (11): 1. Problem Statement, 2. Target Files & Architecture, 3.1 Section-Weighted Confidence Scoring, 3.2 Syntactic Prefix Stripper, 3.3 Role Grammar Anchor Pattern, 3.4 Discard Filter (Verbs & Degrees), 3.5 Title Selection Algorithm, 3. Detailed Technical Specification (+3 more)

### Community 79 - "dependencies"
Cohesion: 0.25
Nodes (8): dependencies, lucide-react, @phosphor-icons/react, react, react-dom, react-markdown, react-router-dom, remark-gfm

### Community 82 - "CASManager"
Cohesion: 0.16
Nodes (9): CASManager, Path, Store content in the CAS file structure. Returns (sha256_hash,…, Remove one stored object (issue #14). store() marks files read-only; the read-…, MockVectorStore, Mock LanceDB vector store connection for isolated test runs., test_parallel_ingest_no_database_locked(), CAS_MANAGER_SHIM() (+1 more)

### Community 83 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 85 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, preview

### Community 86 - "chunker.py"
Cohesion: 0.33
Nodes (5): dataclasses, _match_section_header(), Section-aware text chunker with context injection. Public interface:…, Return the canonical section name if the line is a section header., Shared data model for all ingestion parsers.

### Community 87 - "End-to-End Test Findings"
Cohesion: 0.40
Nodes (4): Bug / Blocker, E2E Run: August 19, 2026, End-to-End Test Findings, System Configuration

### Community 88 - "vector_db"
Cohesion: 0.20
Nodes (13): run_pipeline(), process_file(), on_progress(), run_pipeline(), translate_progress(), cas_mgr(), mock_extraction(), Any (+5 more)

### Community 89 - "extract_inferences"
Cohesion: 0.12
Nodes (16): candidate_intelligence_platform_search_hybrid_searcher, extract_inferences(), LLMExtractionFatalError, Exception, Extract AI inferences from text using a local LLM via Ollama or remote via…, Raised when the LLM repeatedly fails to return valid JSON even after repair…, structlog, Test when LLM returns null claim_value and entity in claim_key. (+8 more)

### Community 90 - "classify_document"
Cohesion: 0.50
Nodes (4): classify_document(), Classify whether a document is a genuine candidate resume or a non-resume file.…, test_classify_document(), test_classify_document_moved_and_public()

### Community 91 - "test_bulk_ingest.py"
Cohesion: 0.15
Nodes (16): generate_markdown_summary(), get_file_hash(), Any, Path, Generate a clean, structured, human-readable Markdown report summarizing the…, run_bulk_ingest(), importlib, sys (+8 more)

### Community 92 - "test_search_ai_availability.py"
Cohesion: 0.13
Nodes (16): fastapi_testclient, TestClient, test_get_logs_endpoint_returns_recent_events(), TestClient, PR #25 review: failed requests keep an access record (path/status/duration)., test_404_handler(), test_cors_headers(), test_health_check() (+8 more)

### Community 95 - "test_exact_title_mode_restricts_vector_pool_to_verbatim_matches"
Cohesion: 0.33
Nodes (5): Issue #38 user story 1: searching 'ai engineer' must not drop "ML Engineer"…, Issue #38 user story 2: exact_title only keeps literal current_title matches,…, test_exact_title_mode_restricts_vector_pool_to_verbatim_matches(), test_soft_title_search_surfaces_related_titles_and_badges(), fake_vector()

### Community 102 - "test_golden_eval.py"
Cohesion: 0.18
Nodes (16): evaluation, init_db(), Engine, Creates all declarative tables, FTS5 virtual tables, and performance indexes., Verify that all relational and FTS5 tables are created successfully., test_db_schema_creation(), golden_store(), _load_golden_set() (+8 more)

## Ambiguous Edges - Review These
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
- **99 isolated node(s):** `path`, `fs`, `candidate-intelligence-platform`, `$schema`, `plugins` (+94 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 547 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

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
- **What is the exact relationship between `bluesky-icon symbol (Bluesky logo)` and `x-icon symbol (X/Twitter logo)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `discord-icon symbol (Discord logo)` and `github-icon symbol (GitHub octocat mark)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._