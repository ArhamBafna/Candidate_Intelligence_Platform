# Handoff – Candidate Intelligence Platform (CIP)

## Current State
- **Project bootstrapped** with Python virtual environment / `uv`.
- **Core Data & Storage** components are complete and fully tested:
  - `config/settings.py` (Pydantic Settings)
  - `config/database.py` (SQLAlchemy engine with WAL pragmas)
  - `storage/cas.py` (Content-Addressable Store)
  - `storage/db_models.py` (SQLAlchemy ORM + FTS5 virtual tables)
  - `storage/vector_store.py` (LanceDB connection & schema)
- **Ingestion Parsers & Chunker** completed:
  - `ingestion/parsers/pdf_parser.py` (PyMuPDF + pdfplumber + OCR)
  - `ingestion/parsers/docx_parser.py` (python-docx)
  - `ingestion/parsers/email_parser.py` (extract_msg / email.parser)
  - `ingestion/chunker.py` (Hierarchical section-aware chunker)
- **Intelligence, Fact Extraction & Search Components** (Stage 3) completed:
  - `extraction/deterministic_ner.py` (SpaCy NER, Regex)
  - `extraction/local_llm_fallback.py` (Ollama LLM JSON extraction fallback)
  - `intelligence/embeddings.py` (fastembed ONNX bge-small vector generator)
  - `search/ast_parser.py` (Strict query filter and FTS parser)
  - `search/rank_fusion.py` (Reciprocal Rank Fusion engine)
  - `search/reranker.py` (ONNX Cross-Encoder re-ranker)
  - `intelligence/explainer.py` (Match Rationale scorecard generator)
  - `search/hybrid_searcher.py` (Hybrid search orchestrator)
- **CRM Timeline & Operational Core** (Stage 4) completed:
  - `crm/timeline_ledger.py` (Event-sourced logger)
  - `crm/state_machine.py` (Candidate stage machine)
  - `backups/backup_manager.py` (SQLite backup, CAS sync)
- **Frontend / API Integration** (Stage 5) completed:
  - `api/main.py` (FastAPI application, CORS, database schema migration startup lifespan)
  - `api/dependencies.py` (SQLAlchemy & LanceDB dependency injection)
  - `api/schemas/` (Pydantic request/response schemas for candidates and search)
  - `api/routes/candidates.py` (CRUD for candidates, event-sourced timeline, and SSE multi-resume upload stream `POST /candidates/upload-stream`)
  - `api/routes/search.py` (Hybrid search endpoint with candidate enrichment)
  - `ui/` (Vite + React + Tailwind CSS Recruiter Dashboard UI with multi-resume Upload Manager progress modal)
- **Tests Created & Passed**: All 72 unit and integration tests across Stages 1-5 pass cleanly.

## What to Work on Next
1. **System Performance Optimization**: Benchmark large-scale resume parsing and search latency under heavy load.
2. **Advanced Analytics & Exporting**: Add recruiter analytics and report exporting features.

## Suggested Skills
- `python-performance-optimization` – profile heavy processing when scaling.

---
*All sensitive data has been redacted.*