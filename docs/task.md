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

- `[/]` **Ingestion & Processing Pipeline**
  - `[x]` `ingestion/parsers/pdf_parser.py` (PyMuPDF, pdfplumber, OCR)
  - `[x]` `ingestion/parsers/docx_parser.py` (python-docx)
  - `[x]` `ingestion/parsers/email_parser.py` (email parser)
  - `[x]` `ingestion/chunker.py` (Section-aware chunker)
  - `[ ]` `ingestion/entity_resolution.py` (Tier 1 & Tier 2 matching)

- `[ ]` **Intelligence, Fact Extraction & Search Components**
  - `[ ]` `extraction/deterministic_ner.py` (SpaCy NER, Regex)
  - `[ ]` `extraction/local_llm_fallback.py` (Ollama fallback)
  - `[ ]` `intelligence/embeddings.py` (fastembed ONNX pipeline)
  - `[ ]` `search/ast_parser.py` (Strict search AST to SQL)
  - `[ ]` `search/hybrid_searcher.py` (Filter-then-rank engine)
  - `[ ]` `search/rank_fusion.py` (Reciprocal Rank Fusion)
  - `[ ]` `search/reranker.py` (ONNX Cross-Encoder re-ranker)
  - `[ ]` `intelligence/explainer.py` (Match Rationale scorecard)

- `[ ]` **CRM Timeline & Operational Core**
  - `[ ]` `crm/timeline_ledger.py` (Event-sourced logger)
  - `[ ]` `crm/state_machine.py` (Candidate stage machine)
  - `[ ]` `backups/backup_manager.py` (SQLite backup, CAS sync)
