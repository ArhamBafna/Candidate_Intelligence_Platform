# Architecture Design Tree: Candidate Intelligence Platform

**Target System**: Enterprise Candidate Intelligence Platform (Automation, Semantic & Strict Search, Intelligence System)  
**Scale Target**: 100,000+ candidates  
**Constraints**: $0 setup cost, local-first, minimal AI reliance, deterministic scripts, local embedding models, Python-based.

---

## Architecture Design Tree Overview

```
Candidate Intelligence Platform
├── 1. Data & Storage Layer
│   ├── 1.1 Operational RDBMS (Structured candidate profiles, notes, history)
│   ├── 1.2 Immutable Document Store (Content-addressable file storage)
│   ├── 1.3 Vector & Lexical Index Engine (Hybrid local search)
│   └── 1.4 Audit & Provenance Ledger (Fact vs. Inference tracking)
├── 2. Ingestion & Data Normalization Pipeline
│   ├── 2.1 File Extraction & Parsing Engine (PDF/DOCX/MSG/HTML)
│   ├── 2.2 Entity Resolution & De-duplication Engine
│   ├── 2.3 Structured Fact Extractor & AI Inference Separator
│   └── 2.4 Schema Evolution & Migration System
├── 3. Intelligence & AI Subsystems
│   ├── 3.1 Local Embedding Pipeline (ONNX / Sentence-Transformers)
│   ├── 3.2 Dynamic Hierarchical Chunking Engine
│   ├── 3.3 Offline / On-Device Local LLM Extraction (Ollama / llama.cpp)
│   └── 3.4 Evidence Attribution & Match Rationale Engine
├── 4. Search, Retrieval & Ranking Pipeline
│   ├── 4.1 Strict AST Filtering Engine (SQL + Boolean Logic)
│   ├── 4.2 Local Dense Semantic Search (Vector HNSW)
│   ├── 4.3 Hybrid Rank Fusion & Re-ranking (BM25 + Cosine + Cross-Encoder)
│   └── 4.4 Match Rationale Explainer Output
└── 5. Operational Core & Scalability
    ├── 5.1 Python Modular Architecture & Plugin System
    ├── 5.2 Backup, Restore & Disaster Recovery Strategy
    ├── 5.3 Workflow State Machine & Recruiter Automation Triggers
    └── 5.4 Local System Resource & Cache Management
```

---

## Decision Log & Frontier Status

### Settled Decisions
- [x] Resumes are immutable source evidence.
- [x] Candidate profile is a single working copy with 1:N resume versions.
- [x] Folder names are treated as weak metadata.
- [x] Explicit facts and AI inferences are strictly separated.
- [x] Search requires hybrid modes (strict + semantic) with explainability.
- [x] Deployment cost = $0, Python-based, local-first execution.
- [x] **Database Engine**: SQLite with WAL mode & FTS5 (embedded RDBMS).
- [x] **Vector Search Engine**: Embedded LanceDB / Qdrant Local.
- [x] **Document Storage**: Content-Addressable Storage (CAS) with SHA-256 hash sharding.
- [x] **Schema & Provenance**: Relational tables + `candidate_claims` table with explicit `source_type` (`EXPLICIT_FACT` vs `AI_INFERENCE`), character-level offset provenance, confidence score, and timestamp.
- [x] **Document Parsing**: Multi-stage deterministic parsing (PyMuPDF/pdfplumber, python-docx, extract_msg/email, Tesseract OCR fallback) emitting Plain Text + Layout JSON.
- [x] **Entity Resolution**: Two-tier engine (Tier 1 deterministic exact keys; Tier 2 probabilistic graph matching with auto-merge >0.92 & Recruiter Review Queue).
- [x] **Chunking Strategy**: Hierarchical Section-Aware Chunking with Candidate ID + Section Name context injection.
- [x] **Fact Extraction**: Deterministic-first pipeline (SpaCy NER + Regex + dictionary lookups, local LLM fallback via Ollama/llama-cpp-python for complex sections).
- [x] **Local Embeddings**: ONNX-accelerated (`fastembed` / `onnxruntime`) with `bge-small-en-v1.5` / `bge-base-en-v1.5`.
- [x] **Search Execution**: Two-stage Filter-Then-Rank (SQLite FTS5 strict filtering pre-filtering LanceDB vector search).
- [x] **Rank Fusion**: Reciprocal Rank Fusion (RRF) + ONNX Cross-Encoder re-ranker (`ms-marco-MiniLM-L-6-v2`) on top-50 results.
- [x] **Match Rationale**: Two-tier evidence explainer (Tier 1 exact matched text/line offsets; Tier 2 structured match scorecard with on-demand local LLM summary).
- [x] **Recruiter Workflow & CRM State**: Event-Sourced Timeline Ledger (`candidate_timeline_events`) + Relational CRM State Machine.
- [x] **Schema Evolution**: Alembic version-controlled SQL migrations + typed `custom_attributes` JSON with Pydantic runtime validation.
- [x] **Backup & Recovery**: SQLite Online Backup API (`sqlite3_backup`) + SHA-256 CAS document sync + Cryptographic Manifest checksum verification.
- [x] **Architecture Completeness**: Architecture design tree is 100% complete across all 4 frontiers. Ready for Architecture Design Document (ADD).

---

## Final Status
Architecture Exploration Stage: **COMPLETE**  
Next Deliverable: **Architecture Design Document (ADD)**




