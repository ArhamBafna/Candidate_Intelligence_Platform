# Structured Claims & Skills Pipeline Integration

## Problem
Currently, `ingest_file()` in `src/candidate_intelligence_platform/ingestion/intake.py` creates the core `Candidate` row (name, email, phone, title) and indexes text into LanceDB and SQLite FTS5. However, it does not persist extracted structured facts (skills, education, employment dates) into the `candidate_claims` table, resulting in `0 skills`, `0 claims`, and `total_yoe = 0.0` for ingested candidates.

## Goal
Integrate structured claim persistence directly into the Unified Intake Pipeline (`intake.py`) so that candidate profile cards display accurate skills badges, employment timeline entries, education credentials, and computed total years of experience (YOE).

## Proposed Architecture & Pipeline Flow

### 1. Extraction Stage Expansion
During Step 5 (`EXTRACTING`) of `ingest_file()`:
- `extract_facts(raw_text)` extracts deterministic facts:
  - `SKILL`: Recognized technology dictionary (`Python`, `Java`, `React`, `AWS`, `Docker`, `SQL`, etc.) with character offsets.
  - `EDUCATION`: Degree titles, universities, graduation years.
  - `EMPLOYMENT`: Company names, titles, date ranges (`2018 - 2024`).
- `extract_candidate_profile_hybrid()` returns both the unified profile and the full list of structured claim dictionaries.

### 2. Total YOE (Years of Experience) Calculation
- Compute `total_yoe` from either:
  1. Explicit resume summary mentions (e.g. `"7 years experience"`, `"11+ years of experience"`).
  2. Sum/span of non-overlapping employment date ranges extracted from work history.
- Update `Candidate.total_yoe` on the candidate record.

### 3. Database Persistence (`candidate_claims` Table)
Insert verified claims into `CandidateClaim`:
```python
for claim in extracted_claims:
    db.add(CandidateClaim(
        id=str(uuid.uuid4()),
        candidate_id=cand_id,
        resume_version_id=rv.id,
        source_type=claim.get("source_type", "EXPLICIT_FACT"),  # EXPLICIT_FACT or AI_INFERENCE
        claim_category=claim.get("claim_category"),            # SKILL, EMPLOYMENT, EDUCATION, LOCATION
        claim_key=claim.get("claim_key"),                      # e.g. "python", "degree", "company"
        claim_value=claim.get("claim_value"),                  # e.g. "Python", "B.S. Computer Science"
        start_date=claim.get("start_date"),
        end_date=claim.get("end_date"),
        confidence_score=claim.get("confidence_score", 1.0),
        source_char_offset_start=claim.get("source_char_offset_start"),
        source_char_offset_end=claim.get("source_char_offset_end"),
    ))
```

### 4. Deduplication & Conflict Handling on Merge
When an incoming resume merges with an existing candidate (`ResolutionAction.MERGE`):
- Attach new claims with the new `resume_version_id`.
- Recalculate aggregate skills and freshest `total_yoe`.

## Benefits
- Candidate profile cards in the UI display full skill pill tags and work experience history.
- Faceted search (filtering by skill, YOE $\ge 5$, or degree) works out of the box.
- Full provenance and explainability: every skill links back to its exact character offset in the source document.
