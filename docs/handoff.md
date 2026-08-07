# Handoff – Candidate Intelligence Platform (CIP)

## Current State
- **Project bootstrapped** with `uv` (Python 3.11) and a virtual environment.
- **Core Data & Storage** components are complete and fully tested:
  - `config/settings.py` (Pydantic‑Settings)
  - `config/database.py` (SQLAlchemy engine with WAL pragmas)
  - `storage/cas.py` (Content‑Addressable Store)
  - `storage/db_models.py` (SQLAlchemy ORM + FTS5 virtual tables)
  - `storage/vector_store.py` (LanceDB connection & schema)
- All associated tests in `tests/` pass (`pytest`).
- `task.md` shows these items marked ✅; the **Ingestion & Processing Pipeline** section is still pending.

## What to Work on Next
1. **Ingestion parsers** – implement and TDD‑test:
   - `ingestion/parsers/pdf_parser.py` (PyMuPDF + pdfplumber + optional OCR)
   - `ingestion/parsers/docx_parser.py` (python‑docx)
   - `ingestion/parsers/email_parser.py` (extract_msg / email.parser)
2. **Chunker & Entity Resolution** – after parsers are stable.
3. **Update `task.md`** as work progresses.

## Suggested Skills
- `tdd` – drive red‑green‑refactor cycles for each parser.
- `grilling` – stress‑test design decisions (e.g., OCR fallback strategy).
- `python-performance-optimization` – profile heavy PDF processing later.
- `find-skills` – locate any missing utilities (e.g., safe SHA‑256 helper).

## Adding `uv` to the Windows PATH (permanent)
1. Open **System Properties** → **Advanced** → **Environment Variables**.
2. Under **User variables**, find (or create) `Path` and click **Edit**.
3. Add a new entry:
   ```
   C:\Users\bafna_ci\.local\bin
   ```
4. Click **OK** to close all dialogs.
5. Open a **new** Command Prompt or PowerShell window – the updated `PATH` will be visible.
   ```powershell
   echo $env:Path
   ```
6. After this, you can run `uv` directly (`uv run …`, `uv add …`) without prefixing `$env:PATH=`.

> **Note:** The temporary PATH adjustment we performed earlier (`$env:PATH="C:\\Users\\bafna_ci\.local\bin;$env:Path"`) only affects the current shell session. Updating the user‑level environment variable makes it permanent for all future terminals.

---
*All sensitive data has been redacted.*
