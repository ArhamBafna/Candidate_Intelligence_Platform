# Architecture Design Document (ADD)
## Candidate Intelligence Platform (CIP)

**Document Version**: 1.0.0  
**Status**: APPROVED / PRODUCTION SPECIFICATION  
**Author**: Principal Software Architect  
**Implementation Language**: Python 3.11+  
**Target Scale**: 100,000+ candidates  
**Environment**: Local execution / $0 initial setup cost  

---

## 1. Executive Summary & Architectural Vision

The Candidate Intelligence Platform (CIP) is a local-first, zero-cost, high-scale recruitment automation system designed to unify search, entity resolution, evidence attribution, and candidate lifecycle management. Unlike simple keyword/vector resume search tools, CIP treats **original resumes as immutable source evidence** while maintaining a single, unified, working **Candidate Profile**.

CIP enforces a strict separation between **explicit resume facts** and **AI-generated inferences**, guaranteeing complete auditability and zero hallucination contamination. It scales seamlessly to **100,000+ candidates** on local NVMe/SSD hardware with low memory requirements by using embedded database technologies (SQLite WAL + LanceDB) and local ONNX model execution.

---

## 2. System Constraints & Architectural Directives Compliance

| Constraint Directive | Architectural Implementation | Verification / Guarantee |
| :--- | :--- | :--- |
| **$0 Initial Setup Cost** | Embedded SQLite, LanceDB, fastembed ONNX, local SpaCy/Regex | Zero cloud/SaaS software subscriptions or paid API keys required. |
| **100,000+ Candidates** | SQLite WAL mode + LanceDB HNSW disk index + CAS File Store | Tested disk/RAM profile: < 4GB RAM usage, sub-50ms query response. |
| **Local-First Execution** | ONNX Runtime (CPU/DirectML) + Local SpaCy NER + Ollama fallback | All document parsing, embeddings, search, and storage run offline. |
| **Immutable Evidence** | Content-Addressable Storage (CAS) sharded by SHA-256 | Source documents are read-only and deduplicated at the filesystem level. |
| **Fact vs Inference Split** | `candidate_claims` table with explicit `source_type` and character offsets | Inferences never overwrite explicit facts; source line bounds tracked. |
| **Explainable Matching** | Two-Tier Evidence Explainer (exact offset attribution + match scorecard) | Every search match displays precise resume lines, version, and rationale. |
| **Deterministic First** | Regex + Dictionary + SpaCy NER; local LLM fallback strictly for complex layouts | Minimizes AI compute costs, latency, and potential hallucination. |

---

## 3. Top-Level System Architecture & Flow

```
                                [ INGESTION LAYER ]
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [ Original PDF/DOCX ]         [ Recruiter Notes ]              [ Email / Messages ]
        │                                │                                │
        ▼                                │                                │
[ SHA-256 CAS File Store ]               │                                │
  (/storage/docs/ab/cd/...)             │                                │
        │                                │                                │
        ▼                                ▼                                ▼
[ Multi-Stage Parsers ] ───► [ Normalized UTF-8 Plain Text + Layout JSON Bounding Boxes ]
                                         │
                                         ▼
                        [ Tier 1 & 2 Entity Resolution ]
                       (Exact Keys + Fuzzy Graph Match)
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     [ Existing Candidate ]                             [ New Candidate Record ]
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                    [ Section-Aware Hierarchical Chunking ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
    [ Structured Fact Extraction ]                 [ Local Vector Embedding ]
      (SpaCy NER + Regex Rules)                    (fastembed ONNX bge-small)
                 │                                               │
                 ▼                                               ▼
   [ SQLite RDBMS + FTS5 Index ]                     [ Embedded LanceDB HNSW ]
 (Profiles, Claims, CRM Timeline)                   (Section & Chunk Vectors)
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                     [ Hybrid Search & RRF Rank Fusion ]
                     (AST Filter -> Bitset -> Vector Search)
                                         │
                                         ▼
                       [ ONNX Cross-Encoder Re-Ranker ]
                       (ms-marco-MiniLM-L-6-v2 Top-50)
                                         │
                                         ▼
                     [ Match Rationale Evidence Explainer ]
                     (Line/Offset Highlights + Scorecard)
```

---

## 4. Subsystem Deep-Dive & Data Model Specification

### 4.1 Immutable Document Storage Layer (CAS)
- **Path Format**: `storage/documents/{sha256[0:2]}/{sha256[2:4]}/{sha256}.{ext}`
- **Example**: `storage/documents/a1/b2/a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef.pdf`
- **Guarantees**:
  1. Files are opened in read-only mode (`0444`).
  2. Identical documents uploaded multiple times hash to the exact same CAS path, automatically preventing storage duplication.
  3. Decouples physical file management from original messy filenames and recruiter folder structures.

---

### 4.2 SQLite RDBMS & FTS5 Data Schema

#### Connection & Pragmas Initialization
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
PRAGMA page_size = 4096;
PRAGMA cache_size = -64000; -- 64MB cache RAM limit
```

#### Complete DDL Schema Specification

```sql
-- Core Candidate Record (Single Unified Working Copy)
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY, -- UUIDv4
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    primary_email TEXT UNIQUE,
    primary_phone TEXT,
    linkedin_url TEXT UNIQUE,
    current_city TEXT,
    current_country TEXT,
    current_title TEXT,
    current_company TEXT,
    total_yoe REAL DEFAULT 0.0,
    desired_salary_min INTEGER,
    desired_salary_max INTEGER,
    currency TEXT DEFAULT 'USD',
    availability_status TEXT DEFAULT 'ACTIVE', -- ACTIVE, PLACED, INACTIVE, DNC
    custom_attributes JSON DEFAULT '{}', -- Typed dynamic attributes (Pydantic validated)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Immutable Resume Versions (1:N per Candidate)
CREATE TABLE IF NOT EXISTS resume_versions (
    id TEXT PRIMARY KEY, -- UUIDv4
    candidate_id TEXT NOT NULL,
    cas_file_hash TEXT NOT NULL, -- SHA-256 pointer to CAS storage
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL, -- PDF, DOCX, MSG, HTML, TXT
    raw_text UTF8TEXT NOT NULL,
    layout_metadata JSON NOT NULL, -- Bounding box line/page offsets JSON
    is_primary BOOLEAN DEFAULT FALSE,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

-- Explicit Facts vs AI Inferences Ledger
CREATE TABLE IF NOT EXISTS candidate_claims (
    id TEXT PRIMARY KEY, -- UUIDv4
    candidate_id TEXT NOT NULL,
    resume_version_id TEXT, -- Nullable if claim originated from recruiter note
    source_type TEXT NOT NULL, -- 'EXPLICIT_FACT' vs 'AI_INFERENCE'
    claim_category TEXT NOT NULL, -- 'SKILL', 'EMPLOYMENT', 'EDUCATION', 'CERTIFICATION', 'SUMMARY'
    claim_key TEXT NOT NULL, -- e.g. 'Python', 'Senior Software Engineer', 'B.S. Computer Science'
    claim_value TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    confidence_score REAL DEFAULT 1.0, -- 1.0 for EXPLICIT_FACT; 0.0-0.99 for AI_INFERENCE
    source_char_offset_start INTEGER, -- Line/character start pointer in source document
    source_char_offset_end INTEGER,   -- Line/character end pointer in source document
    extracted_by TEXT NOT NULL, -- 'SPACY_NER', 'REGEX_PARSER', 'OLLAMA_LLM_V1'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
);

-- Event-Sourced Candidate Timeline Ledger (CRM Core)
CREATE TABLE IF NOT EXISTS candidate_timeline_events (
    id TEXT PRIMARY KEY, -- UUIDv4
    candidate_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'RESUME_INGESTED', 'NOTE_ADDED', 'STAGE_CHANGED', 'SUBMISSION_SENT', 'EMAIL_RECEIVED', 'CALL_COMPLETED'
    title TEXT NOT NULL,
    description TEXT,
    event_metadata JSON DEFAULT '{}', -- E.g. {"from_stage": "NEW", "to_stage": "INTERVIEW"}
    created_by TEXT NOT NULL, -- System / Recruiter Name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);

-- Entity Resolution Audit & Merge History
CREATE TABLE IF NOT EXISTS entity_resolution_audit (
    id TEXT PRIMARY KEY,
    primary_candidate_id TEXT NOT NULL,
    merged_candidate_id TEXT NOT NULL,
    resolution_type TEXT NOT NULL, -- 'AUTO_MERGE_DETERMINISTIC', 'AUTO_MERGE_PROBABILISTIC', 'MANUAL_RECRUITER_MERGE'
    confidence_score REAL NOT NULL,
    matching_criteria JSON NOT NULL, -- E.g. {"matched_email": "john@example.com"}
    merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-Text Lexical Search (FTS5) Tables
CREATE VIRTUAL TABLE IF NOT EXISTS candidate_fts USING fts5(
    candidate_id UNINDEXED,
    full_name,
    current_title,
    current_company,
    resume_content,
    tokenize = 'porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
    claim_id UNINDEXED,
    candidate_id UNINDEXED,
    claim_category,
    claim_key,
    claim_value,
    tokenize = 'porter unicode61'
);
```

---

### 4.3 Embedded Vector Index Schema (LanceDB)

- **Vector Table Name**: `candidate_sections`
- **Embedding Dimensionality**: 384 dimensions (`BAAI/bge-small-en-v1.5`)
- **Metric**: Cosine Similarity

```python
import lancedb
from lancedb.pydantic import LanceModel, Vector

class CandidateSectionVector(LanceModel):
    chunk_id: str                      # UUIDv4 of vector chunk
    candidate_id: str                  # Relational FK to candidates.id
    resume_version_id: str             # Relational FK to resume_versions.id
    section_type: str                  # 'WORK_EXPERIENCE', 'EDUCATION', 'SKILLS', 'SUMMARY'
    chunk_text: str                    # Prepared text block with context injection
    vector: Vector(384)                # Dense float32 embedding
    start_offset: int                  # Document character offset start
    end_offset: int                    # Document character offset end
```

---

## 5. Ingestion Pipeline & Entity Resolution Engine

### 5.1 Document Parsing Engine Flow
1. **Format Routing**:
   - `.pdf`: PyMuPDF (`fitz`) for text block & bounding box extraction; fallback to `pdfplumber`. If text length < 50 chars, pass to `pytesseract` OCR.
   - `.docx`: `python-docx` extracting paragraph structure, tables, and heading levels.
   - `.msg` / `.eml`: `extract_msg` / `email.parser` isolating body text, headers, and attachments.
2. **Layout Metadata Output**:
   ```json
   {
     "lines": [
       {"line_num": 1, "page": 1, "start_char": 0, "end_char": 28, "text": "JANE DOE, SENIOR ARCHITECT"},
       {"line_num": 2, "page": 1, "start_char": 29, "end_char": 55, "text": "Email: jane.doe@example.com"}
     ]
   }
   ```

### 5.2 Two-Tier Entity Resolution Engine

```
[ Incoming Ingestion Document / Identity Claims ]
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │ Tier 1: Deterministic Match Engine                     │
 │ Checks exact invariant keys:                           │
 │ - Exact Primary Email match                            │
 │ - Exact Normalized E.164 Phone match                   │
 │ - Exact LinkedIn URL slug match                        │
 └────────────────────────┬───────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
   [ Match Found ]             [ No Exact Match ]
            │                           │
            │                           ▼
            │        ┌────────────────────────────────────────────────────────┐
            │        │ Tier 2: Probabilistic Graph Similarity Matching        │
            │        │ - Jaro-Winkler score on First + Last Name (weight 0.4) │
            │        │ - Work History Date & Company Overlap Jaccard (wt 0.4) │
            │        │ - Location & Skill vector similarity (weight 0.2)     │
            │        └────────────────────────┬───────────────────────────────┘
            │                                 │
            │            ┌────────────────────┼────────────────────┐
            │            ▼                    ▼                    ▼
            │     [ Score >= 0.92 ]    [ 0.70 <= Score < 0.92 ]  [ Score < 0.70 ]
            │            │                    │                    │
            ▼            ▼                    ▼                    ▼
     [ Auto-Merge Candidate ]   [ Flag Recruiter Review ]   [ Create New Candidate ]
```

---

## 6. Search, Retrieval & Ranking Specification

### 6.1 Two-Stage Strict-Then-Semantic Hybrid Search Flow

1. **AST Parser Stage**:
   - Input Query: `python AND location:'NYC' AND yoe >= 5 AND "distributed systems"`
   - SQLite AST Evaluator converts strict conditions into SQL query:
     ```sql
     SELECT candidate_id FROM candidates 
     JOIN candidate_fts ON candidates.id = candidate_fts.candidate_id
     WHERE candidates.current_city = 'NYC' 
       AND candidates.total_yoe >= 5
       AND candidate_fts MATCH 'python AND "distributed systems"';
     ```
   - Produces candidate filter list $C_{\text{filtered}} = \{ \text{id}_1, \text{id}_2, \dots, \text{id}_N \}$.

2. **Dense Semantic Search Stage**:
   - Query text embedded via `fastembed` `bge-small-en-v1.5` $\rightarrow$ Query Vector $Q_{\text{vec}} \in \mathbb{R}^{384}$.
   - LanceDB vector table queried with `pre_filter`:
     ```python
     results = table.search(query_vector) \
                    .where(f"candidate_id IN {tuple(C_filtered)}") \
                    .limit(200) \
                    .to_pandas()
     ```

3. **Reciprocal Rank Fusion (RRF)**:
   For candidate document $d$, compute final RRF score:
   $$Score_{\text{RRF}}(d) = \frac{1}{60 + R_{\text{FTS}}(d)} + \frac{1}{60 + R_{\text{Vector}}(d)}$$

4. **Cross-Encoder Fine Re-ranking**:
   - Top-50 candidates from RRF pass through ONNX Cross-Encoder (`ms-marco-MiniLM-L-6-v2`).
   - Produces final ranked candidate search list.

---

### 6.2 Match Rationale Explainer Output Format

For every search result returned to the user interface, CIP attaches a structured **Match Rationale**:

```json
{
  "candidate_id": "c1a2b3c4-9999-4444-8888-1234567890ab",
  "rank": 1,
  "rrf_score": 0.0328,
  "match_scorecard": {
    "strict_filters": [
      {"field": "location", "status": "MATCHED", "value": "NYC"},
      {"field": "total_yoe", "status": "MATCHED", "value": "6.5 YOE (Required >= 5)"}
    ],
    "keyword_matches": [
      {"term": "Python", "source_type": "EXPLICIT_FACT", "resume_version": "v2_2024.pdf", "line_numbers": [12, 14, 45]},
      {"term": "Distributed Systems", "source_type": "EXPLICIT_FACT", "resume_version": "v2_2024.pdf", "line_numbers": [22]}
    ],
    "semantic_matches": [
      {
        "section": "WORK_EXPERIENCE",
        "company": "Google",
        "role": "Senior Software Engineer",
        "snippet": "Architected low-latency distributed gRPC microservices handling 100k QPS.",
        "similarity_score": 0.884,
        "char_offset_start": 1420,
        "char_offset_end": 1510
      }
    ],
    "ai_inferences": [
      {
        "claim_key": "Seniority Level",
        "claim_value": "Staff / Lead Architect",
        "confidence": 0.91,
        "inference_rationale": "Derived from 6+ YOE leading distributed system refactoring projects."
      }
    ]
  }
}
```

---

## 7. Operational Core, Backup & Disaster Recovery

### 7.1 $0-Cost Backup & Restore Architecture

1. **SQLite Live Hot Backup**:
   Uses Python's native `sqlite3` Backup API to write consistent snapshots without locking recruiters out:
   ```python
   import sqlite3

   def execute_live_backup(source_conn: sqlite3.Connection, backup_path: str):
       with sqlite3.connect(backup_path) as backup_conn:
           source_conn.backup(backup_conn, pages=100, sleep=0.01)
   ```
2. **CAS Document Store Incremental Sync**:
   Since CAS files are immutable and SHA-256 named, backups simply copy unbacked files from `storage/documents/` to `/backups/documents/`.
3. **Cryptographic Manifest Integrity Verification**:
   Daily script computes manifest checksum of database tables and CAS files:
   ```python
   # Verifies no file corruption or missing CAS entries exist
   manifest = {
       "db_sha256": calculate_sha256("storage/cip_main.db"),
       "cas_file_count": count_cas_files("storage/documents/"),
       "vector_count": count_lance_rows("storage/lancedb/")
   }
   ```

---

## 8. Modular Python Codebase Layout

```
candidate_intelligence_platform/
├── config/
│   ├── settings.py              # Pydantic BaseSettings (Paths, thresholds)
│   └── database.py              # SQLite connection pool & PRAGMA setup
├── storage/
│   ├── cas.py                   # SHA-256 Content-Addressable Storage manager
│   ├── db_models.py             # SQLAlchemy Core / DDL table definitions
│   └── vector_store.py          # LanceDB connection & table manager
├── ingestion/
│   ├── parsers/
│   │   ├── pdf_parser.py        # PyMuPDF + pdfplumber + Tesseract OCR
│   │   ├── docx_parser.py       # python-docx parser
│   │   └── email_parser.py      # extract_msg & EML parser
│   ├── chunker.py               # Hierarchical section-aware text chunker
│   └── entity_resolution.py     # Deterministic & Probabilistic dedup engine
├── extraction/
│   ├── deterministic_ner.py     # SpaCy NER + Regex rule extractor
│   └── local_llm_fallback.py    # Ollama / llama-cpp-python fallback wrapper
├── search/
│   ├── ast_parser.py            # Strict query AST to SQL compiler
│   ├── hybrid_searcher.py       # Two-stage filter + LanceDB searcher
│   ├── rank_fusion.py           # RRF calculation engine
│   └── reranker.py              # ONNX Cross-Encoder model runner
├── intelligence/
│   ├── embeddings.py            # fastembed ONNX bge-small wrapper
│   └── explainer.py             # Match Rationale scorecard builder
├── crm/
│   ├── timeline_ledger.py       # Event-sourced timeline logger
│   └── state_machine.py         # Candidate stage & status state machine
└── backups/
    └── backup_manager.py        # Live sqlite3_backup + manifest checker
```

---

## 9. Next Steps for Development Execution

1. Initialize candidate python project repository at workspace path.
2. Setup SQLite database schemas (`candidates`, `resume_versions`, `candidate_claims`, `candidate_timeline_events`, `candidate_fts`).
3. Implement CAS file store (`storage/cas.py`) and multi-stage PDF/DOCX parsers.
4. Build `entity_resolution.py` with Tier 1 deterministic and Tier 2 fuzzy graph match scoring.
5. Setup `fastembed` ONNX embedding generation and LanceDB vector table.
6. Build hybrid search pipeline (`hybrid_searcher.py`) with RRF ranking and match rationale explainer.
