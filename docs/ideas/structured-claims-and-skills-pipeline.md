# Display Extracted Skills in Candidate Profile UI

**Status:** `PROPOSED`  
**Category:** Frontend / UI / Backend API  

---

## 1. Overview & Problem

During document ingestion (PDF, DOCX, email), the system extracts candidate skills through:
1. **Deterministic extraction** (`deterministic_ner.py` regex matching against `KNOWN_SKILLS`).
2. **AI fallback extraction** (`local_llm_fallback.py` / `prompts.py` extracting structured `SKILL` claims).

These extracted skills are persisted in the `candidate_claims` table (`claim_category = 'SKILL'`) and embedded for search. However, the candidate profile and candidate cards in the UI do not yet display a dedicated skills section or badge pills, making it hard for recruiters to quickly view a candidate's core competencies at a glance.

---

## 2. Proposed UI/UX Experience

1. **Candidate Profile Detail View**:
   - **Skills Badge Section**: Render a dedicated "Skills & Competencies" section displaying extracted skills as interactive, styled badge tags/chips.
   - **Provenance & Confidence Tooltips**: Hovering on a skill badge reveals:
     - Extraction source (e.g. *Explicit Fact via Regex* vs *AI Inference*).
     - Confidence score (e.g. 95%).
     - Match occurrence count or context if available.
   - **Categorization / Grouping (Optional Phase 2)**:
     - Group skills by type (e.g., Languages, Frameworks, Cloud & DevOps, Databases, Methodologies).

2. **Search Result Candidate Cards**:
   - Display top extracted skill tags (e.g., first 5-8 skills with a "+X more" counter).
   - **Query Match Highlighting**: If the candidate was retrieved via a skill search term (e.g., `react`, `aws`, `python`), highlight matching skill tags with an accent color.

3. **Manual Skill Management**:
   - Allow recruiters to add, remove, or confirm skill tags directly on the candidate profile.

---

## 3. Backend & API Integration

1. **API Schema Enhancement**:
   - Extend `CandidateResponse` in `api/schemas/candidates.py` or include a dedicated `skills: List[SkillClaimResponse]` / `skills: List[str]` field populated from `candidate_claims` where `claim_category == "SKILL"`.
2. **Deterministic Deduplication**:
   - Ensure skill claims with slight case variations (e.g. `python` vs `Python`) are normalized and deduplicated when returned to the UI.
3. **Audit Ledger & Claims**:
   - When a recruiter manually adds or removes a skill, record a corresponding `candidate_claims` update and `timeline_event`.

---

## 4. Implementation Steps

1. **API / Serialization**:
   - Update candidate serialization in `api/routes/candidates.py` and `api/schemas/candidates.py` to include aggregated unique skills from candidate claims.
2. **Frontend UI Components**:
   - Create a reusable `SkillBadge` / `SkillsContainer` component.
   - Integrate into candidate profile page and search result cards.
   - Add highlight styling for matching search terms.
3. **Testing**:
   - Add unit tests verifying skill extraction output serialization in `tests/test_api_candidates.py`.
