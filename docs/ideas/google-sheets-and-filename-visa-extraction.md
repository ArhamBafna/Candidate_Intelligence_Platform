# Candidate Metadata Ingestion from Google Sheets & Filename Visa Extraction

**Status:** `OPEN / PROPOSED`  
**Category:** Ingestion / Entity Resolution / Metadata Extraction  

---

## 1. Concept Overview

Many candidates in the pipeline already have structured metadata stored in external sources (such as a Google Sheet tracker or CSV export) and critical work authorization / visa status embedded directly within resume filenames (e.g., `John_Doe_H1B_Resume.pdf`, `Jane_Smith_USC_Data_Engineer.docx`, `Alex_Wong_OPT_EAD.pdf`).

This proposal introduces:
1. **Google Sheets / CSV Metadata Ingestion**: Ingest structured candidate records directly from spreadsheet rows to enrich candidate profiles and claims.
2. **Filename Heuristic Extraction (Visa / Work Auth & Tags)**: Extract visa status, work authorization, and other contextual tags directly from the uploaded file's original name during document intake.

---

## 2. Problem Statement

1. **Missing / Unstructured Visa Data in Resume Body**:
   - Candidates often do not explicitly write "H1B", "OPT EAD", "Green Card", or "US Citizen" in the body text of their CV.
   - Recruiters or agency workflows frequently tag this info in the file name before uploading (e.g., `Resume_JohnDoe_GC.pdf`, `H1B_Transfer_Alice.docx`).
   - Current extraction only parses resume body text and ignores filename clues for work authorization.

2. **Siloed Spreadsheet Data**:
   - Candidate details (submission notes, current stage, phone, rate, visa status, LinkedIn, recruiter comments) live in a Google Sheet separate from the CIP candidate profiles.

---

## 3. Proposed Solution

### A. Filename-Based Visa & Metadata Extractor
- During intake ([`intake.py`](file:///c:/Users/bafna_ci/OneDrive/Desktop/Candidate_Intelligence_Platform/src/candidate_intelligence_platform/ingestion/intake.py)), analyze `original_filename` using deterministic regex and pattern matching.
- **Recognized Visa / Work Auth Patterns**:
  - `H1B` / `H-1B` / `H1-B`
  - `USC` / `US Citizen` / `Citizen`
  - `GC` / `Green Card` / `Permanent Resident`
  - `OPT` / `OPT-EAD` / `CPT` / `STEM OPT`
  - `TN` / `E3` / `L1` / `L2-EAD` / `H4-EAD`
- Store extracted visa information as a candidate claim / metadata tag (`source: FILENAME_HEURISTIC` or explicit claim) attached to the candidate profile.

### B. Google Sheets / CSV Ingestion Pipeline
- Provide a bulk sync / import tool or endpoint that accepts a Google Sheet export (CSV or via Google Sheets API/OAuth).
- **Column Mapping & Reconciliation**:
  - Map standard columns: `Name`, `Email`, `Phone`, `Visa Status`, `Current Location`, `Target Role`, `Notes`, `Resume Link/File`.
  - Link rows with existing candidate records using deterministic entity resolution (email/phone/name matching) or create new candidate profiles.
  - Populate structured attributes into `candidate_claims` and profile ledger.

---

## 4. Expected Benefits

- **Immediate Visa Search & Filtering**: Enables instant filtering by work authorization (e.g., search candidates who are `USC`, `GC`, or `H1B`) even if the resume body text omits it.
- **Richer Candidate Intelligence**: Combines recruiter notes from Google Sheets with deep resume vector & keyword search.
- **Zero Extra Manual Entry**: Leverages existing naming conventions already used by recruiting teams.
