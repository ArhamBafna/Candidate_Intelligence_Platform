# Consolidate Multi-Step LLM Prompts into Single Request

**Status:** `PROPOSED`  
**Category:** LLM Optimization / Cost Efficiency / Latency  

---

## 1. Problem & Motivation

- **Per-Call Overhead**: Provider billing / rate limiting (e.g., OpenRouter or specific remote/local endpoints) and network latency introduce notable overhead per individual API call.
- **Multiple Sequential Calls**: Certain AI analysis tasks, such as generating candidate notes, summaries, or multi-faceted evaluations, currently make separate LLM calls (e.g., 3 individual prompts).
- **Redundant Context Passing**: Sending candidate context in 3 separate calls repeats prompt token ingestion and triples HTTP request overhead.

---

## 2. Proposed Solution

1. **Unified Multi-Aspect Prompt**:
   - Modern LLMs are sufficiently capable of following complex multi-instruction prompts simultaneously.
   - Consolidate multiple prompt steps (e.g., summary, match analysis, and gap evaluation) into a single, unified prompt in [`prompts.py`](file:///c:/Users/bafna_ci/OneDrive/Desktop/Candidate_Intelligence_Platform/src/candidate_intelligence_platform/prompts.py).
2. **Structured Output Format & Parsing**:
   - Instruct the LLM to output responses using a strict structured delimiter or schema (e.g., JSON schema or clear tag delimiters like `### SECTION: STRENGTHS`, `### SECTION: GAPS`, `### SECTION: SUMMARY`).
   - Server-side / client-side parser splits the single LLM response back into the 3 discrete sub-components.
3. **Benefits**:
   - **Cost Reduction**: Drastically cuts per-call billing costs.
   - **Reduced Latency**: Cuts roundtrip HTTP overhead from 3 sequential requests down to 1.
   - **Consistent Context**: Model reasons over all three dimensions in a single coherent context window.
