# Candidate Intelligence Platform (CIP) Domain Context

# Candidate Intelligence Platform (CIP) Domain Context

## Core Concepts
- **Candidate**: Primary profile containing contact info, work history summary, and attributes.
- **Resume Version**: Parsing output associated with a CAS file hash representing a resume upload.
- **Candidate Claim**: Fact extracted from resume or recruiter inputs (skills, titles, education).
- **CAS (Content-Addressed Storage)**: Immutable local binary file store indexed by SHA-256 hash.
- **Skipped (Ingestion)**: A resume upload that is safely ignored either because its exact SHA-256 hash already exists in CAS (duplicate) or because its file type is unsupported.
- **Wide Event / Canonical Log Line**: A single, context-rich structured JSON log entry emitted once per operation (e.g., upload, search) containing all relevant metrics, timers, and statuses.
- **System Telemetry Drawer**: A floating UI component at the bottom-right of the application visualizing real-time structlog canonical events, system health metrics, and background AI warnings.

## Architectural Decision Records (ADRs)

### ADR-001: Candidate Deletion Behavior
- **Status**: Accepted
- **Decision**: Candidate deletion via API (`DELETE /candidates/{candidate_id}`) performs a complete cascade deletion across relational database tables (`candidates`, `resume_versions`, `candidate_claims`, `candidate_timeline_events`), SQLite FTS index (`candidate_fts`, `claims_fts`), and LanceDB vector embeddings.
- **CAS Policy**: Raw files in CAS storage remain untouched to preserve CAS hash immutability and potential shared references.
- **UI Policy**: Deletion triggers provided in both Candidate Directory (List view) and Candidate Profile (Detail view) with modal confirmation dialog.

### ADR-002: Structlog for Canonical Log Lines (Wide Events)
- **Status**: Accepted
- **Decision**: Use `structlog` to implement canonical log lines (wide events) across the backend. Each critical operation (e.g., candidate search, resume ingestion) will build a single structured log payload incrementally and emit it at the end of the operation.
- **Motivation**: Deep visibility into latency, sub-step statuses (worked vs skipped vs failed), and search parameters. Avoids fragmented log traces.
- **Implementation**: API routes will initialize a structlog context. Sub-components (CAS, LanceDB, Parsers) will bind data to this context.

### ADR-003: UI System Telemetry & Log Drawer
- **Status**: Accepted
- **Decision**: Expose structured backend logs via a memory buffer endpoint (`GET /api/logs`) and SSE stream (`GET /api/logs/stream`). The React UI will render a persistent, floating status indicator at the bottom-right of the screen that opens a System Activity Console showing live telemetry, warnings, and skips.
- **Motivation**: Full visibility into system health, AI fallbacks, and backend operations directly inside the recruiter workspace.
