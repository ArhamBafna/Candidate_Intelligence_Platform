# Candidate Intelligence Platform (CIP) - Tasks

- `[x]` **Project Initialization**
  - `[x]` Setup dependency management and virtual environment
  - `[x]` Configure testing framework

- `[x]` **Core Data & Storage Components**
  - `[x]` `config/settings.py` (App configuration, DB paths, CAS root)
  - `[x]` `config/database.py` (SQLite WAL mode, connection pools)
  - `[x]` `storage/cas.py` (Content-Addressable Storage, SHA-256)
  - `[x]` `storage/db_models.py` (SQLite DDL schema)
  - `[x]` `storage/vector_store.py` (LanceDB embedded vector table manager)

- `[x]` **Ingestion & Processing Pipeline**
  - `[x]` `ingestion/parsers/pdf_parser.py` (PyMuPDF, pdfplumber, OCR)
  - `[x]` `ingestion/parsers/docx_parser.py` (python-docx)
  - `[x]` `ingestion/parsers/email_parser.py` (email parser)
  - `[x]` `ingestion/chunker.py` (Section-aware chunker)
  - `[x]` `ingestion/entity_resolution.py` (Tier 1 & Tier 2 matching)

- `[x]` **Intelligence, Fact Extraction & Search Components**
  - `[x]` `extraction/deterministic_ner.py` (SpaCy NER, Regex)
  - `[x]` `extraction/local_llm_fallback.py` (Ollama fallback)
  - `[x]` `intelligence/embeddings.py` (fastembed ONNX pipeline)
  - `[x]` `search/ast_parser.py` (Strict search AST to SQL)
  - `[x]` `search/hybrid_searcher.py` (Filter-then-rank engine)
  - `[x]` `search/rank_fusion.py` (Reciprocal Rank Fusion)
  - `[x]` `search/reranker.py` (ONNX Cross-Encoder re-ranker)
  - `[x]` `intelligence/explainer.py` (Match Rationale scorecard)

- `[x]` **CRM Timeline & Operational Core**
  - `[x]` `crm/timeline_ledger.py` (Event-sourced logger)
  - `[x]` `crm/state_machine.py` (Candidate stage machine)
  - `[x]` `backups/backup_manager.py` (SQLite backup, CAS sync)

- `[ ]` **API & Recruiter Interface Layer**
  - `[x]` `api/main.py` (FastAPI application setup, CORS, error handling)
  - `[x]` `api/dependencies.py` (Dependency Injection for DB, LanceDB, CAS)
  - `[x]` `api/schemas/` (Pydantic request/response models)
  - `[x]` `api/routes/candidates.py` (CRUD for candidates, timeline events)
  - `[x]` `api/routes/search.py` (Hybrid search and reranking endpoints)
  - `[x]` `ui/` (Frontend UI foundation using Vite + React + Tailwind CSS)
  - `[x]` `tests/test_api_*.py` (TDD tests with FastAPI TestClient)
