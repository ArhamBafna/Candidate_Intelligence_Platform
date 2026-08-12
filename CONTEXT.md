# Candidate Intelligence Platform (CIP) Domain Context

## Core Concepts
- **Candidate**: Primary profile containing contact info, work history summary, and attributes.
- **Resume Version**: Parsing output associated with a CAS file hash representing a resume upload.
- **Candidate Claim**: Fact extracted from resume or recruiter inputs (skills, titles, education).
- **CAS (Content-Addressed Storage)**: Immutable local binary file store indexed by SHA-256 hash.

## Architectural Decision Records (ADRs)

### ADR-001: Candidate Deletion Behavior
- **Status**: Accepted
- **Decision**: Candidate deletion via API (`DELETE /candidates/{candidate_id}`) performs a complete cascade deletion across relational database tables (`candidates`, `resume_versions`, `candidate_claims`, `candidate_timeline_events`), SQLite FTS index (`candidate_fts`, `claims_fts`), and LanceDB vector embeddings.
- **CAS Policy**: Raw files in CAS storage remain untouched to preserve CAS hash immutability and potential shared references.
- **UI Policy**: Deletion triggers provided in both Candidate Directory (List view) and Candidate Profile (Detail view) with modal confirmation dialog.
