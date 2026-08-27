> 
> **ALREADY IMPLEMENTED** — This is already implemented and in codebase. Do NOT take this document as context / pending work unless user explicitly says otherwise.

# Centralized AI Prompts

**Status:** `COMPLETED` (Issue #24)  
**Implemented In:** `src/candidate_intelligence_platform/prompts.py`  
**Tests:** `tests/test_prompts.py`  
**Rule:** Defined in `AGENTS.md` (every LLM prompt must be defined via a named builder in `prompts.py`)  

---

## 1. Overview & Architecture

To eliminate scattered inline prompts across route handlers and extraction scripts, all LLM prompts live in `src/candidate_intelligence_platform/prompts.py`.

### Named Builders Available:
- `build_fact_extraction_prompt(raw_text: str) -> str`: Builds schema-constrained JSON extraction prompt for Tier-2 fallback.
- `build_match_insight_prompt(raw_text: str, query: str, filters_summary: str | None) -> str`: Builds candidate explanation prompt for SSE streaming insights.
- `build_job_ad_distillation_prompt(job_description: str) -> str`: Distills unstructured job descriptions into structured search filters and keywords.

---

## 2. Test Verification

`tests/test_prompts.py` enforces byte-identity and structural snapshots to guarantee that refactoring prompts does not silently alter model inputs without deliberate test updates.