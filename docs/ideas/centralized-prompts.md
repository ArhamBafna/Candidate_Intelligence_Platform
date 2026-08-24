# Centralized AI Prompts

## Problem
Prompts for local LLMs live in multiple files:
- `extraction/local_llm_fallback.py` — resume fact extraction (long JSON schema prompt)
- `api/routes/candidates.py` — candidate insight / match rationale prompt

Adding new LLM features means hunting for and editing prompts in different modules. No single source of truth.

## Goal
Single `prompts.py` (or `prompts/` package) holding all prompt templates as strings or functions. Modules import from there. Easy to version, test, swap, or override per model.

## Sketch
```
src/candidate_intelligence_platform/prompts.py

EXTRACTION_PROMPT = """
You are an expert fact-extraction engine for resumes...
"""

INSIGHT_PROMPT = """
Given the candidate profile and resume text:
{raw_text}

Explain why this candidate is a good match for: '{query}'
"""

def render_extraction(text: str) -> str:
    return EXTRACTION_PROMPT.format(text=text[:3000])

def render_insight(raw_text: str, query: str) -> str:
    return INSIGHT_PROMPT.format(raw_text=raw_text, query=query)
```

## Benefits
- One place to read all prompts
- Unit-test prompt rendering independently
- Swap prompt versions per model (e.g., smaller prompt for faster model)
- Non-coders can edit prompts without touching logic files

## Open questions
- Keep as `.py` with f-strings, or move to `.txt`/`.jinja` files loaded at runtime?
- Add prompt versioning / metadata (model compatibility, token estimate)?
- Where does `prompts.py` live — `intelligence/`, `extraction/`, or top-level `prompts/`?