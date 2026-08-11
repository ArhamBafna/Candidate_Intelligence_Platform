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
- **Tests Created & Passed**: All unit tests for Stages 1-4 pass cleanly.

## What to Work on Next
1. **Frontend / API Integration** (Stage 5):
   - Build FastAPI endpoints to expose the platform capabilities.
   - Build UI for recruiters to ingest, search, and manage candidates.
2. **Review System Performance** under load.

## Suggested Skills
- `python-performance-optimization` – profile heavy processing when scaling.

---