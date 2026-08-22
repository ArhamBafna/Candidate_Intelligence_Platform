"""PROTOTYPE (wayfinder ticket #6) - rough shape sketch for the unified intake module.

Signatures and dataclasses only, no real logic. This file is a discussion artifact;
the build session writes the real module at
`src/candidate_intelligence_platform/ingestion/intake.py`.

Bound by macro decisions D1-D14 on the wayfinder map (issue #4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Mapping, Optional

from sqlalchemy.orm import Session

from config.settings import Settings
from ingestion.entity_resolution import ResolutionAction
from storage.cas import CASManager


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class IntakeStatus(str, Enum):
    """Terminal outcome of one document through the pipeline."""

    INGESTED = "INGESTED"                    # new candidate created, fully indexed
    MERGED = "MERGED"                        # appended to an existing candidate (auto-merge)
    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"  # exact CAS hash already stored (checked BEFORE CAS store, D5)
    SKIPPED_NON_RESUME = "SKIPPED_NON_RESUME"  # classifier rejected the document (D1/D11)
    PARTIAL = "PARTIAL"                      # core rows saved but a non-critical stage failed (e.g. vectors)
    ERROR = "ERROR"                          # critical failure; caller owns rollback (D7)


@dataclass(frozen=True)
class IntakeResult:
    """Everything a door needs to build its response/SSE completion event."""

    status: IntakeStatus
    candidate_id: Optional[str] = None          # id of the created OR merged-with candidate
    matched_candidate_id: Optional[str] = None  # REVIEW band: the look-alike we did NOT merge into
    resolution_action: Optional[ResolutionAction] = None  # NEW / MERGE / REVIEW; None when no resolution ran
    classified_as: str = ""                     # classify_document category ("VALID_RESUME", "NON_RESUME_LEGAL_CONTRACT", ...)
    warnings: List[str] = field(default_factory=list)
    used_ai_fallback: bool = False
    model_name: Optional[str] = None            # settings.llm_model when AI fallback fired


# ---------------------------------------------------------------------------
# Progress callback (D14: SSE doors adapt this into their event streams)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntakeProgress:
    """One progress tick emitted from inside the pipeline."""

    stage: str          # canonical names: HASHING, PARSING, CLASSIFYING, EXTRACTING,
                        # ENTITY_RESOLUTION, SAVING, UPDATING_FTS, GENERATING_VECTORS,
                        # LOGGING_TIMELINE, COMPLETED
    progress: int       # 0-100
    message: str
    detail: Mapping[str, Any] = field(default_factory=dict)  # e.g. {"used_ai": True, "model_name": "llama3.2"}


ProgressCallback = Callable[[IntakeProgress], None]


# ---------------------------------------------------------------------------
# Timeline switch (D3): parameter, not code divergence
# ---------------------------------------------------------------------------

class TimelineMode(str, Enum):
    LEDGER = "LEDGER"  # web doors: pipeline writes RESUME_INGESTED via TimelineLedger
    NONE = "NONE"      # bulk tool keeps writing its own diary rows after intake returns


class IntakeSource(str, Enum):
    """Which door invoked the pipeline; stamped onto audit rows (#8)."""

    UPLOAD = "upload"
    UPLOAD_STREAM = "upload-stream"
    BULK = "bulk"


# ---------------------------------------------------------------------------
# Public surface - two functions, not one mode-flagged entry point
# ---------------------------------------------------------------------------

def ingest_file(
    *,
    content: bytes,
    filename: str,
    db: Session,
    cas_mgr: CASManager,
    vector_db: Any,
    settings: Settings,
    source: IntakeSource,
    timeline_mode: TimelineMode,
    folder_tag: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> IntakeResult:
    """File-bytes door shared by single upload, batch upload, and the bulk script.

    Stage order (each stage emits progress when on_progress is given):
      1. hash once -> duplicate check against resume_versions.cas_file_hash (BEFORE CAS store, D5)
      2. CAS store (immutable blob)
      3. parse (pdf/docx/eml/msg dispatch + raw-text fallback)
      4. classify_document -> SKIPPED_NON_RESUME with category/reason on reject (D1/D11)
      5. extract_candidate_profile_hybrid called EXACTLY ONCE with settings.extraction_confidence_threshold (D13)
      6. entity_resolution.resolve vs existing candidates (thresholds from Settings, D4):
           MERGE        -> promote newest ResumeVersion to primary, demote prior (D12)
           REVIEW band  -> create NEW candidate AND EntityResolutionAudit row (D2)
           NEW          -> create candidate
      7. persist Candidate + ResumeVersion (flush, no commit - caller commits once at end, D7)
      8. FTS via CandidateService.update_fts_index (single SQL copy, D8)
      9. vectors via CandidateService.update_vector_index (chunker+embeddings live behind it)
     10. timeline per timeline_mode (D3)
    """
    raise NotImplementedError


def reprocess_text(
    *,
    raw_text: str,
    candidate_id: str,
    resume_version_id: str,
    db: Session,
    vector_db: Any,
    settings: Settings,
    on_progress: Optional[ProgressCallback] = None,
) -> IntakeResult:
    """Text door for all three reprocess variants (sync, stream, batch-stream).

    Per D10: NO classification (no file bytes), NO entity merge (candidate exists).
    Shares only: extract-once (D13) -> apply fields -> FTS -> vectors ->
    REPROCESS_TRIGGERED timeline event via TimelineLedger.
    Success status is INGESTED; resolution fields stay None.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Moved collaborator (out of scripts/bulk_ingest.py; keyword tables move with it)
# ---------------------------------------------------------------------------

def classify_document(text: str, filename: str) -> tuple[bool, str, str]:
    """Resume-vs-non-resume gate. Returns (is_resume, category, reason)."""
    raise NotImplementedError
