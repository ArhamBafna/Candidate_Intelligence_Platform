> 
> **ALREADY IMPLEMENTED** — This is already implemented and in codebase. Do NOT take this document as context / pending work unless user explicitly says otherwise.

# Async AI Candidate Match Insights

**Status:** `COMPLETED`  
**Implemented In:** `api/routes/candidates.py` (`/insight` endpoint), `ui/src/pages/CandidateList.jsx`  
**Tests:** `tests/test_api_candidates.py`, `tests/test_api_insight_fallback.py`  

---

## 1. Overview & Problem Solved

To prevent slow LLM generation from blocking the sub-second hybrid search experience, match rationales are decoupled from the initial search response. Initial search returns immediately using AST/FTS5 + Dense Vector retrieval; AI explanations stream asynchronously per candidate card via Server-Sent Events (SSE).

---

## 2. API & Protocol Specification

### Endpoint:
```http
GET /api/candidates/{candidate_id}/insight?query=...&title=...&city=...&minYoe=...
```

- **Protocol**: `text/event-stream` (Server-Sent Events)
- **Response Format**: `data: {"text": "<token>"}\n\n`
- **Error / Fallback Event**: `data: {"error": "AI_EXPLANATION_UNAVAILABLE", "message": "..."}\n\n`

---

## 3. Frontend Lifecycle & Cancellation

In `ui/src/pages/CandidateList.jsx`:
1. **Parallel Stream Initiation**: Triggers independent SSE requests for the Top 3 candidates upon search completion.
2. **AbortController Management**: Each candidate card maintains a dedicated `AbortController`.
3. **Manual Cancellation**: Clicking the cancel button immediately calls `controller.abort()`, closing the HTTP connection and unblocking UI state.
4. **Backend Compute Abort**: FastAPI detects client disconnects (`await request.is_disconnected()`) and cancels local Ollama inference to free GPU/CPU resources.
5. **Manual Re-trigger**: Cards with cancelled or un-streamed insights show a "Generate AI Note" button.

---

## 4. Test Coverage & Verification

- `tests/test_api_candidates.py`: Verifies SSE stream token yield and query parameter propagation.
- `tests/test_api_insight_fallback.py`: Verifies graceful JSON degradation when local Ollama is offline or unavailable.
