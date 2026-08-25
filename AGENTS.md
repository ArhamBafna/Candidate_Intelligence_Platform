# AGENTS.md

## Mission

CIP is a privacy-first, local-first candidate intelligence and retrieval system for résumés, CVs, emails, and profiles. Preserve local-only behavior: request approval before adding any remote API or cloud dependency.

## Working sequence

1. **Orient.** Read `docs/agents/domain.md` before exploring domain behavior. Read relevant ADRs in `docs/adr/` and any context file they identify.
2. **Change.** Follow existing module boundaries and types. Keep CAS deduplication before parsing, SQLite WAL behavior, and immutable SHA-256 CAS files.
3. **Verify.** Run the smallest relevant existing test, then `uv run pytest` unless the user gives another scope. Work is complete only when changed behavior is covered and the selected tests pass.
4. **Track.** Update the matching unchecked item in `docs/task.md` only when the change completes that item. Work is complete only when the task entry reflects the delivered state.

## Implementation rules

- Add explicit type annotations for every argument and return value.
- Validate ingestion data with Pydantic v2 schemas.
- Use SQLAlchemy 2.0 models in `storage/db_models.py`.
- Check hashes through `storage/cas.py` before parsing.
- Add tests for changed behavior; ingestion, storage, and config modules require corresponding `tests/test_<module>.py` coverage.
- Write fast tests (< 2s per file): always mock heavy ML models (spaCy, FastEmbed/SentenceTransformers, CrossEncoder reranker) and LLM inference (Ollama). Never introduce unmocked model loading, blocking event loops, or unbounded stream iterations in the test suite.
- Keep SQLite WAL pragmas mandatory.
- Every LLM prompt must be defined in `src/candidate_intelligence_platform/prompts.py` via a named builder function — never inline at a call site.
- Keep all candidate data and processing local unless the user approves an exception.

## Environment

Use `pyproject.toml` and the repository layout as sources of truth for versions and dependencies.

```powershell
uv sync
# Or
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

`pytest` uses `pythonpath = ["."]` from `pyproject.toml`.

```powershell
# Default: skips live Ollama integration
uv run pytest

# Include live Ollama integration
uv run pytest --run-ollama

# Run only live Ollama integration
uv run pytest -m ollama --run-ollama
```

## Agent-facing references

- GitHub issue and PR operations: `docs/agents/issue-tracker.md`
- Domain exploration, context files, and ADRs: `docs/agents/domain.md`
- Product direction for agentic retrieval: `docs/ideas/agentic-retrieval.md`

Create commits or push only when the user requests it or the task explicitly requires it.

---
OPTIONAL READ:
# Candidate Intelligence Platform - Codebase Exploration Summary
## 1. Overall Project Structure
The project is organized as a **local-first, privacy-focused candidate intelligence and retrieval system** for résumés, CVs, emails, and profiles. Key directory layout:
```
Root/
├── api/                    # FastAPI application
│   ├── main.py             # App setup, middleware, lifespan
│   ├── routes/             # API endpoints (candidates, search, logs)
│   ├── dependencies.py     # Dependency injection
│   └── schemas/            # Pydantic v2 models
├── src/candidate_intelligence_platform/  # Main Python package
│   ├── config/             # Pydantic settings
│   ├── storage/            # CAS, DB models, LanceDB
│   ├── ingestion/          # Document pipeline (intake.py)
│   ├── extraction/         # NER and LLM fallback
│   ├── search/             # Hybrid search (AST + vector + RRF + reranker)
│   ├── intelligence/       # Embeddings and explainers
│   ├── crm/                # State machine + timeline ledger
│   └── prompts.py          # Central LLM prompt catalog
├── storage/                # Runtime files (SQLite DB, CAS, LanceDB)
├── tests/                  # 46 test files
├── docs/                   # Full documentation
│   ├── agents/             # Domain & issue tracker guides
│   ├── adr/                # Architecture decision records
│   ├── task.md             # Task/ticket tracker
│   └── architecture_design_document.md
├── api/routes/candidates.py  # 912-line main router
├── api/routes/search.py      # 205-line search router
├── pyproject.toml          # Project config (deps, scripts)
└── .env                    # Environment config (CIP_LLM_PROVIDER=openrouter)
```
## 2. What the Project Does
**Core Functionality:**
- **Document Ingestion**: Parse PDF, DOCX, EML, MSG files via multi-stage pipeline (hashing → CAS store → parsing → classification → entity resolution)
- **Entity Resolution**: Deterministic matching (exact email/phone/LinkedIn) + probabilistic graph similarity (Jaro-Winkler names, date/company overlap, skill/location vectors)
- **Hybrid Search**: Two-stage pipeline — AST parser (SQLite FTS5 filters) → Dense semantic search (LanceDB HNSW) → Reciprocal Rank Fusion → Cross-Encoder re-ranker
- **Candidate Profile Management**: Unified working copy with immutable resume versions, explicit fact vs AI-inference split via `candidate_claims` table
- **API Endpoints**: `/upload`, `/upload-stream`, `/search`, `/candidates/{id}`, `/candidates/{id}/insight` (SSE AI explanations)
- **Cryptographic Deduplication**: SHA-256 content-addressed storage automatically prevents duplicate file storage
**Key Technical Decisions:**
- SQLite WAL mode + 64MB cache
- LanceDB embedded vector store with HNSW index
- fastembed `BAAI/bge-small-en-v1.5` (384 dims) for embeddings
- Ollama `llama3.2` as default LLM, OpenRouter as optional cloud fallback
- Content-Addressable Storage (CAS) sharded by first 4 chars of SHA-256 hash
- Separate `EXPLICIT_FACT` vs `AI_INFERENCE` source tracking in `candidate_claims`
## 3. Issue 29 Search Results
**No references to "issue 29", "#29", or "issue_29" were found anywhere in the codebase** — not in Python files, Markdown docs, task lists, or any other files.
The task tracking (`docs/task.md`) references these issue numbers:
- **Issue #24**: Centralized AI Prompts (completed — all prompts moved to `src/candidate_intelligence_platform/prompts.py`)
- **Issue #12**: Unified Intake Pipeline (completed — multi-door shared pipeline)
- **Performance Tickets P0-P7**: All completed (baseline, thread-offload, DB indexes, lazy models, GPU auto-detect, gates/docs)
- **Completed Tickets 01-06**: Various test, algorithm, security, and simplification tickets
The issue tracker documentation (`docs/agents/issue-tracker.md`) describes a GitHub-based workflow using `gh` CLI but doesn't list specific issue numbers.
## 4. pyproject.toml Configuration
```toml
name = "candidate-intelligence-platform"
version = "0.1.0"
description = "Add your description here"
requires-python = ">=3.14"
dependencies = [
    "click>=8.4.2", "extract-msg>=0.56.0", "fastapi[standard]>=0.141.1",
    "fastembed>=0.8.0", "httpx>=0.28.1", "lancedb>=0.36.0", "ollama>=0.6.2",
    "pdfplumber>=0.11.10", "pydantic>=2.13.4", "pydantic-settings>=2.15.0",
    "pymupdf>=1.28.2", "pytest>=9.1.1", "pytest-benchmark>=5.1.0",
    "python-docx>=1.2.0", "spacy>=3.8.13", "sqlalchemy>=2.0.51",
    "structlog>=24.0.0",
]
candidate-intelligence-platform = "candidate_intelligence_platform:main"
pythonpath = ["."]
markers = [
    "ollama: marks tests as requiring live Ollama instance",
    "evaluation: marks golden-set search accuracy evaluation tests",
]
requires = ["uv_build>=0.12.3,<0.13.0"]
build-backend = "uv_build"
```
**Key dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0, LanceDB, Ollama, PDF tools, spaCy, fastembed
## 5. docs/agents/ Domain Information
- **`docs/agents/domain.md`**: Exploration gate requiring CONTEXT.md, CONTEXT-MAP.md, and ADR review before domain behavior exploration
- **`docs/agents/issue-tracker.md`**: GitHub issue workflow using `gh` CLI — create/read/list/comment/label/close operations
## 6. Existing Tests
**46 test files** covering:
- **API tests**: `test_api_main.py`, `test_api_candidates.py`, `test_api_search.py`, `test_api_search_stream.py`, `test_api_upload_stream.py`, `test_api_logs.py`, `test_api_insight_fallback.py`
- **Database**: `test_db_models.py`, `test_database.py`
- **CAS**: `test_cas.py`
- **Ingestion**: `test_intake.py`, `test_bulk_ingest.py`, `test_chunker.py`
- **Extraction**: `test_docx_parser.py`, `test_email_parser.py`, `test_pdf_parser.py`, `test_deterministic_ner.py`, `test_hybrid_extractor.py`
- **Search**: `test_search_engine.py`, `test_search_logging.py`, `test_search_ai_availability.py`
- **Intelligence**: `test_intelligence.py`, `test_entity_resolution.py`, `test_vector_store.py`
- **LLM/Fallback**: `test_local_llm_fallback.py`, `test_ai_failure_logging.py`, `test_model_fallbacks.py`, `test_chat_model.py`, `test_prompts.py`
- **Others**: `test_settings.py`, `test_dependencies.py`, `test_state_machine.py`, `test_timeline_ledger.py`, `test_logging.py`, `test_upload_logging.py`, `test_ui_build.py`, `test_golden_eval.py`, `test_explainer.py`, `test_performance.py`, `test_dependencies.py`
Tests follow patterns of mocking heavy ML models (spaCy, FastEmbed, CrossEncoder, Ollama) and use `conftest.py` for shared fixtures. Tests are run with `uv run pytest` (skips live Ollama by default) or `uv run pytest --run-ollama` to include them.
## Key Files for Issue 29 (if creating a new ticket)
