"""Unified resume intake pipeline (issue #12, Deepening #1).

Single shared pipeline behind every intake door: website single upload,
website batch upload, the three reprocess variants, and the bulk import
script. Bound by macro decisions D1-D14 (wayfinder map #4).
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import structlog
from sqlalchemy.orm import Session

from api.services.candidate_service import CandidateService
from config.settings import Settings
from crm.timeline_ledger import TimelineLedger
from ingestion.entity_resolution import (
    CandidateIdentifiers,
    ResolutionAction,
    resolve,
)
from storage.cas import CASManager
from storage.db_models import Candidate, EntityResolutionAudit, ResumeVersion

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class IntakeStatus(str, Enum):
    """Terminal outcome of one document through the pipeline."""

    INGESTED = "INGESTED"
    MERGED = "MERGED"
    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
    SKIPPED_NON_RESUME = "SKIPPED_NON_RESUME"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class IntakeResult:
    """Everything a door needs to build its response or SSE completion event."""

    status: IntakeStatus
    candidate_id: Optional[str] = None
    matched_candidate_id: Optional[str] = None
    resolution_action: Optional[ResolutionAction] = None
    classified_as: str = ""
    warnings: List[str] = field(default_factory=list)
    used_ai_fallback: bool = False
    model_name: Optional[str] = None


@dataclass(frozen=True)
class IntakeProgress:
    """One progress tick emitted from inside the pipeline."""

    stage: str
    progress: int
    message: str
    detail: Mapping[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[IntakeProgress], None]


class TimelineMode(str, Enum):
    """D3 parameter switch: web doors write the ledger, bulk keeps its own diary."""

    LEDGER = "LEDGER"
    NONE = "NONE"


class IntakeSource(str, Enum):
    """Which door invoked the pipeline; stamped onto audit rows (#8)."""

    UPLOAD = "upload"
    UPLOAD_STREAM = "upload-stream"
    BULK = "bulk"


# ---------------------------------------------------------------------------
# Document classification (moved verbatim from scripts/bulk_ingest.py)
# ---------------------------------------------------------------------------

LEGAL_CONTRACT_FILENAME_KEYWORDS = [
    "agreement", "msa.pdf", "msa.docx", "c2c rtr", "vendor", "subcontractor", "nda.pdf", "nda.docx"
]

LEGAL_CONTRACT_CONTENT_KEYWORDS = [
    "referral agreement", "subcontractor agreement", "vendor agreement",
    "master services agreement", "non-disclosure agreement", "c2c rtr",
    "indemnification", "governing law", "hereby agree", "confidentiality agreement",
    "parties hereto", "independent contractor", "mutual non-disclosure"
]

IMMIGRATION_ID_FILENAME_KEYWORDS = [
    "passport", "visa.pdf", "visa.docx", "dmv.pdf", "dmv.docx", "i-94", "opt -card",
    "opt card", "driver license", "driving license", "dl_files", "h1 approval",
    "h1b approval", "approval notice", "travel history", "ead card", "ead.pdf"
]

IMMIGRATION_ID_CONTENT_KEYWORDS = [
    "form i-797", "form i-94", "department of homeland security",
    "u.s. citizenship and immigration", "notice of action",
    "alien registration", "arrival-departure record", "arrival/departure record",
    "employment authorization document"
]

STUDY_TEMPLATE_KEYWORDS = [
    "submission format", "question bank", "interview questions",
    "key components of spring", "spring boot key components", "study guide",
    "cheat sheet", "sample test", "client portal submission"
]

RESUME_SIGNALS = [
    "experience", "employment", "work history", "professional experience",
    "project experience", "education", "skills", "technical skills",
    "summary", "objective", "certifications", "qualifications",
    "profile", "curriculum vitae", "responsibilities", "academic background"
]


def classify_document(text: str, filename: str) -> Tuple[bool, str, str]:
    """
    Classify whether a document is a genuine candidate resume or a non-resume file.
    Returns: (is_resume: bool, category: str, reason: str)
    """
    clean_text = text.lower()
    clean_fname = filename.lower()

    # 1. Check for empty text / scanned PDF
    if len(text.strip()) < 50:
        return False, "SCANNED_IMAGE_REQUIRES_OCR", "Document text is empty or contains fewer than 50 characters (scanned image without OCR text layer)"

    # 2. Check Immigration / ID documents
    for kw in IMMIGRATION_ID_FILENAME_KEYWORDS:
        if kw in clean_fname:
            return False, "NON_RESUME_IMMIGRATION_OR_ID", f"Document identified as government/visa/ID document from filename (matched: '{kw}')"

    for kw in IMMIGRATION_ID_CONTENT_KEYWORDS:
        if kw in clean_text:
            return False, "NON_RESUME_IMMIGRATION_OR_ID", f"Document identified as government/visa/ID document from text (matched: '{kw}')"

    # 3. Check Legal / Contracts / Vendor Agreements
    for kw in LEGAL_CONTRACT_FILENAME_KEYWORDS:
        if kw in clean_fname:
            return False, "NON_RESUME_LEGAL_CONTRACT", f"Document identified as legal contract from filename (matched: '{kw}')"

    legal_matches = [kw for kw in LEGAL_CONTRACT_CONTENT_KEYWORDS if kw in clean_text]
    if len(legal_matches) >= 2:
        return False, "NON_RESUME_LEGAL_CONTRACT", f"Document identified as legal contract from text (matched: {', '.join(legal_matches[:3])})"

    # 4. Check Study Guides / Formats
    for kw in STUDY_TEMPLATE_KEYWORDS:
        if kw in clean_fname or kw in clean_text:
            return False, "NON_RESUME_STUDY_OR_TEMPLATE", f"Document identified as interview prep/template format (matched keyword: '{kw}')"

    # 5. Check Resume Signals (must have at least one structural resume section or standard candidate contact indicators)
    signal_count = sum(1 for s in RESUME_SIGNALS if s in clean_text)
    has_email_or_phone = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text) or re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", text))

    if signal_count == 0 and not has_email_or_phone:
        return False, "NON_RESUME_INSUFFICIENT_SIGNALS", "Document lacks standard resume sections (no work experience, education, skills, or contact info)"

    return True, "VALID_RESUME", "Passed candidate resume verification"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _emit(
    on_progress: Optional[ProgressCallback],
    stage: str,
    progress: int,
    message: str,
    detail: Optional[Mapping[str, Any]] = None,
) -> None:
    if on_progress is not None:
        on_progress(IntakeProgress(stage=stage, progress=progress, message=message, detail=detail or {}))


def _parse_raw_text(content: bytes, cas_path: str, ext_lower: str, warnings: List[str]) -> str:
    raw_text = ""
    try:
        if ext_lower == ".pdf":
            from ingestion.parsers.pdf_parser import parse_pdf
            doc = parse_pdf(Path(cas_path))
            raw_text = doc.text
        elif ext_lower == ".docx":
            from ingestion.parsers.docx_parser import parse_docx
            doc = parse_docx(Path(cas_path))
            raw_text = doc.text
        elif ext_lower in [".eml", ".msg"]:
            from ingestion.parsers.email_parser import parse_email
            doc = parse_email(Path(cas_path))
            raw_text = doc.text
        else:
            return content.decode("utf-8", errors="ignore")
    except Exception as e:
        warnings.append(f"Structured parser failed ({str(e)}), used raw text fallback.")
        return content.decode("utf-8", errors="ignore")
    return raw_text


def _is_dummy_profile(first_name: str, last_name: str, email: Optional[str], phone: Optional[str]) -> bool:
    is_dummy_name = first_name.lower() in ["uploaded", ""] and last_name.lower() in ["candidate", ""]
    return is_dummy_name and not email and not phone


def _load_existing_identifiers(db: Session) -> List[CandidateIdentifiers]:
    existing_cands = db.query(Candidate).all()
    identifiers: List[CandidateIdentifiers] = []
    for c in existing_cands:
        name = f"{c.first_name} {c.last_name}".strip()
        identifiers.append(
            CandidateIdentifiers(
                c.id,
                c.primary_email,
                c.primary_phone,
                None,
                "" if name == "Uploaded Candidate" else name,
            )
        )
    return identifiers


def _build_audit_criteria(
    source: IntakeSource,
    tier: int,
    matching_keys: List[str],
    incoming: CandidateIdentifiers,
    matched_candidate_id: Optional[str],
    created_candidate_id: Optional[str],
) -> Dict[str, Any]:
    return {
        "source_door": source.value,
        "tier": tier,
        "matching_keys": matching_keys,
        "incoming": {
            "email": incoming.email,
            "phone": incoming.phone,
            "full_name": incoming.full_name,
            "linkedin_url": incoming.linkedin_url,
        },
        "matched_candidate_id": matched_candidate_id,
        "created_candidate_id": created_candidate_id,
    }


def _write_audit_row(
    db: Session,
    resolution_type: str,
    primary_candidate_id: str,
    merged_candidate_id: str,
    confidence_score: float,
    matching_criteria: Dict[str, Any],
) -> None:
    db.add(EntityResolutionAudit(
        id=str(uuid.uuid4()),
        primary_candidate_id=primary_candidate_id,
        merged_candidate_id=merged_candidate_id,
        resolution_type=resolution_type,
        confidence_score=confidence_score,
        matching_criteria=matching_criteria,
    ))


# ---------------------------------------------------------------------------
# Public surface
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
    """File-bytes door shared by /upload, /upload-stream and the bulk script.

    Stage order:
      1. hash once -> duplicate check BEFORE CAS store (D5)
      2. CAS store
      3. parse (pdf/docx/eml/msg dispatch + raw-text fallback)
      4. classify_document -> SKIPPED_NON_RESUME on reject, nothing persisted
      5. extraction exactly once with settings.extraction_confidence_threshold (D13)
      6. entity resolution vs current candidates, thresholds from Settings (D4)
      7. persist + flush, NO commit - caller commits once and owns rollback (D7)
      8. audit rows per #8 (MERGE and REVIEW write; NEW silent)
      9. FTS via CandidateService.update_fts_index (single SQL copy, D8)
     10. vectors via CandidateService.update_vector_index (failure is never fatal)
     11. timeline per timeline_mode (D3)
    """
    warnings: List[str] = []
    try:
        # 1. Hash once + duplicate check before CAS store (D5)
        _emit(on_progress, "HASHING", 10, "Computing file hash and checking for duplicates")
        file_hash = hashlib.sha256(content).hexdigest()
        existing_rv = db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == file_hash).first()
        if existing_rv:
            logger.info("resume_upload_complete", status="skipped", skip_reason="cas_duplicate", file_hash=file_hash)
            _emit(on_progress, "COMPLETED", 100, "File already exists", {"status": "SKIPPED_DUPLICATE"})
            return IntakeResult(
                status=IntakeStatus.SKIPPED_DUPLICATE,
                candidate_id=existing_rv.candidate_id,
                classified_as="DUPLICATE_FILE",
            )

        # 2. CAS store
        ext = Path(filename).suffix if filename else ".txt"
        _, cas_path = cas_mgr.store(content, extension=ext)

        # 3. Parse
        _emit(on_progress, "PARSING", 25, f"Parsing {ext} document")
        raw_text = _parse_raw_text(content, cas_path, ext.lower(), warnings)

        # 4. Classify
        _emit(on_progress, "CLASSIFYING", 40, "Verifying document is a genuine resume")
        is_resume, category, reason = classify_document(raw_text, filename)
        if not is_resume:
            logger.info("resume_upload_complete", status="skipped", skip_reason="non_resume", category=category)
            _emit(on_progress, "COMPLETED", 100, reason, {"status": "SKIPPED_NON_RESUME", "classified_as": category})
            return IntakeResult(
                status=IntakeStatus.SKIPPED_NON_RESUME,
                classified_as=category,
                warnings=[reason],
            )

        # 5. Extraction exactly once (D13)
        from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts
        from candidate_intelligence_platform.extraction.hybrid_extractor import extract_candidate_profile_hybrid

        _emit(on_progress, "EXTRACTING", 60, "Extracting profile facts")
        facts = extract_facts(raw_text)
        extracted = extract_candidate_profile_hybrid(
            raw_text,
            confidence_threshold=settings.extraction_confidence_threshold,
            facts=facts,
        )
        if extracted.get("warnings"):
            warnings.extend(extracted["warnings"])
        used_ai = bool(extracted.get("used_ai_fallback", False))
        model_name = settings.llm_model if used_ai else None

        first_name = extracted.get("first_name", "").strip() or ""
        last_name = extracted.get("last_name", "").strip() or ""
        email: Optional[str] = extracted.get("primary_email") or None
        phone: Optional[str] = extracted.get("primary_phone") or None
        full_name = f"{first_name} {last_name}".strip()

        if _is_dummy_profile(first_name, last_name, email, phone):
            category = "AI_CLASSIFIED_NOT_RESUME"
            reason = "No identifiable candidate name or contact information found in document"
            logger.info("resume_upload_complete", status="skipped", skip_reason="non_resume", category=category)
            _emit(on_progress, "COMPLETED", 100, reason, {"status": "SKIPPED_NON_RESUME", "classified_as": category})
            return IntakeResult(status=IntakeStatus.SKIPPED_NON_RESUME, classified_as=category, warnings=[reason])

        if used_ai:
            _emit(on_progress, "AI_EXTRACTION", 65, f"Running local AI Model extraction ({settings.llm_model})...", {
                "used_ai": True, "model_name": settings.llm_model,
            })

        # 6. Entity resolution against current candidates (thresholds from Settings, D4)
        _emit(on_progress, "ENTITY_RESOLUTION", 70, "Resolving candidate identity against existing records")
        incoming_identifiers = CandidateIdentifiers(
            candidate_id="temp",
            email=email,
            phone=phone,
            full_name="" if _is_dummy_profile(first_name, last_name, email, phone) else full_name,
        )
        resolution = resolve(
            incoming_identifiers,
            _load_existing_identifiers(db),
            auto_merge_threshold=settings.entity_res_auto_merge_threshold,
            review_threshold=settings.entity_res_review_threshold,
        )

        cand_id: Optional[str] = None
        matched_candidate_id: Optional[str] = None
        target_candidate: Optional[Candidate] = None

        if resolution.action == ResolutionAction.MERGE and resolution.matched_id:
            # D12: demote current primary RV(s); incoming RV becomes primary
            cand_id = resolution.matched_id
            db.query(ResumeVersion).filter(
                ResumeVersion.candidate_id == cand_id,
                ResumeVersion.is_primary == True,  # noqa: E712
            ).update({"is_primary": False})
            target_candidate = db.query(Candidate).filter(Candidate.id == cand_id).first()
        elif resolution.action == ResolutionAction.REVIEW and resolution.matched_id:
            matched_candidate_id = resolution.matched_id

        if not cand_id:
            cand_id = str(uuid.uuid4())
            target_candidate = Candidate(
                id=cand_id,
                first_name=first_name if first_name else "Candidate",
                last_name=last_name if last_name else "",
                primary_email=email,
                primary_phone=phone,
                availability_status="ACTIVE",
                current_title=extracted.get("current_title", "Candidate"),
            )
            db.add(target_candidate)

        layout_metadata: Dict[str, Any] = {}
        if folder_tag is not None:
            layout_metadata["source_folder"] = folder_tag

        rv = ResumeVersion(
            id=str(uuid.uuid4()),
            candidate_id=cand_id,
            cas_file_hash=file_hash,
            original_filename=filename or "resume",
            file_type=ext.replace(".", "").upper(),
            raw_text=raw_text,
            layout_metadata=layout_metadata,
            is_primary=True,
        )
        db.add(rv)

        # 7/8. Persist + audit rows (#8): MERGE and REVIEW write; NEW silent
        _emit(on_progress, "SAVING", 80, "Persisting candidate and resume version")
        if resolution.action == ResolutionAction.MERGE and resolution.matched_id:
            _write_audit_row(
                db,
                resolution_type="MERGE",
                primary_candidate_id=cand_id,
                merged_candidate_id=cand_id,
                confidence_score=resolution.confidence,
                matching_criteria=_build_audit_criteria(
                    source, resolution.tier, sorted(resolution.matching_keys),
                    incoming_identifiers, cand_id, None,
                ),
            )
        elif resolution.action == ResolutionAction.REVIEW:
            _write_audit_row(
                db,
                resolution_type="REVIEW",
                primary_candidate_id=cand_id,
                merged_candidate_id=matched_candidate_id or "",
                confidence_score=resolution.confidence,
                matching_criteria=_build_audit_criteria(
                    source, resolution.tier, sorted(resolution.matching_keys),
                    incoming_identifiers, matched_candidate_id, cand_id,
                ),
            )

        db.flush()

        status = IntakeStatus.MERGED if (
            resolution.action == ResolutionAction.MERGE and resolution.matched_id
        ) else IntakeStatus.INGESTED

        # 9. FTS via CandidateService (single SQL copy, D8)
        _emit(on_progress, "UPDATING_FTS", 85, "Refreshing full-text search index")
        try:
            display_name = full_name if full_name else "Candidate"
            CandidateService.update_fts_index(db, cand_id, display_name, target_candidate, raw_text)
        except Exception as e:
            warnings.append(f"Full-Text Search (FTS) index update failed ({str(e)}).")

        # 10. Vectors via CandidateService (failure never fatal)
        vector_failed = False
        if vector_db:
            _emit(on_progress, "GENERATING_VECTORS", 90, "Generating vector embeddings")
            try:
                CandidateService.update_vector_index(vector_db, cand_id, raw_text, rv.id)
            except Exception:
                vector_failed = True
                warnings.append("Vector indexing skipped (embedding engine or vector store unavailable).")
        else:
            vector_failed = True
            warnings.append("Vector indexing skipped (vector store connection unavailable).")

        # 11. Timeline per mode (D3)
        if timeline_mode == TimelineMode.LEDGER:
            _emit(on_progress, "LOGGING_TIMELINE", 95, "Logging timeline event")
            ledger = TimelineLedger()
            ledger.log_event(
                session=db,
                candidate_id=cand_id,
                event_type="RESUME_INGESTED",
                title="Resume Ingested",
                description=f"File {filename} uploaded and processed",
                metadata={},
                created_by="Recruiter",
            )

        final_status = IntakeStatus.PARTIAL if vector_failed else status

        _emit(on_progress, "COMPLETED", 100, "Intake completed", {
            "status": final_status.value,
            "candidate_id": cand_id,
            "resolution_action": resolution.action.value,
            "classified_as": category,
        })
        return IntakeResult(
            status=final_status,
            candidate_id=cand_id,
            matched_candidate_id=matched_candidate_id,
            resolution_action=resolution.action,
            classified_as=category,
            warnings=warnings,
            used_ai_fallback=used_ai,
            model_name=model_name,
        )
    except Exception as e:
        logger.error("resume_upload_complete", status="failed", error=str(e))
        return IntakeResult(status=IntakeStatus.ERROR, classified_as="", warnings=[str(e)])


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
    """Text door for all three reprocess variants.

    Per D10: no classification, no entity merge. Shares only extract-once ->
    apply fields -> FTS -> vectors -> REPROCESS_TRIGGERED timeline event.
    No commit - caller commits once and owns rollback (D7).
    """
    warnings: List[str] = []
    try:
        from candidate_intelligence_platform.extraction.deterministic_ner import extract_facts
        from candidate_intelligence_platform.extraction.hybrid_extractor import extract_candidate_profile_hybrid

        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return IntakeResult(status=IntakeStatus.ERROR, warnings=["Candidate not found"])

        _emit(on_progress, "ENTITY_RESOLUTION", 30, "Re-extracting candidate profile entities")
        facts = extract_facts(raw_text)
        extracted = extract_candidate_profile_hybrid(
            raw_text,
            confidence_threshold=settings.extraction_confidence_threshold,
            facts=facts,
        )
        if extracted.get("warnings"):
            warnings.extend(extracted["warnings"])
        used_ai = bool(extracted.get("used_ai_fallback", False))
        model_name = settings.llm_model if used_ai else None

        if used_ai:
            _emit(on_progress, "AI_EXTRACTION", 35, f"Running local AI Model extraction ({settings.llm_model})", {
                "used_ai": True, "model_name": settings.llm_model,
            })

        candidate.first_name = extracted.get("first_name", candidate.first_name)
        candidate.last_name = extracted.get("last_name", candidate.last_name)
        if extracted.get("primary_email"):
            candidate.primary_email = extracted["primary_email"]
        if extracted.get("primary_phone"):
            candidate.primary_phone = extracted["primary_phone"]
        if extracted.get("current_title"):
            candidate.current_title = extracted["current_title"]

        # FTS refresh
        _emit(on_progress, "UPDATING_FTS", 50, "Refreshing FTS search index")
        try:
            candidate_name = f"{candidate.first_name} {candidate.last_name}".strip()
            CandidateService.update_fts_index(db, candidate_id, candidate_name, candidate, raw_text)
        except Exception as e:
            warnings.append(f"Full-Text Search (FTS) index update failed ({str(e)}).")

        # Vector refresh (never fatal)
        vector_failed = False
        if vector_db:
            _emit(on_progress, "GENERATING_VECTORS", 75, "Chunking document and re-generating vector embeddings")
            try:
                CandidateService.update_vector_index(vector_db, candidate_id, raw_text, resume_version_id)
            except Exception:
                vector_failed = True
                warnings.append("Vector re-indexing skipped (embedding model or vector store error).")
        else:
            vector_failed = True
            warnings.append("Vector re-indexing skipped (LanceDB connection unavailable).")

        # Timeline event
        _emit(on_progress, "LOGGING_TIMELINE", 90, "Logging timeline audit event")
        ledger = TimelineLedger()
        ledger.log_event(
            session=db,
            candidate_id=candidate_id,
            event_type="REPROCESS_TRIGGERED",
            title="Reprocessing Triggered",
            description="Recruiter triggered a manual re-processing of candidate data",
            metadata={},
            created_by="Recruiter",
        )

        final_status = IntakeStatus.PARTIAL if warnings or vector_failed else IntakeStatus.INGESTED
        _emit(on_progress, "COMPLETED", 100, "Reprocessing completed", {"status": final_status.value})
        return IntakeResult(
            status=final_status,
            candidate_id=candidate_id,
            warnings=warnings,
            used_ai_fallback=used_ai,
            model_name=model_name,
        )
    except Exception as e:
        logger.error("reprocess_completed", status="failed", error=str(e))
        return IntakeResult(status=IntakeStatus.ERROR, warnings=[str(e)])
