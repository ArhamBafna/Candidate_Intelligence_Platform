# DSA Codebase Audit Report

## Summary
- **Subsystems Audited:** 4 (API, CRM, Ingestion, Storage)
- **Total Recommendations:** 4 | **Skips:** 0
- **Primary Complexity Themes:**
  - Scattered state duplication
  - Scattered schema/types
  - Repeated duplication across endpoints
  - Complex nested logic

## Ranked Recommendations

| Priority | Subsystem | Recommendation | Affected Files | Complexity / Risk | Confidence |
|---|---|---|---|---|---|
| P1 | api | Abstract bulk reprocess/delete endpoints logic | `api/routes/candidates.py:465` | Duplicated candidate entity update flow / High | High |
| P2 | ingestion | Replace difflib with more efficient similarity metric in entity resolution | `ingestion/entity_resolution.py:30` | Inefficient quadratic string comparison logic / Medium | High |
| P3 | crm | Refactor state transition logging to use single object param | `crm/state_machine.py:17` | Scattered parameter lists / Low | High |
| P4 | storage | Remove manual `CandidateSectionVector` mapping inside endpoints, use single factory method | `api/routes/candidates.py` & `storage/vector_store.py` | Leaky abstractions on insertion logic / Low | High |

## Detailed Findings & Proposed Simplifications

### 1. api: Abstract bulk reprocess/delete endpoints logic
- **Subsystem & Location:** `api/routes/candidates.py`
- **Current Problem:** The endpoints for reprocessing, batch processing and candidate deletion duplicate the vector deletion and DB commit sequence heavily. They copy-paste extraction logic and manual FTS updates.
- **Proposed Model:** Create a `CandidateService` class or standalone domain functions that encapsulate the "Reprocess Candidate", "Delete Candidate", and "Create Candidate from Resume" flows. This centralizes the SQLAlchemy DB writes, FTS execution, Vector DB updates, and Timeline logging.
- **Implementation Scope:** `api/routes/candidates.py`, `api/services/candidate_service.py` (new)
- **Risks & Verification:** High risk due to modifying core API endpoints. Requires extensive API regression tests.

### 2. ingestion: Refactor Entity Resolution
- **Subsystem & Location:** `ingestion/entity_resolution.py`
- **Current Problem:** Entity resolution uses manual loops across all existing entities with `difflib` similarity logic, which isn't scale-efficient, nor does it scale cleanly as rules expand.
- **Proposed Model:** Implement a dedicated `EntityResolver` class or index that reduces quadratic comparisons, or simplify the resolution loop logic. While keeping difflib might be okay for small lists, the nested loop `for cand in existing` inside `resolve` can be abstracted.
- **Implementation Scope:** `ingestion/entity_resolution.py`
- **Risks & Verification:** Low regression risk if only abstracting the control flow. Requires unit tests for entity resolution to pass.

### 3. crm: Refactor state transition logic
- **Subsystem & Location:** `crm/state_machine.py:17`
- **Current Problem:** `transition_state` takes many positional/keyword parameters, and logic will get complex when more states are introduced.
- **Proposed Model:** Introduce a `TransitionContext` or use an Enum-driven map to manage transitions and validation logic in a scalable way, instead of scattered `if` statements and basic sets.
- **Implementation Scope:** `crm/state_machine.py`
- **Risks & Verification:** Low risk. Validate with existing test suite `test_state_machine.py`.

### 4. storage/api: Encapsulate Vector Model Insertion
- **Subsystem & Location:** `api/routes/candidates.py` and `storage/vector_store.py`
- **Current Problem:** In `api/routes/candidates.py`, the mapping to LanceDB `CandidateSectionVector` is done via raw dictionary creation multiple times `{"chunk_id": chunk.chunk_id, ...}`.
- **Proposed Model:** Add a factory/helper function in `storage/vector_store.py` or `CandidateSectionVector` to instantiate or bulk-create vector models from chunks and embeddings directly.
- **Implementation Scope:** `api/routes/candidates.py`, `storage/vector_store.py`
- **Risks & Verification:** Low risk. Need to make sure `test_api_candidates.py` passes.

## Coverage & Skips
- None.
