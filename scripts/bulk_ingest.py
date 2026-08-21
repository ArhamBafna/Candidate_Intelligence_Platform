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
from api.dependencies import _SessionLocal as SessionLocal, get_vector_db
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

def process_single_file(filepath: Path, base_dir: Path, db, cas_mgr: CASManager) -> Tuple[bool, str, Dict[str, Any]]:
    """Process a single file. Returns (success, hash, details_or_error)"""
    ext = filepath.suffix.lower()
    
    try:
        content = filepath.read_bytes()
        file_hash = get_file_hash(filepath)
    except Exception as e:
        return False, "", {
            "category": "CORRUPTED_OR_UNREADABLE",
            "error": f"Failed to read file: {str(e)}",
            "trace": traceback.format_exc()
        }

    # 1. Deduplication via CAS Hash
    existing_rv = db.query(ResumeVersion).filter(ResumeVersion.cas_file_hash == file_hash).first()
    if existing_rv:
        return True, file_hash, {"status": "skipped", "reason": "cas_duplicate"}

    # Calculate taxonomy category tag
    rel_path = filepath.relative_to(base_dir)
    folder_tag = str(rel_path.parent) if str(rel_path.parent) != "." else "Uncategorized"

    # 2. Store in CAS
    try:
        _, cas_path = cas_mgr.store(content, extension=ext)
    except Exception as e:
        return False, file_hash, {
            "category": "CAS_STORAGE_ERROR",
            "error": f"CAS Storage failed: {str(e)}",
            "trace": traceback.format_exc()
        }

    # 3. Parse Document
    raw_text = ""
    file_warnings: List[str] = []
    
    try:
        if ext == ".pdf":
            from ingestion.parsers.pdf_parser import parse_pdf
            doc = parse_pdf(Path(cas_path))
            raw_text = doc.text
        elif ext == ".docx":
            from ingestion.parsers.docx_parser import parse_docx
            doc = parse_docx(Path(cas_path))
            raw_text = doc.text
        elif ext in [".eml", ".msg"]:
            from ingestion.parsers.email_parser import parse_email
            doc = parse_email(Path(cas_path))
            raw_text = doc.text
        elif ext == ".doc":
            raw_text = content.decode("utf-8", errors="ignore")
            file_warnings.append("Legacy .doc format extracted via raw text fallback.")
        else:
            raw_text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        if ext in [".pdf", ".docx", ".eml", ".msg"]:
            raw_text = content.decode("utf-8", errors="ignore")
            file_warnings.append(f"Structured parser failed ({str(e)}), used raw text fallback.")
        else:
            return False, file_hash, {
                "category": "PARSING_FAILED",
                "error": f"Parsing failed: {str(e)}",
                "trace": traceback.format_exc()
            }

    # 4. Classify Resume vs Non-Resume
    is_resume, category, reason = classify_document(raw_text, filepath.name)
    if not is_resume:
        return False, file_hash, {
            "category": category,
            "error": reason,
            "trace": ""
        }

    # 5. Entity Extraction & Validation
    try:
        extracted = extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
        if extracted.get("warnings"):
            file_warnings.extend(extracted["warnings"])

        first_name = extracted.get("first_name", "").strip()
        last_name = extracted.get("last_name", "").strip()
        email = extracted.get("primary_email")
        phone = extracted.get("primary_phone")
        full_name = f"{first_name} {last_name}".strip()

        # Reject dummy names with no contact details
        is_dummy_name = (first_name.lower() in ["uploaded", ""] and last_name.lower() in ["candidate", ""])
        if is_dummy_name and not email and not phone:
            return False, file_hash, {
                "category": "AI_CLASSIFIED_NOT_RESUME",
                "error": "No identifiable candidate name or contact information found in document",
                "trace": ""
            }

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
        
    except Exception as e:
        return False, file_hash, {
            "category": "DATABASE_ERROR",
            "error": f"Database insertion failed: {str(e)}",
            "trace": traceback.format_exc()
        }

    # 7. Vector Store (LanceDB)
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
    except Exception as e:
        file_warnings.append(f"Vector indexing skipped: {str(e)}")

    return True, file_hash, {"status": "success", "candidate_id": cand_id, "warnings": file_warnings}

def run_bulk_ingest(
    source_dir: str,
    batch_size: int,
    checkpoint_file: str,
    unprocessed_log: str,
    dry_run: bool = False
):
    base_dir = Path(source_dir)
    if not base_dir.exists():
        logger.error("Source directory does not exist", directory=source_dir)
        return

    checkpoint_path = Path(checkpoint_file)
    unprocessed_path = Path(unprocessed_log)
    
    processed_files: Set[str] = set()
    if checkpoint_path.exists():
        try:
            state = json.loads(checkpoint_path.read_text())
            processed_files = set(state.get("processed_paths", []))
            logger.info("Loaded checkpoint", count=len(processed_files))
        except Exception as e:
            logger.error("Failed to load checkpoint", error=str(e))
    
    unprocessed_records: List[Dict[str, Any]] = []
    if unprocessed_path.exists():
        try:
            unprocessed_records = json.loads(unprocessed_path.read_text())
        except Exception:
            pass

    cas_mgr = CASManager(Settings().cas_root_dir)
    db = SessionLocal()
    
    processed_this_run = 0
    skipped_this_run = 0
    unprocessed_this_run = 0

    print(f"Scanning directory: {base_dir}")
    
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

            # Log non-supported extensions (e.g. standalone images, .zip, etc.)
            if ext in IMAGE_EXTENSIONS:
                if not dry_run:
                    unprocessed_this_run += 1
                    processed_files.add(rel_path_str)
                    unprocessed_records.append({
                        "path": rel_path_str,
                        "category": "STANDALONE_IMAGE",
                        "reason": f"Standalone image file ({ext}) requires OCR extraction pipeline",
                        "file_size": filepath.stat().st_size if filepath.exists() else 0,
                        "timestamp": datetime.now().isoformat()
                    })
                    checkpoint_path.write_text(json.dumps({"processed_paths": list(processed_files)}, indent=2))
                    unprocessed_path.write_text(json.dumps(unprocessed_records, indent=2))
                continue

            if ext not in SUPPORTED_EXTENSIONS:
                continue

            if dry_run:
                print(f"[DRY RUN] Would evaluate: {rel_path_str}")
                processed_this_run += 1
                if processed_this_run >= batch_size:
                    print("Dry run batch limit reached.")
                    return
                continue

            # Process inside a savepoint transaction
            success, file_hash, details = process_single_file(filepath, base_dir, db, cas_mgr)
            
            if success:
                if details.get("status") == "skipped":
                    skipped_this_run += 1
                    logger.info("File skipped", path=rel_path_str, reason=details.get("reason"))
                else:
                    processed_this_run += 1
                    logger.info("Processed resume", path=rel_path_str, candidate_id=details.get("candidate_id"))
                    
                processed_files.add(rel_path_str)
                db.commit() # Commit successful transaction
            else:
                db.rollback() # Rollback on failure / non-resume
                unprocessed_this_run += 1
                processed_files.add(rel_path_str) # Mark as handled so we don't re-attempt
                
                cat = details.get("category", "NON_RESUME_OR_ERROR")
                err_msg = details.get("error", "Unknown error")
                logger.info("File not ingested as resume", path=rel_path_str, category=cat, reason=err_msg)
                
                unprocessed_records.append({
                    "path": rel_path_str,
                    "category": cat,
                    "reason": err_msg,
                    "hash": file_hash,
                    "file_size": filepath.stat().st_size if filepath.exists() else 0,
                    "timestamp": datetime.now().isoformat(),
                    "trace": details.get("trace", "")
                })
            
            # Update Checkpoint & Unprocessed Logs
            checkpoint_path.write_text(json.dumps({"processed_paths": list(processed_files)}, indent=2))
            unprocessed_path.write_text(json.dumps(unprocessed_records, indent=2))

            if processed_this_run >= batch_size:
                logger.info(
                    "Batch limit reached",
                    resumes_ingested=processed_this_run,
                    skipped_duplicates=skipped_this_run,
                    unprocessed_non_resumes=unprocessed_this_run
                )
                db.close()
                return

    logger.info(
        "Ingestion complete. No more files to process.",
        resumes_ingested=processed_this_run,
        skipped_duplicates=skipped_this_run,
        unprocessed_non_resumes=unprocessed_this_run
    )
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk Resume Ingestion Script")
    parser.add_argument("--source-dir", type=str, default=r"G:\My Drive\intellect_iSolutons\All_Resumes\Resumes", help="Path to resumes folder")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of valid resumes to ingest in this run")
    parser.add_argument("--checkpoint-file", type=str, default="bulk_ingest_checkpoint.json", help="Path to checkpoint JSON file")
    parser.add_argument("--unprocessed-log", type=str, default="bulk_ingest_unprocessed.json", help="Path to unprocessed non-resume log JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Scan and list files without processing")
    
    args = parser.parse_args()
    
    run_bulk_ingest(
        source_dir=args.source_dir,
        batch_size=args.batch_size,
        checkpoint_file=args.checkpoint_file,
        unprocessed_log=args.unprocessed_log,
        dry_run=args.dry_run
    )
