# Structured Claims & Skills Pipeline Integration

**Status:** `OPEN / READY FOR IMPLEMENTATION`  
**Priority:** High  
**Prerequisites:** Issue #12 (Unified Intake Pipeline)  

---

## 1. Problem Statement

Currently, `ingest_file()` in `src/candidate_intelligence_platform/ingestion/intake.py` creates the base `Candidate` record and indexes resume text into LanceDB and SQLite FTS5. However, extracted structured entities (skills, educational credentials, work experience history) are not persisted to the `candidate_claims` database table.

As a result:
- Ingested candidate cards display `0 skills`, `0 claims`, and `total_yoe = 0.0`.
- Skill badges and faceted filtering by skill or experience level cannot function from database queries.
- Evidence provenance (connecting a skill back to its exact character offset in the resume) is lost.

---

## 2. Target Files & Architecture

| File | Purpose | Changes Required |
|---|---|---|
| `src/candidate_intelligence_platform/extraction/deterministic_ner.py` | Entity and fact extraction | Expand technology dictionary, improve date range parsing, and emit standard claim dicts. |
| `src/candidate_intelligence_platform/extraction/hybrid_extractor.py` | Tier-1 / Tier-2 extraction | Return structured claims list alongside candidate profile fields. |
| `src/candidate_intelligence_platform/ingestion/intake.py` | Unified intake pipeline | Persist claims to `CandidateClaim` table in Step 6; compute and set `Candidate.total_yoe`. |
| `src/candidate_intelligence_platform/storage/db_models.py` | SQLAlchemy models | Reference model `CandidateClaim` with category, key, value, dates, offsets. |
| `tests/test_intake.py` | Intake test suite | Add unit and integration tests verifying claims persistence and YOE computation. |

---

## 3. Detailed Technical Specification

### 3.1 Claim Data Model & Categories

Every claim is stored in the `candidate_claims` table (`CandidateClaim` model):

```python
class CandidateClaim(Base):
    id: str                        # UUID primary key
    candidate_id: str              # FK -> candidates.id (indexed)
    resume_version_id: str         # FK -> resume_versions.id (indexed)
    source_type: str               # "EXPLICIT_FACT" (deterministic) or "AI_INFERENCE" (LLM)
    claim_category: str            # "SKILL" | "EMPLOYMENT" | "EDUCATION" | "LOCATION"
    claim_key: str                 # Normalized lowercase search key (e.g. "python", "aws", "bachelor")
    claim_value: str               # Display string (e.g. "Python", "Amazon Web Services", "B.S. Computer Science")
    start_date: str | None         # ISO format / year (e.g. "2020-01" or "2020")
    end_date: str | None           # ISO format / year or "Present"
    confidence_score: float        # 1.0 for deterministic, 0.7-0.95 for AI inference
    source_char_offset_start: int | None  # Character offset in raw resume text
    source_char_offset_end: int | None
```

### 3.2 Expanded Skill Dictionary & Matching

In `deterministic_ner.py`:
- Maintain a curated dictionary of tech skills mapped from normalized keywords to canonical names:
  - Languages: `python`, `typescript`, `javascript`, `golang`, `java`, `c++`, `c#`, `ruby`, `rust`, `sql`, `html`, `css`.
  - Frameworks: `react`, `next.js`, `vue`, `angular`, `fastapi`, `django`, `flask`, `spring boot`, `node.js`, `express`.
  - Cloud & Infra: `aws`, `azure`, `gcp`, `docker`, `kubernetes`, `terraform`, `ansible`, `linux`, `ci/cd`.
  - Data & AI: `postgresql`, `mysql`, `mongodb`, `redis`, `lancedb`, `pytorch`, `tensorflow`, `pandas`, `numpy`, `spacy`.
- Use word-boundary regex (`\b(?:keyword)\b`) to prevent substring false matches (e.g., `c` in `cat`, `go` in `good`).
- Record character start and end offsets for every matched skill.
- **Tier 2 LLM Skill Fallback**: If Tier 1 finds fewer than 3 skills, prompt LLM via `prompts.py` to extract up to 10 key technical skills (`source_type="AI_INFERENCE"`). Clamp output to maximum 10 skills to prevent hallucination bloat.

### 3.3 Total YOE (Years of Experience) Calculation

Compute `total_yoe` during Step 5 of `ingest_file()` using a two-tier strategy:

1. **Employment Date Span Summation (Primary)**:
   - Extract non-overlapping date intervals from work experience entries:
     - Regex patterns: `(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})[,\s]+(\d{4})\s*(?:-|–|to)\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|...|\d{1,2})[,\s]+(\d{4})|Present|Current)`
     - Interval calculation: Convert dates to decimal years (`year + (month-1)/12`). Treat `"Present"` as current date.
     - **Vague Year Ranges**: Year-only spans (e.g. `2021 - 2023`) calculate as exact year delta: $2023 - 2021 = 2.0\text{ years}$.
     - Merge overlapping intervals to avoid double-counting concurrent jobs.
     - Compute total span in years: $\text{total\_yoe} = \sum (\text{end} - \text{start})$.

2. **Explicit Summary Pattern (Fallback)**:
   - If no valid date intervals are found, check resume header/summary:
     `r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)'`
   - Example: `"8+ years of experience in backend development"` $\rightarrow 8.0$.

3. **Sanity Clamping**:
   - Clamp `total_yoe` between `0.0` and `50.0`. Round to 1 decimal place.

### 3.4 Ingestion Pipeline Integration (`intake.py`)

In Step 5 & 6 of `ingest_file()`:

```python
# Step 5: Extract profile & claims
outcome = extract_candidate_profile_hybrid(raw_text, facts=facts, threshold=settings.hybrid_extraction_threshold)
extracted_claims = outcome.claims  # list[dict]
computed_yoe = compute_total_yoe(raw_text, extracted_claims)

# Step 6: Persist Candidate & Claims in single transaction
candidate.total_yoe = computed_yoe
db.add(candidate)
db.flush()

for c in extracted_claims:
    claim_obj = CandidateClaim(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        resume_version_id=resume_version.id,
        source_type=c.get("source_type", "EXPLICIT_FACT"),
        claim_category=c.get("claim_category", "SKILL"),
        claim_key=c.get("claim_key").lower().strip(),
        claim_value=c.get("claim_value").strip(),
        start_date=c.get("start_date"),
        end_date=c.get("end_date"),
        confidence_score=float(c.get("confidence_score", 1.0)),
        source_char_offset_start=c.get("offset_start"),
        source_char_offset_end=c.get("offset_end"),
    )
    db.add(claim_obj)

db.commit()
```

### 3.5 Merge & Re-Upload Handling (`ResolutionAction.MERGE`)

When an uploaded resume matches an existing candidate:
- Delete existing `candidate_claims` for `candidate.id` and replace with fresh claims from new resume version.
- Update `Candidate.total_yoe` with the newly computed value.

---

## 4. Verification & Testing Plan

### 4.1 Fast Unit Tests (< 2s)
- Test skill extraction: match known tech stack, verify boundary checks (no false positives for `Go` in `Good`).
- Test LLM skill fallback when deterministic dictionary misses rare tech.
- Test YOE parser: multi-job overlapping dates, year-only intervals (`2021 - 2023 = 2.0`), `"Present"` handling, fallback string regex.
- Test claim persistence & replacement on re-upload in `tests/test_intake.py`.

### 4.2 Integration Verification
- Ingest sample resume (`tests/test-resumes/resume_valid_1.pdf`).
- Query candidate via `/api/candidates/{id}`: verify `claims` array and `total_yoe > 0.0`.
- Verify UI renders skill pills and experience badge.
