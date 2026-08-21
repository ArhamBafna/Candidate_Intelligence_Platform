# Session Handoff: Bulk Resume Ingestion & Document Classifier (August 2026)

## Overview
This session designed, implemented, and verified an automated, local-first bulk ingestion CLI tool (`scripts/bulk_ingest.py`) to process ~3,300+ resumes located in `G:\My Drive\intellect_iSolutons\All_Resumes\Resumes`.

The script runs directly against internal CIP storage/database/embedding modules, supports 500-file incremental batching, maintains resumption checkpoints, automatically filters out non-resume files (contracts, visa documents, study guides, and flat image PDFs), and writes a full audit log of all unprocessed files.

---

## What Was Implemented

### 1. Standalone Bulk Ingestion Script
- **File**: `scripts/bulk_ingest.py`
- **CLI Options**:
  - `--source-dir`: Path to root resumes folder (default: `G:\My Drive\intellect_iSolutons\All_Resumes\Resumes`)
  - `--batch-size`: Max valid resumes to process per run (default: `500`)
  - `--checkpoint-file`: State tracking file (default: `bulk_ingest_checkpoint.json`)
  - `--unprocessed-log`: Unprocessed document audit log (default: `bulk_ingest_unprocessed.json`)
  - `--dry-run`: Read-only simulation mode that previews queued files without mutating state

### 2. Dry-Run Simulation Mode (`--dry-run`)
When invoked with `--dry-run`, the script executes a safe, read-only preview of what would happen in the upcoming batch:
- **What It Does**:
  - Scans the folder hierarchy starting from `--source-dir`.
  - Silently skips MS Word lock files (`~$*`) and OS files (`desktop.ini`).
  - Checks `bulk_ingest_checkpoint.json` and skips files already processed in previous runs.
  - Prints every eligible resume file queued for the next batch (`[DRY RUN] Would evaluate: <relative_path>`).
  - Halts cleanly once `--batch-size` (e.g. 500) is reached.
- **Read-Only Guarantees (Zero Side Effects)**:
  - ❌ **No Database Writes**: No records created or modified in SQLite (`candidates`, `resume_versions`, `timeline_events`).
  - ❌ **No Search Indexing**: Full-Text Search tables (`candidate_fts`, `claims_fts`) remain untouched.
  - ❌ **No Vector Embeddings**: Bypasses embedding models (FastEmbed/LanceDB) entirely.
  - ❌ **No CAS Storage**: Does not copy binary files to Content-Addressable Storage.
  - ❌ **No Checkpoint Mutation**: `bulk_ingest_checkpoint.json` and `bulk_ingest_unprocessed.json` are NOT altered.

### 3. Multi-Tier Document Classifier (`classify_document`)
- **Scanned PDF / Flat Images**: Identifies PDFs with no selectable OCR text (< 50 chars) and standalone images (`.jpg`, `.png`, `.heic`), tagging them as `SCANNED_IMAGE_REQUIRES_OCR` or `STANDALONE_IMAGE`.
- **Legal Contracts & Agreements**: Detects vendor agreements, NDAs, C2C RTRs, MSAs, and subcontractor contracts in 0.1ms using filename and content phrase matching (`NON_RESUME_LEGAL_CONTRACT`).
- **Immigration / ID Documents**: Detects Form I-797, Form I-94, passport scans, and DMV records (`NON_RESUME_IMMIGRATION_OR_ID`).
- **Study Guides / Templates**: Detects interview prep notes and client portal blank submission templates (`NON_RESUME_STUDY_OR_TEMPLATE`).
- **MS Word Lock Files**: Silently ignores temporary lock files (`~$*`) and system metadata (`desktop.ini`).

### 4. Checkpointing & Resumption Engine
- Maintains `bulk_ingest_checkpoint.json` containing all processed paths.
- On subsequent runs, scans directory and skips already handled files in O(1) time.
- Secondary safety: SHA-256 CAS hash check prevents re-inserting identical binary files even if moved or renamed.

### 5. Entity Resolution & Dummy Name Guard
- Prevents documents with generic extracted headers (e.g. `"Uploaded Candidate"`) and no contact info from being auto-merged into existing candidate profiles.
- Captures relative folder paths (e.g. `Java developer`, `Data resumes\DE`) as `layout_metadata["source_folder"]` and records them in the candidate's timeline audit history.

### 6. Comprehensive End-to-End Audit & Telemetry Logging (`bulk_ingest_report.json`)
Every file evaluated by the script is recorded with rich structured telemetry:
- **Candidate & File Identity**: `candidate_name`, `candidate_id`, `file_path`, `file_name`, `file_type`, `folder_tag`, `file_size_bytes`, `hash`
- **Processing Status**:
  - `SUCCESS`: Complete ingestion into DB, FTS, and LanceDB vector store.
  - `PARTIAL_SUCCESS`: Candidate ingested and searchable in SQLite DB/FTS, but vector store indexing skipped or raw text fallback parser was used.
  - `SKIPPED_DUPLICATE`: Exact SHA-256 binary hash already exists in DB.
  - `SKIPPED_NON_RESUME`: Identified as a contract, visa form, study guide, or flat image PDF.
  - `FAILED`: Corrupted file or unhandled pipeline exception.
- **Pipeline Telemetry & AI Tracking**:
  - `how_processed`: Exact parser used (`PyMuPDF_Parser`, `Docx_Parser`, `Email_Parser`, `Raw_Text_Fallback`)
  - `ai_used`: `true` (if local LLM/Ollama fallback was invoked) or `false` (if Tier 1 deterministic NER extracted facts)
  - `confidence_score`: Extraction confidence float (`0.0` to `1.0`)
  - `stages_succeeded`: List of completed stages (`["FILE_READ", "CAS_STORE", "TEXT_PARSING", "DOCUMENT_CLASSIFICATION", "PROFILE_EXTRACTION", "DATABASE_INSERTION", "FTS_INDEXING", "VECTOR_INDEXING"]`)
  - `stages_failed`: List of failed stages (e.g. `["VECTOR_INDEXING"]` or `["DOCUMENT_CLASSIFICATION"]`)
  - `warnings`: Warning messages (e.g. legacy `.doc` fallback, vector store unavailable)
  - `error` & `trace`: Detailed error message and exception traceback on failure

### 7. Automated Test Suite
- **File**: `tests/test_bulk_ingest.py`
- Tests hash generation, document classification rules, dry-run safety, and master telemetry audit logging.

---

## Artifacts & Logs

| File | Purpose | Contents / Telemetry |
| :--- | :--- | :--- |
| `scripts/bulk_ingest.py` | Main CLI ingestion script | Production batch pipeline |
| `tests/test_bulk_ingest.py` | Pytest unit test suite | Automated verification |
| `bulk_ingest_report.json` | **Master Audit Log** | Every file evaluated (status, candidate name, parser, AI flag, stages succeeded/failed, warnings, errors) |
| `bulk_ingest_unprocessed.json` | **Non-Resume / Error Log** | Filtered view of non-resumes (contracts, visas, study guides, scanned PDFs) |
| `bulk_ingest_checkpoint.json` | **Resumption Checkpoint** | Array of completed file paths for instant O(1) restart |

---

## Test Verification
- **Command**: `uv run pytest tests/test_bulk_ingest.py -v`
- **Result**: `4 passed, 1 warning in 0.29s` (100% pass rate)

---

## How to Run Ingestion

1. **Preview next batch without making changes (Dry Run)**:
   ```powershell
   uv run python scripts/bulk_ingest.py --dry-run
   ```

2. **Execute an incremental 500-resume ingestion batch**:
   ```powershell
   uv run python scripts/bulk_ingest.py --batch-size 500
   ```

3. **Inspect skipped / non-resume files**:
   Open `bulk_ingest_unprocessed.json` to review all skipped contracts, visa documents, and scanned image PDFs.
