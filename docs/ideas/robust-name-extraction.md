# Specification: Robust Multi-Stage Anchored Candidate Name Extraction

## Problem Statement

Recruiters and hiring managers frequently ingest resumes with diverse layouts—ranging from traditional single-column documents to creative multi-column templates, documents with decorative headers, and resumes starting with section titles like "Profile Summary" or "Curriculum Vitae". 

Currently, deterministic name extraction relies on brittle top-line heuristics and standard NER models that often mistake generic section headers for candidate names, or fail completely on non-standard layouts, defaulting to generic fallback identities ("Uploaded Candidate"). Adding endless keyword blacklists is fragile and risks rejecting valid non-Western names, while invoking heavy transformer models or remote LLMs for every resume introduces severe latency, high memory usage, and privacy concerns in a local-first system.

## Solution

A multi-stage deterministic extraction cascade that anchors candidate discovery to known structural landmarks (top lines and contact information blocks) and cross-validates extracted candidate names against candidate email handles using a fast, shared validation gate.

1. **Stage 1 (Primary Discovery & NER):** Evaluates top lines and NER candidate person entities, passing candidates through the shared email validation gate. Validated names are accepted immediately with high confidence.
2. **Stage 2 (Contact Block Positional Anchoring):** If Stage 1 fails or matches known header noise, searches a bounded window (1–3 lines above, 1 line below) around contact landmarks (email / phone) and pipes candidates through the same email validation gate.
3. **Stage 3 (Tier-2 AI / Local LLM Fallback):** If deterministic stages fail to identify a validated name, the system escalates to the local LLM fallback to extract candidate identity and infer missing fields.

## User Stories

1. As a recruiter uploading a standard resume, I want the parser to extract the candidate's first and last name from the top lines, so that the candidate profile is accurately created in the system.
2. As a recruiter uploading a creative multi-column resume where the name is placed beside or above the contact details, I want the parser to scan the contact block neighborhood, so that names not located in the absolute top line are still identified.
3. As a recruiter ingesting resumes with prominent section headings (such as "Executive Summary" or "Profile Overview"), I want candidate names validated against the candidate's email handle, so that section headers are never saved as candidate names.
4. As a recruiter processing resumes where the candidate's email uses initials (e.g., `jsmith@example.com` or `j.smith@example.com` for "John Smith"), I want initial-aware fuzzy matching in the validation gate, so that valid names pass verification without invoking AI fallbacks.
5. As a recruiter uploading a resume that contains only a phone number or no email, I want the validation gate to degrade gracefully to positional and NER scoring, so that candidates without email addresses are not incorrectly rejected.
6. As a candidate with an all-caps or all-lowercase name in my resume header, I want my name normalized into proper Title Case, so that my candidate profile appears clean and professional.
7. As a system administrator running CIP locally on constrained hardware, I want deterministic name extraction to execute in milliseconds without heavy transformer models or external cloud APIs, so that document ingestion remains fast, private, and lightweight (<2s per file).
8. As an intake pipeline worker processing difficult or corrupt documents where heuristics cannot extract a name with confidence, I want automatic escalation to the local LLM fallback, so that edge cases are handled without pipeline crashes.
9. As an API client consuming ingestion endpoints, I want the returned extraction outcome to provide clear confidence scores and indicate whether AI fallback was used, so that downstream CRM components know when human review is advised.
10. As a recruiter uploading resumes with non-Western names, I want name extraction to avoid brittle static gazetteers or exclusionary blacklists, so that valid names from any cultural origin are fairly and accurately extracted.
11. As a developer maintaining extraction logic, I want a single reusable email-validation gate used across all extraction stages, so that name validation rules and scoring thresholds are consistent and easily maintained.
12. As a search user querying candidate names in the platform, I want names extracted without trailing punctuation, noise tokens, or job title prefixes, so that full-text and entity resolution queries match accurately.

## Implementation Decisions

- **Cascade Architecture:**
  - Introduce a 3-stage cascade within the deterministic extraction pipeline: Stage 1 (Top Lines / NER) -> Stage 2 (Contact Block Neighborhood Anchoring) -> Stage 3 (Local LLM Fallback).
  - Both deterministic stages (Stage 1 & Stage 2) must route through a single, shared validation function rather than separate custom checks.

- **Shared Email Validation Gate:**
  - Implement a reusable validation function that compares candidate name strings against the email prefix (`local-part` before `@`).
  - The gate normalizes both strings by stripping punctuation, digits, and special characters.
  - Supports multiple match strategies:
    1. Full token containment (e.g. `john` and `doe` in `john.doe@...` or `johndoe@...`).
    2. Initial + surname matching (e.g. `j` and `smith` in `jsmith@...` or `j.smith@...`).
    3. Fuzzy string similarity threshold (e.g., Jaro-Winkler score $\ge 0.70$) to accommodate minor typos or truncated email prefixes.
  - When no email is present in the document, the gate returns a neutral fallback confidence, allowing positional NER to proceed without strict email cross-referencing.

- **Contact Block Positional Anchoring:**
  - When Stage 1 fails or detects noise header lines, locate the character / line offsets of extracted contact landmarks (email or phone).
  - Inspect a bounded window: 1 to 3 lines above and 1 line below the primary contact line.
  - Candidate lines are filtered for valid name characteristics (1–4 words, alphabetic tokens, absence of job title keywords or URL schemes) and scored through the shared email validation gate.

- **Confidence Scoring & LLM Escalation:**
  - Name verification from Stage 1 or Stage 2 with email confirmation yields high Tier-1 name confidence.
  - If neither stage identifies a validated name, or if extracted candidate remains "Uploaded Candidate", Tier-1 confidence falls below the escalation threshold, triggering the existing local LLM fallback (`extract_inferences`).

- **Interface Preservation:**
  - Preserve the existing `ExtractionOutcome` data contract and `extract_candidate_profile_hybrid()` signature.
  - Ensure all internal fact representations adhere to Pydantic v2 schemas and SQLAlchemy 2.0 storage models.

## Testing Decisions

- **What Makes a Good Test:**
  - Tests must evaluate external behavior against input resume text and verify the resulting `ExtractionOutcome` (extracted `first_name`, `last_name`, `confidence_score`, and `used_ai_fallback`).
  - Tests must not assert internal intermediate regex passes or private loop counters.
  - Tests must execute in <2s and must mock all heavy ML / LLM components (spaCy, Ollama) to keep test execution fast and deterministic.

- **Tested Scenarios:**
  - **Standard Header:** Name on line 1 with email on line 2 (Stage 1 immediate pass).
  - **Prominent Section Header Collision:** Resume starts with "Profile Summary" or "Curriculum Vitae" followed by candidate name and contact block (Stage 1 header rejection -> Stage 2 contact anchor success).
  - **Initial-based Email:** Name "John Smith" with email `jsmith@example.com` or `j.smith@example.com` (Fuzzy email gate match).
  - **Multi-column Layout / Contact First:** Email and phone on top lines with name directly adjacent/below (Stage 2 contact anchor success).
  - **Missing Email:** Resume with only phone number and name (Graceful neutral gate behavior without breaking extraction).
  - **Non-Western Name:** Multi-part non-Western name correctly extracted and capitalized without blacklist collision.
  - **Corrupt / Unparseable Header:** Corrupt text causing both Stage 1 and Stage 2 to fail, correctly routing to mocked Tier-2 LLM fallback.

- **Prior Art:**
  - Existing deterministic and hybrid extraction test patterns in `tests/test_hybrid_extractor.py` and `tests/test_deterministic_ner.py`.

## Out of Scope

- **Massive dictionary / gazetteer lookups:** Adding large static name dictionaries is out of scope to avoid memory bloat and cultural bias against non-Western names.
- **Heavy transformer NER models (e.g., `en_core_web_trf`):** Too slow for local-first CPU execution budget (<2s per file).
- **Infinite keyword blacklists:** Manual list expansion of arbitrary noise words is rejected in favor of structural anchoring and email validation.
- **External cloud parsing services:** All extraction remains 100% local to protect candidate privacy and honor local-first architectural requirements.

## Further Notes

- This specification replaces the initial idea draft in `docs/ideas/robust-name-extraction.md`.
- Label: `ready-for-agent`.
