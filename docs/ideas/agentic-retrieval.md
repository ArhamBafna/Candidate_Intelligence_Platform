# Autonomous Agentic Retrieval System

**Status:** `DEFERRED / SKIPPED` (User decision: Retained for reference, not currently in active roadmap)  
**Category:** Experimental Feature  

---

## 1. Concept Overview

A multi-step autonomous recruiter search agent designed for nuanced natural language queries (e.g., *"Led a team of 5+ engineers at a high-growth fintech startup"*). 

Instead of single-shot retrieval:
1. Agent autonomously executes tool calls (`filter_by_metadata`, `vector_search`) to retrieve a shortlist.
2. Hardcoded limit: narrows pool to at most 10 candidate resumes.
3. Uses a `read_raw_resume` tool to deeply analyze the 10 resumes against criteria.
4. Generates qualitative match assessments without arbitrary numeric grading.

---

## 2. Deferred Rationale

- Instant hybrid search with soft filters and streaming SSE match insights meets current latency and UX requirements without incurring the 15–30 second delay of multi-step agentic tool loops.
