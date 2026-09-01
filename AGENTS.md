# AGENTS.md

## Mission & Constraints
- Local-first, privacy-first. Request approval before adding remote API or cloud dependencies.

## Workflow
1. **Orient:** Read `docs/agents/domain.md` and relevant ADRs in `docs/adr/`.
2. **Change:** Follow existing module boundaries and types.
3. **Verify:** Run target test file, then `uv run pytest`. Work complete only when tests pass.
4. **Track:** Update unchecked items in `docs/task.md`.

## Implementation Rules
- Add explicit type annotations for every argument and return value.
- Validate ingestion data with Pydantic v2 schemas.
- Use SQLAlchemy 2.0 models in `storage/db_models.py`.
- Check hashes through `storage/cas.py` before parsing.
- Keep SQLite WAL pragmas mandatory.
- Every LLM prompt must be defined in `src/candidate_intelligence_platform/prompts.py` via named builder — never inline at call site.
- Fast tests (< 2s/file): always mock heavy ML models (spaCy, FastEmbed/SentenceTransformers, CrossEncoder reranker) and LLM inference (Ollama).

## Commands
```powershell
# Default test run (models mocked)
uv run pytest

# Include live Ollama integration
uv run pytest --run-ollama
```

## References
- Domain & ADRs: `docs/agents/domain.md`
- Issue/PR operations: `docs/agents/issue-tracker.md`
