# AGENTS.md

## Mission

CIP is a privacy-first, local-first candidate intelligence and retrieval system for résumés, CVs, emails, and profiles. Preserve local-only behavior: request approval before adding any remote API or cloud dependency.

## Working sequence

1. **Orient.** Read `docs/agents/domain.md` before exploring domain behavior. Read relevant ADRs in `docs/adr/` and any context file they identify.
2. **Change.** Follow existing module boundaries and types. Keep CAS deduplication before parsing, SQLite WAL behavior, and immutable SHA-256 CAS files.
3. **Verify.** Run the smallest relevant existing test, then `uv run pytest` unless the user gives another scope. Work is complete only when changed behavior is covered and the selected tests pass.
4. **Track.** Update the matching unchecked item in `docs/task.md` only when the change completes that item. Work is complete only when the task entry reflects the delivered state.

## Implementation rules

- Add explicit type annotations for every argument and return value.
- Validate ingestion data with Pydantic v2 schemas.
- Use SQLAlchemy 2.0 models in `storage/db_models.py`.
- Check hashes through `storage/cas.py` before parsing.
- Add tests for changed behavior; ingestion, storage, and config modules require corresponding `tests/test_<module>.py` coverage.
- Keep SQLite WAL pragmas mandatory.
- Keep all candidate data and processing local unless the user approves an exception.

## Environment

Use `pyproject.toml` and the repository layout as sources of truth for versions and dependencies.

```powershell
uv sync
# Or
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

`pytest` uses `pythonpath = ["."]` from `pyproject.toml`.

```powershell
# Default: skips live Ollama integration
uv run pytest

# Include live Ollama integration
uv run pytest --run-ollama

# Run only live Ollama integration
uv run pytest -m ollama --run-ollama
```

## Agent-facing references

- GitHub issue and PR operations: `docs/agents/issue-tracker.md`
- Domain exploration, context files, and ADRs: `docs/agents/domain.md`
- Product direction for agentic retrieval: `docs/ideas/agentic-retrieval.md`

Create commits or push only when the user requests it or the task explicitly requires it.
