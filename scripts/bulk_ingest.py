import argparse
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import hashlib
import uuid
import re
import structlog
import traceback
from datetime import datetime
from typing import Set, Dict, Any, Tuple, List, Optional

from config.settings import Settings
from api.dependencies import _get_sessionmaker, get_vector_db
from storage.cas import CASManager
from storage.db_models import Candidate, ResumeVersion, CandidateTimelineEvent
from candidate_intelligence_platform.extraction.hybrid_extractor import extract_candidate_profile_hybrid
from ingestion.entity_resolution import resolve, CandidateIdentifiers, ResolutionAction
from ingestion.chunker import chunk_document
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings
from storage.vector_store import CandidateSectionVector
from sqlalchemy import text

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {".docx", ".doc", ".pdf", ".msg", ".eml", ".txt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".jfif", ".gif"}

# Non-resume pattern detectors
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

def get_file_hash(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

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

def generate_markdown_summary(report_records: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Generate a clean, structured, human-readable Markdown report summarizing the ingestion run.
    """
    ingested = [r for r in report_records if r.get("status") in ["SUCCESS", "PARTIAL_SUCCESS"]]
    skipped_non_resumes = [r for r in report_records if r.get("status") == "SKIPPED_NON_RESUME"]
    duplicates = [r for r in report_records if r.get("status") == "SKIPPED_DUPLICATE"]
    failed = [r for r in report_records if r.get("status") == "FAILED"]

    # Category counts for non-resumes
    category_counts: Dict[str, int] = {}
    for r in skipped_non_resumes:
        cat = r.get("category", "UNKNOWN")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    md_lines = [
        "# Bulk Resume Ingestion Summary Report",
        "",
        f"- **Total Files Evaluated:** {len(report_records)}",
        f"- **Ingested (Valid Resumes):** {len(ingested)}",
        f"- **Skipped (Non-Resumes & Docs):** {len(skipped_non_resumes)}",
        f"- **Skipped (Duplicates):** {len(duplicates)}",
        f"- **Failed / Ingestion Errors:** {len(failed)}",
        "",
        "---",
        "",
        "## 1. Ingested Resumes",
        "",
        "| # | Candidate Name | Parser Engine | AI Used | Folder | File Name |",
        "|---|----------------|---------------|---------|--------|-----------|",
    ]

    for idx, r in enumerate(ingested, 1):
        name = r.get("candidate_name") or "Unknown"
        parser = r.get("how_processed") or "N/A"
        ai_used = "Yes" if r.get("ai_used") else "No"
        folder = r.get("folder_tag") or "Root"
        fname = r.get("file_name") or ""
        md_lines.append(f"| {idx} | **{name}** | `{parser}` | {ai_used} | `{folder}` | `{fname}` |")

    if not ingested:
        md_lines.append("| - | *No resumes ingested in this run* | - | - | - | - |")

    md_lines.extend([
        "",
        "---",
        "",
        "## 2. Skipped Non-Resume Breakdown",
        "",
        "| Category | Count | Common Reason / Document Type |",
        "|----------|-------|-------------------------------|",
    ])

    category_descriptions = {
        "SCANNED_IMAGE_REQUIRES_OCR": "Scanned document / image PDF without OCR text layer (<50 chars)",
        "STANDALONE_IMAGE": "Standalone image file (.jpg, .png, etc.) requiring OCR pipeline",
        "NON_RESUME_IMMIGRATION_OR_ID": "Government ID, Driver's License, Visa, Passport, or H-1B notice",
        "NON_RESUME_LEGAL_CONTRACT": "Legal contract, Referral Agreement, NDA, or Vendor Agreement",
        "NON_RESUME_STUDY_OR_TEMPLATE": "Interview study guide, question bank, or submission template",
        "AI_CLASSIFIED_NOT_RESUME": "No identifiable candidate name or contact information found",
        "NON_RESUME_INSUFFICIENT_SIGNALS": "Document lacks standard resume sections (experience, education, skills)",
    }

    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        desc = category_descriptions.get(cat, "Non-resume document")
        md_lines.append(f"| `{cat}` | **{count}** | {desc} |")

    if not category_counts:
        md_lines.append("| *None* | 0 | *No non-resumes encountered* |")

    if failed:
        md_lines.extend([
            "",
            "---",
            "",
            "## 3. Failed Ingestion Errors",
            "",
            "| File Name | Folder | Category | Error Reason |",
            "|-----------|--------|----------|--------------|",
        ])
        for r in failed:
            fname = r.get("file_name") or ""
            folder = r.get("folder_tag") or ""
            cat = r.get("category") or ""
            err = r.get("error") or "Unknown error"
            md_lines.append(f"| `{fname}` | `{folder}` | `{cat}` | {err} |")

    md_lines.append("")
    output_path.write_text("\n".join(md_lines), encoding="utf-8")

def process_single_file(filepath: Path, base_dir: Path, db, cas_mgr: CASManager) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Process a single file through the full ingestion pipeline with fine-grained stage tracking.
    Returns: (success: bool, hash: str, telemetry: Dict[str, Any])
    """
    ext = filepath.suffix.lower()
    rel_path = filepath.relative_to(base_dir)
    rel_path_str = str(rel_path)
    folder_tag = str(rel_path.parent) if str(rel_path.parent) != "." else "Uncategorized"

    stages_succeeded: List[str] = []
    stages_failed: List[str] = []
    file_warnings: List[str] = []
    
    telemetry: Dict[str, Any] = {
        "file_path": rel_path_str,
        "file_name": filepath.name,
        "file_type": ext,
        "folder_tag": folder_tag,
        "candidate_id": None,
        "candidate_name": None,
        "status": "FAILED",
        "how_processed": "None",
        "ai_used": False,
        "confidence_score": 0.0,
        "stages_succeeded": stages_succeeded,
        "stages_failed": stages_failed,
        "warnings": file_warnings,
        "category": "UNKNOWN",
        "error": None
    }

    try:
        content = filepath.read_bytes()
        file_hash = get_file_hash(filepath)
        stages_succeeded.append("FILE_READ")
    except Exception as e:
        stages_failed.append("FILE_READ")
        telemetry.update({
            "category": "CORRUPTED_OR_UNREADABLE",
            "error": f"Failed to read file: {str(e)}"
        })
        return False, "", telemetry

    # 1. Deduplication via CAS Hash
    existing_rv = db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == file_hash).first()
    if existing_rv:
        telemetry.update({
            "status": "SKIPPED_DUPLICATE",
            "candidate_id": existing_rv.candidate_id,
            "category": "DUPLICATE_FILE",
            "reason": "Exact CAS file hash already ingested in database"
        })
        return True, file_hash, telemetry

    # 2. Store in CAS
    try:
        _, cas_path = cas_mgr.store(content, extension=ext)
        stages_succeeded.append("CAS_STORE")
    except Exception as e:
        stages_failed.append("CAS_STORE")
        telemetry.update({
            "category": "CAS_STORAGE_ERROR",
            "error": f"CAS Storage failed: {str(e)}"
        })
        return False, file_hash, telemetry

    # 3. Parse Document
    raw_text = ""
    how_processed = "None"
    
    try:
        if ext == ".pdf":
            from ingestion.parsers.pdf_parser import parse_pdf
            doc = parse_pdf(Path(cas_path))
            raw_text = doc.text
            how_processed = "PyMuPDF_Parser"
        elif ext == ".docx":
            from ingestion.parsers.docx_parser import parse_docx
            doc = parse_docx(Path(cas_path))
            raw_text = doc.text
            how_processed = "Docx_Parser"
        elif ext in [".eml", ".msg"]:
            from ingestion.parsers.email_parser import parse_email
            doc = parse_email(Path(cas_path))
            raw_text = doc.text
            how_processed = "Email_Parser"
        elif ext == ".doc":
            raw_text = content.decode("utf-8", errors="ignore")
            how_processed = "Raw_Text_Fallback"
            file_warnings.append("Legacy .doc format extracted via raw text fallback.")
        else:
            raw_text = content.decode("utf-8", errors="ignore")
            how_processed = "Raw_Text_Fallback"
            
        stages_succeeded.append("TEXT_PARSING")
    except Exception as e:
        if ext in [".pdf", ".docx", ".eml", ".msg"]:
            raw_text = content.decode("utf-8", errors="ignore")
            how_processed = "Raw_Text_Fallback"
            file_warnings.append(f"Structured parser failed ({str(e)}), used raw text fallback.")
            stages_succeeded.append("TEXT_PARSING")
        else:
            stages_failed.append("TEXT_PARSING")
            telemetry.update({
                "how_processed": how_processed,
                "category": "PARSING_FAILED",
                "error": f"Parsing failed: {str(e)}"
            })
            return False, file_hash, telemetry

    telemetry["how_processed"] = how_processed

    # 4. Classify Resume vs Non-Resume
    is_resume, category, reason = classify_document(raw_text, filepath.name)
    if not is_resume:
        stages_failed.append("DOCUMENT_CLASSIFICATION")
        telemetry.update({
            "status": "SKIPPED_NON_RESUME",
            "category": category,
            "error": reason
        })
        return False, file_hash, telemetry

    stages_succeeded.append("DOCUMENT_CLASSIFICATION")

    # 5. Entity Extraction & Profile Extraction
    try:
        extracted = extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
        if extracted.get("warnings"):
            file_warnings.extend(extracted["warnings"])

        first_name = extracted.get("first_name", "").strip()
        last_name = extracted.get("last_name", "").strip()
        email = extracted.get("primary_email")
        phone = extracted.get("primary_phone")
        full_name = f"{first_name} {last_name}".strip()
        
        telemetry["candidate_name"] = full_name
        telemetry["ai_used"] = extracted.get("used_ai_fallback", False)
        telemetry["confidence_score"] = extracted.get("confidence_score", 0.0)

        # Reject dummy names with no contact details
        is_dummy_name = (first_name.lower() in ["uploaded", ""] and last_name.lower() in ["candidate", ""])
        if is_dummy_name and not email and not phone:
            stages_failed.append("PROFILE_EXTRACTION")
            telemetry.update({
                "status": "SKIPPED_NON_RESUME",
                "category": "AI_CLASSIFIED_NOT_RESUME",
                "error": "No identifiable candidate name or contact information found in document"
            })
            return False, file_hash, telemetry

        stages_succeeded.append("PROFILE_EXTRACTION")

        cand_id = None
        cand = None

        # Entity Resolution (only if real identifier exists)
        if not is_dummy_name or email or phone:
            incoming_identifiers = CandidateIdentifiers(
                candidate_id="temp",
                email=email,
                phone=phone,
                full_name="" if is_dummy_name else full_name
            )

            existing_cands = db.query(Candidate).all()
            existing_identifiers = [
                CandidateIdentifiers(
                    c.id, c.primary_email, c.primary_phone, None,
                    "" if f"{c.first_name} {c.last_name}".strip() == "Uploaded Candidate" else f"{c.first_name} {c.last_name}".strip()
                )
                for c in existing_cands
            ]

            resolution = resolve(incoming_identifiers, existing_identifiers)
            if resolution.action == ResolutionAction.MERGE and resolution.matched_id:
                cand_id = resolution.matched_id
                stages_succeeded.append("ENTITY_MERGE")
                db.query(ResumeVersion).filter(
                    ResumeVersion.candidate_id == cand_id,
                    ResumeVersion.is_primary == True
                ).update({"is_primary": False})

        if not cand_id:
            cand_id = str(uuid.uuid4())
            cand = Candidate(
                id=cand_id,
                first_name=first_name if first_name else "Candidate",
                last_name=last_name if last_name else "",
                primary_email=email,
                primary_phone=phone,
                availability_status="ACTIVE",
                current_title=extracted.get("current_title", "Candidate")
            )
            db.add(cand)
            stages_succeeded.append("CANDIDATE_CREATION")

        telemetry["candidate_id"] = cand_id

        layout_metadata = {"source_folder": folder_tag}
        
        rv = ResumeVersion(
            id=str(uuid.uuid4()),
            candidate_id=cand_id,
            cas_file_hash=file_hash,
            original_filename=filepath.name,
            file_type=ext.replace(".", "").upper(),
            raw_text=raw_text,
            layout_metadata=layout_metadata,
            is_primary=True
        )
        db.add(rv)

        # Timeline Event
        event = CandidateTimelineEvent(
            id=str(uuid.uuid4()),
            candidate_id=cand_id,
            event_type="RESUME_INGESTED",
            title="Resume Ingested (Batch)",
            description=f"File {filepath.name} imported from folder '{folder_tag}'",
            created_by="System"
        )
        db.add(event)
        
        # 6. SQLite FTS Insertion
        db.execute(
            text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
            {
                "cid": cand_id,
                "fname": full_name,
                "title": extracted.get("current_title", ""),
                "company": extracted.get("current_company", ""),
                "content": raw_text
            }
        )

        db.flush()
        stages_succeeded.append("DATABASE_INSERTION")
        stages_succeeded.append("FTS_INDEXING")
        
    except Exception as e:
        stages_failed.append("DATABASE_INSERTION")
        telemetry.update({
            "category": "DATABASE_ERROR",
            "error": f"Database insertion failed: {str(e)}"
        })
        return False, file_hash, telemetry

    # 7. Vector Store (LanceDB)
    vector_succeeded = False
    try:
        from ingestion.parsers.models import ParsedDocument
        doc_model = ParsedDocument(text=raw_text, pages=1)
        chunks = chunk_document(doc_model, cand_id, "SUMMARY")
        
        if chunks:
            texts = [c.text for c in chunks]
            embeddings = generate_embeddings(texts)
            vector_db = get_vector_db()
            if vector_db:
                table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
                records = []
                for i, chunk in enumerate(chunks):
                    records.append({
                        "chunk_id": chunk.chunk_id,
                        "candidate_id": chunk.candidate_id,
                        "resume_version_id": rv.id,
                        "section_type": chunk.section_name,
                        "chunk_text": chunk.text,
                        "vector": embeddings[i],
                        "start_offset": chunk.start_offset,
                        "end_offset": chunk.end_offset
                    })
                table.add(records)
                stages_succeeded.append("VECTOR_INDEXING")
                vector_succeeded = True
    except Exception as e:
        stages_failed.append("VECTOR_INDEXING")
        file_warnings.append(f"Vector indexing skipped: {str(e)}")

    if file_warnings or not vector_succeeded:
        telemetry["status"] = "PARTIAL_SUCCESS"
    else:
        telemetry["status"] = "SUCCESS"

    telemetry["category"] = "VALID_RESUME"
    return True, file_hash, telemetry

def run_bulk_ingest(
    source_dir: str,
    batch_size: int,
    output_dir: Optional[str] = "ingestion_reports",
    checkpoint_file: Optional[str] = None,
    report_file: Optional[str] = None,
    unprocessed_log: Optional[str] = None,
    summary_file: Optional[str] = None,
    dry_run: bool = False
):
    base_dir = Path(source_dir)
    if not base_dir.exists():
        logger.error("Source directory does not exist", directory=source_dir)
        return

    out_dir_path = Path(output_dir) if output_dir else Path(".")
    if not dry_run and output_dir:
        out_dir_path.mkdir(parents=True, exist_ok=True)

    checkpoint_name = checkpoint_file if checkpoint_file else "bulk_ingest_checkpoint.json"
    report_name = report_file if report_file else "bulk_ingest_report.json"
    unprocessed_name = unprocessed_log if unprocessed_log else "bulk_ingest_unprocessed.json"
    summary_name = summary_file if summary_file else "bulk_ingest_summary.md"

    checkpoint_path = Path(checkpoint_name) if (checkpoint_file and Path(checkpoint_file).is_absolute()) else out_dir_path / checkpoint_name
    report_path = Path(report_name) if (report_file and Path(report_file).is_absolute()) else out_dir_path / report_name
    unprocessed_path = Path(unprocessed_name) if (unprocessed_log and Path(unprocessed_log).is_absolute()) else out_dir_path / unprocessed_name
    summary_path = Path(summary_name) if (summary_file and Path(summary_file).is_absolute()) else out_dir_path / summary_name
    
    processed_files: Set[str] = set()
    if checkpoint_path.exists():
        try:
            state = json.loads(checkpoint_path.read_text())
            processed_files = set(state.get("processed_paths", []))
            print(f"[*] Loaded checkpoint: {len(processed_files)} previously evaluated files.")
        except Exception as e:
            logger.error("Failed to load checkpoint", error=str(e))
    
    report_records: List[Dict[str, Any]] = []
    if report_path.exists():
        try:
            report_records = json.loads(report_path.read_text())
        except Exception:
            pass

    unprocessed_records: List[Dict[str, Any]] = []
    if unprocessed_path.exists():
        try:
            unprocessed_records = json.loads(unprocessed_path.read_text())
        except Exception:
            pass

    cas_mgr = CASManager(Settings().cas_root_dir)
    SessionLocal = _get_sessionmaker(Settings().db_path)
    db = SessionLocal()
    
    scanned_count = 0
    success_count = 0
    partial_count = 0
    duplicate_count = 0
    unprocessed_count = 0
    failed_count = 0

    print(f"\n=======================================================")
    print(f"  CIP Bulk Ingestion Engine")
    print(f"  Source Directory: {base_dir}")
    print(f"  Output Directory: {out_dir_path.resolve()}")
    print(f"  Batch Size Limit: {batch_size}")
    print(f"  Master Report:   {report_path}")
    print(f"  Summary Report:  {summary_path}")
    print(f"=======================================================\n")
    
    # Generator-based traversal
    for root, _, files in os.walk(base_dir):
        for filename in files:
            # Silently skip MS Word temporary/lock files & system files
            if filename.startswith("~$") or filename.startswith("._") or filename in ["desktop.ini", ".DS_Store"]:
                continue
                
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()
            rel_path_str = str(filepath.relative_to(base_dir))
            
            # Checkpoint filter
            if rel_path_str in processed_files:
                continue

            scanned_count += 1

            # Log non-supported extensions (e.g. standalone images, .zip, etc.)
            if ext in IMAGE_EXTENSIONS:
                if not dry_run:
                    unprocessed_count += 1
                    processed_files.add(rel_path_str)
                    img_telemetry = {
                        "file_path": rel_path_str,
                        "file_name": filepath.name,
                        "file_type": ext,
                        "folder_tag": str(filepath.relative_to(base_dir).parent),
                        "candidate_id": None,
                        "candidate_name": None,
                        "status": "SKIPPED_NON_RESUME",
                        "how_processed": "None",
                        "ai_used": False,
                        "confidence_score": 0.0,
                        "stages_succeeded": [],
                        "stages_failed": ["DOCUMENT_CLASSIFICATION"],
                        "warnings": [],
                        "category": "STANDALONE_IMAGE",
                        "error": f"Standalone image file ({ext}) requires OCR extraction pipeline"
                    }
                    report_records.append(img_telemetry)
                    unprocessed_records.append(img_telemetry)
                    print(f"[  -  ] (File #{scanned_count:3d}) [SKIP] Standalone Image (Needs OCR): {filepath.name}")
                    checkpoint_path.write_text(json.dumps({"processed_paths": list(processed_files)}, indent=2))
                    report_path.write_text(json.dumps(report_records, indent=2))
                    unprocessed_path.write_text(json.dumps(unprocessed_records, indent=2))
                    generate_markdown_summary(report_records, summary_path)
                continue

            if ext not in SUPPORTED_EXTENSIONS:
                continue

            if dry_run:
                print(f"[DRY RUN {success_count + 1:2d}/{batch_size}] (File #{scanned_count:3d}) Would evaluate: {rel_path_str}")
                success_count += 1
                if success_count >= batch_size:
                    print(f"\n[DRY RUN] Batch limit of {batch_size} reached. Simulation completed.")
                    return
                continue

            # Process inside a savepoint transaction
            success, file_hash, telemetry = process_single_file(filepath, base_dir, db, cas_mgr)
            
            # Update telemetry master log & unprocessed log
            report_records.append(telemetry)
            processed_files.add(rel_path_str)
            
            status = telemetry.get("status")
            cand_name = telemetry.get("candidate_name") or "N/A"
            how_proc = telemetry.get("how_processed")
            ai_flag = "Ollama" if telemetry.get("ai_used") else "Deterministic"

            if success:
                if status == "SKIPPED_DUPLICATE":
                    duplicate_count += 1
                    print(f"[  -  ] (File #{scanned_count:3d}) [SKIP] Duplicate File: {filepath.name}")
                elif status == "PARTIAL_SUCCESS":
                    partial_count += 1
                    db.commit()
                    curr = success_count + partial_count
                    print(f"[{curr:2d}/{batch_size}] (File #{scanned_count:3d}) [OK]   Ingested Resume (Partial): '{cand_name}' | {how_proc} | {rel_path_str}")
                else:
                    success_count += 1
                    db.commit()
                    curr = success_count + partial_count
                    print(f"[{curr:2d}/{batch_size}] (File #{scanned_count:3d}) [OK]   Ingested Resume: '{cand_name}' | {how_proc} ({ai_flag}) | {rel_path_str}")
            else:
                db.rollback()
                if status == "SKIPPED_NON_RESUME":
                    unprocessed_count += 1
                    unprocessed_records.append(telemetry)
                    print(f"[  -  ] (File #{scanned_count:3d}) [SKIP] Non-Resume [{telemetry.get('category')}]: {filepath.name}")
                else:
                    failed_count += 1
                    unprocessed_records.append(telemetry)
                    print(f"[  -  ] (File #{scanned_count:3d}) [FAIL] Ingestion Error [{telemetry.get('category')}]: {filepath.name} ({telemetry.get('error')})")
            
            # Write out persisted checkpoints, JSON logs, and Markdown summary
            checkpoint_path.write_text(json.dumps({"processed_paths": list(processed_files)}, indent=2))
            report_path.write_text(json.dumps(report_records, indent=2))
            unprocessed_path.write_text(json.dumps(unprocessed_records, indent=2))
            generate_markdown_summary(report_records, summary_path)

            if success_count + partial_count >= batch_size:
                print(f"\n=======================================================")
                print(f"  Batch Ingestion Limit ({batch_size}) Reached!")
                print(f"  - Ingested (Full Success):    {success_count}")
                print(f"  - Ingested (Partial Success): {partial_count}")
                print(f"  - Skipped Duplicates:         {duplicate_count}")
                print(f"  - Skipped Non-Resumes:        {unprocessed_count}")
                print(f"  - Failed / Errors:            {failed_count}")
                print(f"  - Master Audit Log:           {report_path}")
                print(f"  - Markdown Summary:           {summary_path}")
                print(f"=======================================================\n")
                db.close()
                return

    print(f"\n=======================================================")
    print(f"  Ingestion Complete! No more files to process.")
    print(f"  - Ingested (Full Success):    {success_count}")
    print(f"  - Ingested (Partial Success): {partial_count}")
    print(f"  - Skipped Duplicates:         {duplicate_count}")
    print(f"  - Skipped Non-Resumes:        {unprocessed_count}")
    print(f"  - Failed / Errors:            {failed_count}")
    print(f"  - Master Audit Log:           {report_path}")
    print(f"  - Markdown Summary:           {summary_path}")
    print(f"=======================================================")
    print()
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Resume Ingestion Script")
    parser.add_argument("--source-dir", type=str, default=r"G:\My Drive\intellect_iSolutons\All_Resumes\Resumes", help="Path to resumes folder")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of valid resumes to ingest in this run")
    parser.add_argument("--output-dir", type=str, default="ingestion_reports", help="Directory where all generated reports, summaries, and checkpoints are stored")
    parser.add_argument("--checkpoint-file", type=str, default=None, help="Name or path to checkpoint JSON file (saved in output-dir by default)")
    parser.add_argument("--report-file", type=str, default=None, help="Name or path to master audit JSON report (saved in output-dir by default)")
    parser.add_argument("--unprocessed-log", type=str, default=None, help="Name or path to unprocessed non-resume log JSON file (saved in output-dir by default)")
    parser.add_argument("--summary-file", type=str, default=None, help="Name or path to generated Markdown summary report (saved in output-dir by default)")
    parser.add_argument("--dry-run", action="store_true", help="Scan and list files without processing")
    
    args = parser.parse_args()
    
    run_bulk_ingest(
        source_dir=args.source_dir,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
        checkpoint_file=args.checkpoint_file,
        report_file=args.report_file,
        unprocessed_log=args.unprocessed_log,
        summary_file=args.summary_file,
        dry_run=args.dry_run
    )
