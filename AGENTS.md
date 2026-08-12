# AGENTS.md

## Overview
Candidate Intelligence Platform (CIP): privacy-first, local-first intelligence & candidate retrieval system (résumés, CVs, emails, profiles). No external cloud APIs.

- **Storage**: SQLite (WAL mode) via SQLAlchemy 2.0 ORM.
- **CAS**: SHA-256 binary hash storage, deduplicate before parse.
- **Vector**: LanceDB embedded index.
- **Ingestion**: Multi-format parse (PDF: PyMuPDF/pdfplumber, DOCX: python-docx, MSG: extract-msg) + section-aware chunker.
- **Entity Resolution**: Tier 1 deterministic exact match (email/phone), Tier 2 probabilistic Jaro-Winkler (name).

## Stack & Deps
- Python `>=3.14`
- `uv` (`uv_build`)
- SQLAlchemy `^2.0`, SQLite (WAL mode), LanceDB `^0.36`
- Pydantic `^2.13`, `pydantic-settings` `^2.15`
- PyMuPDF `^1.28`, pdfplumber `^0.11`, python-docx `^1.2`, extract-msg `^0.56`
- `pytest` `^9.1`

## Setup & Commands
```powershell
uv sync
# Or
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Testing & Verification
`pytest` uses `pythonpath = ["."]` in `pyproject.toml`.

```powershell
# Backend tests
uv run pytest

# Frontend build verification (must pass with 0 errors)
cd ui; npm run build; cd ..
```

## Layout
```
Candidate_Intelligence_Platform/
├── config/                  # DB & app settings (settings.py, database.py)
├── storage/                 # ORM, CAS, LanceDB (db_models.py, cas.py, vector_store.py)
├── ingestion/               # Parsers, chunker, entity resolution (parsers/, chunker.py, entity_resolution.py)
├── src/                     # Package root (candidate_intelligence_platform/)
├── api/                     # FastAPI application, dependencies, schemas & routes
├── ui/                      # Vite + React + Tailwind CSS Recruiter UI
├── docs/                    # Architecture docs & task.md
└── tests/                   # Test suite matching modules
```

## Code Rules
- **Type Annotations**: Explicit Python type hints for all args + returns.
- **Validation**: Pydantic v2 schemas for all ingestion data.
- **ORM**: Use SQLAlchemy 2.0 models in `storage/db_models.py`.
- **Deduplication**: Check hash with `storage/cas.py` before parsing.
- **Testing & Verification**: Every module in `ingestion/`, `storage/`, `config/` requires test in `tests/test_<module>.py`. Run both `uv run pytest` and `cd ui; npm run build` before declaring complete.
- **Task Tracking**: Update `docs/task.md` `[ ]` -> `[x]`.
- **Commit, Push**: after minor change to move towards a greater big change, commit. after big changes, push.


## Security & Ops
- **Privacy**: Local-first. No remote API call or cloud dep without approval.
- **DB**: SQLite WAL pragmas mandatory.
- **CAS**: SHA-256 files immutable once written.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues (`gh` CLI). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context repository layout (`CONTEXT.md` + `docs/adr/`). See `docs/agents/domain.md`.


