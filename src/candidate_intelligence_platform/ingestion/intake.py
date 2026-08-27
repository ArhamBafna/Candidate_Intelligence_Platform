"""Unified resume intake pipeline (issue #12, Deepening #1).

Single shared pipeline behind every intake door: website single upload,
website batch upload, the three reprocess variants, and the bulk import
script. Bound by macro decisions D1-D14 (wayfinder map #4).
"""

from __future__ import annotations

import hashlib
import re
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import structlog
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from storage.index_writer import StorageIndexWriter
from config.settings import Settings
from crm.timeline_ledger import TimelineLedger
from ingestion.entity_resolution import (
    CandidateIdentifiers,
    ResolutionAction,
    resolve,
)
from storage.cas import CASManager
from storage.db_models import Candidate, CandidateClaim, EntityResolutionAudit, ResumeVersion

logger = structlog.get_logger(__name__)

# PR #25 review: identical uploads share one hash-derived CAS path. Track
# active holders per hash so a rejecting/failing pipeline can never delete
# the object another in-flight or already-committed pipeline still needs.
_CAS_ACTIVE_REFS: Dict[str, int] = {}
_CAS_REF_LOCK = threading.Lock()


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

FINANCIAL_BILL_KEYWORDS = [
    "bank statement", "account summary", "routing number", "account number",
    "billing statement", "invoice", "payment due", "amount enclosed",
    "tax invoice", "utility bill", "credit card statement", "deposit",
    "withdrawal", "balance summary", "statement of account"
]

RECRUITER_SUBMISSION_KEYWORDS = [
    "candidate submission", "candidate presentation", "submitted by",
    "recruiter notes", "agency submission", "candidate overview",
    "rate details", "availability:", "relocation:", "visa status:"
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

    # 4.5. Check Financial/Bills
    financial_matches = [kw for kw in FINANCIAL_BILL_KEYWORDS if kw in clean_text]
    if len(financial_matches) >= 2:
        return False, "NON_RESUME_FINANCIAL_BILL", f"Document identified as financial/bill from text (matched: {', '.join(financial_matches[:3])})"

    # 4.6. Check Recruiter Submission Sheets
    recruiter_matches = [kw for kw in RECRUITER_SUBMISSION_KEYWORDS if kw in clean_text]
    if len(recruiter_matches) >= 2:
        return False, "NON_RESUME_RECRUITER_SUBMISSION", f"Document identified as recruiter submission sheet from text (matched: {', '.join(recruiter_matches[:3])})"

    # 5. Check Resume Signals (must have at least one structural resume section or standard candidate contact indicators)
    signal_count = sum(1 for s in RESUME_SIGNALS if s in clean_text)
    has_email_or_phone = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text) or re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", text))

    if signal_count == 0 and not has_email_or_phone:
        from candidate_intelligence_platform.extraction.local_llm_fallback import classify_document_llm
        # LLM fallback for ambiguous docs (might be a resume with poor parsing or unusual structure)
        if classify_document_llm(text):
            return True, "VALID_RESUME", "Passed candidate resume verification via AI Fallback"
        
        return False, "NON_RESUME_INSUFFICIENT_SIGNALS", "Document lacks standard resume sections (no work experience, education, skills, or contact info) and failed AI fallback"

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


def _purge_cas_object(cas_mgr: CASManager, cas_path: Optional[str], warnings: List[str]) -> None:
    """Issue #14: a rejected upload leaves no trace - best-effort CAS purge.

    Never fatal: on failure the rejection still returns normally and a warning
    is attached so operators can see the cleanup could not happen.
    """
    if not cas_path:
        return
    try:
        purged = cas_mgr.delete(cas_path)
    except Exception as e:
        purged = False
        error = str(e)
    else:
        error = "CAS delete reported failure"
    if not purged:
        warnings.append(f"CAS purge failed for rejected document ({error}).")
        logger.warning("cas_purge_failed", cas_path=cas_path, error=error)


def _acquire_cas_ref(file_hash: str) -> None:
    """Register this pipeline as an active holder of the shared CAS object."""
    with _CAS_REF_LOCK:
        _CAS_ACTIVE_REFS[file_hash] = _CAS_ACTIVE_REFS.get(file_hash, 0) + 1


def _release_cas_ref(file_hash: str) -> None:
    """Drop one active-holder registration (no-op when nothing registered)."""
    with _CAS_REF_LOCK:
        count = _CAS_ACTIVE_REFS.get(file_hash, 0)
        if count > 1:
            _CAS_ACTIVE_REFS[file_hash] = count - 1
        else:
            _CAS_ACTIVE_REFS.pop(file_hash, None)


def _bind_release_on_commit(db: Session, file_hash: str) -> None:
    """Keep the hash hold until the caller's commit makes the row visible.

    PR #25 review round 2: releasing at the end of ingest_file leaves a gap
    where the RV is still uncommitted; a rejecting twin pipeline could then
    see zero holders and zero committed rows and delete the shared object.
    Tying the release to the session's after_commit event closes that gap.
    Idempotent: extra commits/rollbacks release a missing key as a no-op.
    """

    def _release(session: Session) -> None:
        _release_cas_ref(file_hash)

    event.listen(db, "after_commit", _release)
    event.listen(db, "after_rollback", _release)


def _has_committed_reference(db: Session, file_hash: str) -> bool:
    """True when a committed ResumeVersion already stores this hash.

    Uses a fresh connection so the caller's own pending (uncommitted, about
    to be rolled back) rows stay invisible. Failure fails safe by reporting
    a reference so the object is kept.
    """
    try:
        with db.get_bind().connect() as conn:
            row = conn.execute(
                select(ResumeVersion.id)
                .where(ResumeVersion.cas_file_hash == file_hash)
                .limit(1)
            ).first()
        return row is not None
    except Exception:
        return True


def _release_and_purge_if_last(
    cas_mgr: CASManager,
    db: Session,
    file_hash: Optional[str],
    cas_path: Optional[str],
    warnings: List[str],
) -> None:
    """Issue #14 + PR #25 review: reject/failure cleanup for the stored bytes.

    Deletes only when this pipeline was the sole active holder of the hash
    AND no committed ResumeVersion references it; otherwise another upload
    may depend on the very same content-addressed file. The committed check
    and the delete run inside the reference lock, so a concurrent identical
    upload either acquires before this point (count > 1, no delete) or after
    it (its store() recreates the bytes fresh) - never in between.
    """
    if not cas_path or not file_hash:
        return
    with _CAS_REF_LOCK:
        count = _CAS_ACTIVE_REFS.get(file_hash, 0)
        if count > 1:
            _CAS_ACTIVE_REFS[file_hash] = count - 1
            return
        _CAS_ACTIVE_REFS.pop(file_hash, None)
        if not _has_committed_reference(db, file_hash):
            _purge_cas_object(cas_mgr, cas_path, warnings)


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
         (stored bytes purged, #14)
      5. extraction exactly once with settings.extraction_confidence_threshold (D13)
      6. entity resolution vs current candidates, thresholds from Settings (D4)
      7. vector embeddings via StorageIndexWriter
         DB write, keeping the SQLite write txn short under parallel uploads
         (failure is never fatal)
      8. persist + flush, NO commit - caller commits once and owns rollback (D7)
      9. audit rows per #8 (MERGE and REVIEW write; NEW silent)
     10. FTS via StorageIndexWriter
      11. timeline per timeline_mode (D3)
    """
    warnings: List[str] = []
    cas_path: Optional[str] = None
    file_hash: Optional[str] = None
    try:
        # 1. Hash once + duplicate check before CAS store (D5). The hash
        # reference is taken BEFORE the check so a concurrent identical
        # upload can never slip between "check" and "hold".
        _emit(on_progress, "HASHING", 10, "Computing file hash and checking for duplicates")
        file_hash = hashlib.sha256(content).hexdigest()
        _acquire_cas_ref(file_hash)
        existing_rv = db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == file_hash).first()
        if existing_rv:
            logger.info("resume_upload_complete", status="skipped", skip_reason="cas_duplicate", file_hash=file_hash, file_name=filename or "")
            _release_cas_ref(file_hash)
            _emit(on_progress, "COMPLETED", 100, "File already exists", {"status": "SKIPPED_DUPLICATE"})
            return IntakeResult(
                status=IntakeStatus.SKIPPED_DUPLICATE,
                candidate_id=existing_rv.candidate_id,
                classified_as="DUPLICATE_FILE",
            )

        # 2. CAS store (object may already exist from a concurrent upload)
        ext = Path(filename).suffix if filename else ".txt"
        _, cas_path = cas_mgr.store(content, extension=ext)

        # 3. Parse
        _emit(on_progress, "PARSING", 25, f"Parsing {ext} document")
        raw_text = _parse_raw_text(content, cas_path, ext.lower(), warnings)

        # 4. Classify
        _emit(on_progress, "CLASSIFYING", 40, "Verifying document is a genuine resume")
        is_resume, category, reason = classify_document(raw_text, filename)
        if not is_resume:
            # Purge warnings isolated so the payload keeps reason as warnings[0]
            # and stays byte-identical to the pre-#14 contract on success.
            purge_warnings: List[str] = []
            _release_and_purge_if_last(cas_mgr, db, file_hash, cas_path, purge_warnings)
            logger.info("resume_upload_complete", status="skipped", skip_reason="non_resume", category=category, file_name=filename or "")
            _emit(on_progress, "COMPLETED", 100, reason, {"status": "SKIPPED_NON_RESUME", "classified_as": category})
            return IntakeResult(
                status=IntakeStatus.SKIPPED_NON_RESUME,
                classified_as=category,
                warnings=[reason, *purge_warnings],
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
            purge_warnings = []
            _release_and_purge_if_last(cas_mgr, db, file_hash, cas_path, purge_warnings)
            category = "AI_CLASSIFIED_NOT_RESUME"
            reason = "No identifiable candidate name or contact information found in document"
            logger.info("resume_upload_complete", status="skipped", skip_reason="non_resume", category=category, file_name=filename or "")
            _emit(on_progress, "COMPLETED", 100, reason, {"status": "SKIPPED_NON_RESUME", "classified_as": category})
            return IntakeResult(
                status=IntakeStatus.SKIPPED_NON_RESUME,
                classified_as=category,
                warnings=[reason, *purge_warnings],
            )

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
        is_merge = resolution.action == ResolutionAction.MERGE and resolution.matched_id
        is_new_candidate = False

        if is_merge:
            cand_id = resolution.matched_id
        elif resolution.action == ResolutionAction.REVIEW and resolution.matched_id:
            matched_candidate_id = resolution.matched_id

        if not cand_id:
            cand_id = str(uuid.uuid4())
            is_new_candidate = True

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

        vector_failed = False
        chunks = None
        embeddings = None
        if vector_db is not None:
            _emit(on_progress, "GENERATING_VECTORS", 75, "Generating vector embeddings")
            try:
                from ingestion.chunker import chunk_resume
                from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings
                from ingestion.parsers.models import ParsedDocument
                doc_obj = ParsedDocument(text=raw_text, pages=1)
                chunks = chunk_resume(doc_obj, cand_id)
                if chunks:
                    embeddings = generate_embeddings([c.text for c in chunks])
            except Exception as e:
                vector_failed = True
                warnings.append(f"Vector embeddings generation failed ({str(e)}).")

        if is_merge:
            # D12: demote current primary RV(s); incoming RV becomes primary
            db.query(ResumeVersion).filter(
                ResumeVersion.candidate_id == cand_id,
                ResumeVersion.is_primary == True,  # noqa: E712
            ).update({"is_primary": False})
            target_candidate = db.query(Candidate).filter(Candidate.id == cand_id).first()
            # Issue #15: the merged RV is the new primary, so the profile card
            # follows the freshest data. Same conditional-update semantics as
            # reprocess_text: overwrite only when extraction produced a value;
            # never clear stored data because extraction missed it.
            if target_candidate is not None:
                if first_name:
                    target_candidate.first_name = first_name
                if last_name:
                    target_candidate.last_name = last_name
                if email:
                    target_candidate.primary_email = email
                if phone:
                    target_candidate.primary_phone = phone
                if extracted.get("current_title"):
                    target_candidate.current_title = extracted["current_title"]

        if is_new_candidate:
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

        db.add(rv)
        
        # Flush parent records before inserting claims to guarantee insert order 
        # since we don't define SQLAlchemy relationships
        db.flush()

        for claim_dict in extracted.get("facts", []):
            claim = CandidateClaim(
                id=str(uuid.uuid4()),
                candidate_id=cand_id,
                resume_version_id=rv.id,
                source_type=claim_dict.get("source_type", "EXPLICIT_FACT"),
                claim_category=claim_dict.get("claim_category", "UNKNOWN"),
                claim_key=claim_dict.get("claim_key", ""),
                claim_value=claim_dict.get("claim_value", ""),
                confidence_score=claim_dict.get("confidence_score", 1.0),
                source_char_offset_start=claim_dict.get("source_char_offset_start"),
                source_char_offset_end=claim_dict.get("source_char_offset_end"),
                extracted_by=claim_dict.get("extracted_by", "SYSTEM")
            )
            db.add(claim)

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

        # 9. FTS and Vectors via StorageIndexWriter (atomic)
        _emit(on_progress, "UPDATING_FTS", 85, "Refreshing full-text search index and vectors")
        try:
            writer = StorageIndexWriter(db, vector_db)
            writer.write_candidate_indices(target_candidate, rv.id, raw_text, chunks=chunks, embeddings=embeddings)
        except Exception as e:
            vector_failed = True
            warnings.append(f"Search index update failed ({str(e)}).")

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

        # Success: the hold transfers to the caller's commit (D7). The CAS
        # object stays pinned until the RV row is actually visible.
        _bind_release_on_commit(db, file_hash)

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
        logger.error("resume_upload_complete", status="failed", file_name=filename or "", error=str(e))
        # Issue #14: caller rolls the txn back (D7), so stored bytes must go
        # too - unless a concurrent/committed pipeline shares the same object.
        purge_warnings: List[str] = []
        _release_and_purge_if_last(cas_mgr, db, file_hash, cas_path, purge_warnings)
        return IntakeResult(status=IntakeStatus.ERROR, classified_as="", warnings=[str(e), *purge_warnings])


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

        vector_failed = False
        chunks = None
        embeddings = None
        if vector_db is not None:
            _emit(on_progress, "GENERATING_VECTORS", 75, "Chunking document and re-generating vector embeddings")
            try:
                from ingestion.chunker import chunk_resume
                from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings
                from ingestion.parsers.models import ParsedDocument
                doc_obj = ParsedDocument(text=raw_text, pages=1)
                chunks = chunk_resume(doc_obj, candidate_id)
                if chunks:
                    embeddings = generate_embeddings([c.text for c in chunks])
            except Exception as e:
                vector_failed = True
                warnings.append(f"Vector embeddings generation failed ({str(e)}).")

        candidate.first_name = extracted.get("first_name", candidate.first_name)
        candidate.last_name = extracted.get("last_name", candidate.last_name)
        if extracted.get("primary_email"):
            candidate.primary_email = extracted["primary_email"]
        if extracted.get("primary_phone"):
            candidate.primary_phone = extracted["primary_phone"]
        if extracted.get("current_title"):
            candidate.current_title = extracted["current_title"]

        db.query(CandidateClaim).filter_by(resume_version_id=resume_version_id).delete()
        for claim_dict in extracted.get("facts", []):
            claim = CandidateClaim(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                resume_version_id=resume_version_id,
                source_type=claim_dict.get("source_type", "EXPLICIT_FACT"),
                claim_category=claim_dict.get("claim_category", "UNKNOWN"),
                claim_key=claim_dict.get("claim_key", ""),
                claim_value=claim_dict.get("claim_value", ""),
                confidence_score=claim_dict.get("confidence_score", 1.0),
                source_char_offset_start=claim_dict.get("source_char_offset_start"),
                source_char_offset_end=claim_dict.get("source_char_offset_end"),
                extracted_by=claim_dict.get("extracted_by", "SYSTEM")
            )
            db.add(claim)

        # FTS and Vector refresh
        _emit(on_progress, "UPDATING_FTS", 85, "Refreshing full-text search index and vectors")
        try:
            writer = StorageIndexWriter(db, vector_db)
            writer.write_candidate_indices(candidate, resume_version_id, raw_text, chunks=chunks, embeddings=embeddings)
        except Exception as e:
            vector_failed = True
            warnings.append(f"Search index update failed ({str(e)}).")

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

        final_status = IntakeStatus.PARTIAL if vector_failed else IntakeStatus.INGESTED
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
