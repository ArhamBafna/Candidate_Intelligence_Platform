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
- **Tests Created**: All unit tests for core data, storage, parsers, chunker, and entity resolution specifications exist in `tests/`.

## What to Work on Next
1. **Entity Resolution Engine** (`ingestion/entity_resolution.py`):
   - Complete green implementation for Tier 1 (deterministic exact match) and Tier 2 (probabilistic Jaro-Winkler name similarity match).
   - Test suite is already defined in `tests/test_entity_resolution.py`.
2. **Intelligence & Fact Extraction Phase** (Stage 3):
   - `extraction/deterministic_ner.py` (SpaCy NER, Regex)
   - `extraction/local_llm_fallback.py` (Ollama fallback)
   - `intelligence/embeddings.py` (fastembed ONNX pipeline)
   - `search/` engine components & RRF rank fusion.
3. **Update `task.md`** as work progresses.

## Suggested Skills
- `tdd` – drive red-green-refactor cycles for entity resolution and extraction.
- `python-performance-optimization` – profile heavy processing when scaling.

---
*All sensitive data has been redacted.*
