> 
> **ALREADY IMPLEMENTED** — This is already implemented and in codebase. Do NOT take this document as context / pending work unless user explicitly says otherwise.

# Architecture Deepening Opportunities

**Status:** `COMPLETED`  
**Tracker:** See `docs/task.md` for completed ticket references.

---

## Summary of Deepening Opportunities

| # | Item | Status | Completed In | Focus Area |
|---|---|---|---|---|
| **1** | Resume Intake Pipeline Unified | **COMPLETED** | Issue #12 (`intake.py`) | Single shared ingestion pipeline for uploads, streaming, reprocess, and bulk scripts |
| **2** | Search DSL Seam & Soft Filters | **COMPLETED** | Issues #36 & #38 | Soft semantic job title matching, S-curve YoE scoring, clean text passing |
| **3** | Database Housekeeping Knowledge Scattered | **COMPLETED** | `StorageIndexWriter` (`storage/index_writer.py`) | Consolidate table literals, DDL, and vector/FTS writers into Storage IndexWriter |
| **4** | Hybrid Extractor Internals & spaCy Seam | **COMPLETED** | `hybrid_extractor.py` & `deterministic_ner.py` | Injectable NER model loader, clean `ExtractionOutcome` dataclass boundary, fast mock tests |
| **5** | CandidateService Helper Dissolution | **COMPLETED** | `candidate_store.py` | Merge static methods into unified storage and index layers, deleted `candidate_service.py` |

---

## 1. Resume Intake Pipeline Unified (`COMPLETED`)

- **Delivered**: `src/candidate_intelligence_platform/ingestion/intake.py` created with `ingest_file()` and `reprocess_text()`.
- **Impact**: All 4 entry points (`/upload`, `/upload-stream`, reprocess endpoints, `bulk_ingest.py`) use the single unified pipeline. Entity resolution, deduplication, and classification now run consistently everywhere.

---

## 2. Search DSL Seam & Soft Filters (`COMPLETED`)

- **Delivered**: `ast_parser.py`, `hybrid_searcher.py`, `rank_fusion.py`, `CandidateList.jsx`.
- **Impact**: Soft job title search surfaces semantic relatives (e.g. `Backend Engineer` matches `Software Engineer`) with `+20%` exact title bonus; strict mode available via `exact_title` toggle; YoE uses smooth Sigmoid penalty.

---

## 3. Database Housekeeping Knowledge Scattered (`COMPLETED`)

### 3.1 Problem
Database table names, column names, record shapes, and model wiring are still duplicated across multiple files:
- `"candidate_vectors"` table literal appears in `candidate_service.py`, `candidates.py`, `bulk_ingest.py`, `hybrid_searcher.py`.
- FTS table column definitions exist in `db_models.py` and `conftest.py`.
- `settings.embedding_model` is not uniformly plumbed into vector store init.

### 3.2 Target Refactor: `StorageIndexWriter` Module
Create a unified indexing interface in `storage/index_writer.py`:

```python
class StorageIndexWriter:
    """Single owner of SQLite FTS5 and LanceDB vector index synchronization."""
    
    def __init__(self, db_session, vector_db):
        self.db = db_session
        self.vector_db = vector_db
        
    def write_candidate_indices(self, candidate: Candidate, resume_version: ResumeVersion, raw_text: str) -> None:
        """Atomic write to SQLite FTS5 table and LanceDB vector chunks.
        
        If vector write fails after FTS write, roll back DB transaction and log error 
        to ensure both stores stay strictly consistent without orphaned records.
        """
        try:
            self._update_fts(candidate, raw_text)
            self._update_vectors(candidate.id, resume_version.id, raw_text)
        except Exception as e:
            self.db.rollback()
            logger.error("index_writer_sync_failed", candidate_id=candidate.id, error=str(e))
            raise
        
    def delete_candidate_indices(self, candidate_id: str) -> None:
        """Atomic deletion from both search stores."""
        try:
            self._delete_fts(candidate_id)
            self._delete_vectors(candidate_id)
        except Exception as e:
            self.db.rollback()
            logger.error("index_writer_delete_failed", candidate_id=candidate_id, error=str(e))
            raise
```

---

## 4. Hybrid Extractor Internals & spaCy Seam (`COMPLETED`)

### 4.1 Problem
- `deterministic_ner.py` loads spaCy at module import time (`nlp = spacy.load("en_core_web_sm")`), which slows down test imports and makes mocking difficult.
- `hybrid_extractor.py` exports 8 callables, leaking internal helpers across module boundaries.

### 4.2 Target Refactor
1. Move spaCy model loading behind a lazy singleton (`get_nlp_model()`) with an injection hook for unit tests:
   ```python
   def get_nlp(mock_model=None):
       global _NLP_INSTANCE
       if mock_model is not None:
           return mock_model
       if _NLP_INSTANCE is None:
           _NLP_INSTANCE = spacy.load("en_core_web_sm")
       return _NLP_INSTANCE
   ```
2. Unify extraction output into a single strongly-typed dataclass:
   ```python
   @dataclass(frozen=True)
   class ExtractionOutcome:
       first_name: str | None
       last_name: str | None
       current_title: str | None
       current_city: str | None
       emails: list[str]
       phones: list[str]
       claims: list[dict]
       confidence_score: float
       tier_used: str  # "TIER_1_NER" | "TIER_2_LLM"
   ```

---

## 5. CandidateService Helper Dissolution (`COMPLETED`)

### 5.1 Problem
`api/services/candidate_service.py` is a shallow helper with 3 static methods that contain bare `except: pass` blocks and leak commit transactions.

### 5.2 Target Refactor
- Dissolve `CandidateService.update_fts_index` and `update_vector_index` into `StorageIndexWriter` (Item #3).
- Move cascade delete logic into `storage/candidate_store.py` with explicit transaction boundaries and error logging.
- Delete `api/services/candidate_service.py`.
