# Candidate Intelligence Platform (CIP) - Implementation Plan

**Goal**: Build a production-grade Candidate Intelligence Platform in Python based on the finalized Architecture Design Document (ADD). The platform runs locally at $0 cost, scales to 100,000+ candidates, uses embedded SQLite (WAL+FTS5) & LanceDB, implements Content-Addressable Storage (CAS), a two-tier entity resolution engine, hierarchical section-aware chunking, hybrid search (strict AST + ONNX dense embeddings), RRF ranking, match rationale explainer, and event-sourced CRM timeline ledger.

---

## User Review Required

> [!IMPORTANT]
> The Architecture Design Document (ADD) has been fully generated and approved across all 4 decision frontiers.  
> Detailed specification artifact available at: [architecture_design_document.md](file:///C:/Users/bafna_ci/.gemini/antigravity-ide/brain/9890c480-b8f3-4043-a614-803095958025/architecture_design_document.md)  
> Architectural exploration artifact available at: [architecture_design_tree.md](file:///C:/Users/bafna_ci/.gemini/antigravity-ide/brain/9890c480-b8f3-4043-a614-803095958025/architecture_design_tree.md)

---

## Proposed Changes

### Core Data & Storage Components

#### [NEW] `config/settings.py`
Application configuration, database paths, CAS root directory, embedding model identifiers, and entity resolution thresholds.

#### [NEW] `config/database.py`
SQLite database initialization script setting PRAGMA WAL mode, FTS5 virtual tables, and connection pools.

#### [NEW] `storage/cas.py`
Content-Addressable Storage (CAS) file store manager implementing SHA-256 sharding and read-only file lock permissioning.

#### [NEW] `storage/db_models.py`
Complete SQLite DDL schema creation script (`candidates`, `resume_versions`, `candidate_claims`, `candidate_timeline_events`, `entity_resolution_audit`, `candidate_fts`, `claims_fts`).

#### [NEW] `storage/vector_store.py`
LanceDB embedded vector table manager (`candidate_sections` table schema, index builder, and query vector searcher).

---

### Ingestion & Processing Pipeline

#### [NEW] `ingestion/parsers/pdf_parser.py`
Multi-stage PDF parser using PyMuPDF + pdfplumber, with Tesseract OCR fallback and bounding box layout JSON exporter.

#### [NEW] `ingestion/parsers/docx_parser.py`
Word document paragraph, table, and structure parser.

#### [NEW] `ingestion/parsers/email_parser.py`
Email (.msg / .eml) parser extracting body, attachments, and headers.

#### [NEW] `ingestion/chunker.py`
Hierarchical section-aware text chunker with context injection (Candidate ID + Section Name).

#### [NEW] `ingestion/entity_resolution.py`
Two-tier entity resolution engine (Tier 1 deterministic exact key matching; Tier 2 probabilistic graph match scoring with auto-merge thresholding and recruiter review queue).

---

### Intelligence, Fact Extraction & Search Components

#### [NEW] `extraction/deterministic_ner.py`
Deterministic fact extractor using SpaCy NER + Regex + dictionary lookups for contact info, dates, titles, skills.

#### [NEW] `extraction/local_llm_fallback.py`
Ollama / llama-cpp-python fallback wrapper for structured JSON extraction on complex unstructured resume blocks.

#### [NEW] `intelligence/embeddings.py`
`fastembed` ONNX embedding pipeline for `BAAI/bge-small-en-v1.5` dense vector generation.

#### [NEW] `search/ast_parser.py`
Strict search AST parser compiling boolean/relational filter queries into SQLite SQL queries.

#### [NEW] `search/hybrid_searcher.py`
Two-stage filter-then-rank engine combining SQLite FTS5 pre-filtering with LanceDB vector search.

#### [NEW] `search/rank_fusion.py`
Reciprocal Rank Fusion (RRF) algorithm combining lexical and vector dense ranks.

#### [NEW] `search/reranker.py`
ONNX Cross-Encoder re-ranker (`ms-marco-MiniLM-L-6-v2`) fine-tuning top-50 results.

#### [NEW] `intelligence/explainer.py`
Match Rationale scorecard builder generating exact text offsets, line numbers, matched claims, and scorecards.

---

### CRM Timeline & Operational Core

#### [NEW] `crm/timeline_ledger.py`
Event-sourced timeline logger recording candidate lifecycle events.

#### [NEW] `crm/state_machine.py`
Candidate recruitment stage state machine.

#### [NEW] `backups/backup_manager.py`
SQLite live `sqlite3_backup` runner, CAS incremental sync, and Cryptographic Manifest auditor.

---

## Verification Plan

### Automated Tests
- Unit tests for SHA-256 CAS storage deduplication (`tests/test_cas.py`).
- Schema validation & DDL integrity tests for SQLite + FTS5 (`tests/test_database.py`).
- Tier 1 & Tier 2 Entity Resolution scoring test suite (`tests/test_entity_resolution.py`).
- Vector indexing & LanceDB query performance tests (`tests/test_vector_store.py`).
- AST Parser & Hybrid Search RRF ranking tests (`tests/test_hybrid_search.py`).

### Manual Verification
- End-to-end ingest of sample PDF/DOCX resumes to verify CAS storage, plain text extraction, layout JSON, fact/inference claims split, and LanceDB section vector generation.
- Execute hybrid search query (strict boolean + semantic intent) and verify the generated **Match Rationale Scorecard** and precise line attribution highlights.
