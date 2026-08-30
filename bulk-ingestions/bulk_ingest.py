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

from config.settings import get_settings
from api.dependencies import _get_sessionmaker, get_vector_db
from storage.cas import CASManager
from storage.db_models import Candidate, CandidateTimelineEvent
from candidate_intelligence_platform.ingestion.intake import (
    ingest_file,
    IntakeSource,
    IntakeStatus,
    TimelineMode,
)
from ingestion.entity_resolution import ResolutionAction

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {".docx", ".doc", ".pdf", ".msg", ".eml", ".txt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".jfif", ".gif"}
DEFAULT_EXCLUDED_DIRS = {"candidate details"}

def get_file_hash(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

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

def _derive_how_processed(ext: str, warnings: List[str]) -> str:
    """Map extension (+ parser-fallback warning) to the legacy how_processed label."""
    fallback = any(w.startswith("Structured parser failed") for w in warnings)
    if ext == ".pdf":
        return "Raw_Text_Fallback" if fallback else "PyMuPDF_Parser"
    if ext == ".docx":
        return "Raw_Text_Fallback" if fallback else "Docx_Parser"
    if ext in [".eml", ".msg"]:
        return "Raw_Text_Fallback" if fallback else "Email_Parser"
    return "Raw_Text_Fallback"

def process_single_file(filepath: Path, base_dir: Path, db, cas_mgr: CASManager) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Process a single file through the unified intake pipeline (issue #12), adapting
    the IntakeResult into this script's legacy telemetry shape. Report statuses,
    categories, and print strings are preserved byte-identically; a new optional
    telemetry key `resolution_action` is added.
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
        "error": None,
        "resolution_action": None
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

    # Unified intake pipeline (D5 dedup-before-CAS included; D7 caller owns commit)
    result = ingest_file(
        content=content,
        filename=filepath.name,
        db=db,
        cas_mgr=cas_mgr,
        vector_db=get_vector_db(),
        settings=get_settings(),
        source=IntakeSource.BULK,
        timeline_mode=TimelineMode.NONE,
        folder_tag=folder_tag,
    )
    telemetry["resolution_action"] = result.resolution_action.value if result.resolution_action else None

    # 1. Deduplication via CAS Hash (handled before CAS store inside the pipeline, D5)
    if result.status == IntakeStatus.SKIPPED_DUPLICATE:
        telemetry.update({
            "status": "SKIPPED_DUPLICATE",
            "candidate_id": result.candidate_id,
            "category": "DUPLICATE_FILE",
            "reason": "Exact CAS file hash already ingested in database"
        })
        return True, file_hash, telemetry

    # 2. Non-resume rejection: nothing persisted by the pipeline
    if result.status == IntakeStatus.SKIPPED_NON_RESUME:
        category = result.classified_as or "UNKNOWN"
        reason = result.warnings[0] if result.warnings else "Document rejected"
        stages_succeeded.extend(["CAS_STORE", "TEXT_PARSING"])
        if category == "AI_CLASSIFIED_NOT_RESUME":
            stages_succeeded.append("DOCUMENT_CLASSIFICATION")
            stages_failed.append("PROFILE_EXTRACTION")
        else:
            stages_failed.append("DOCUMENT_CLASSIFICATION")
        telemetry.update({
            "how_processed": _derive_how_processed(ext, result.warnings),
            "status": "SKIPPED_NON_RESUME",
            "category": category,
            "error": reason
        })
        file_warnings.extend(result.warnings[1:])
        return False, file_hash, telemetry

    if result.status == IntakeStatus.ERROR:
        telemetry.update({
            "how_processed": _derive_how_processed(ext, result.warnings),
            "category": "UNKNOWN",
            "error": result.warnings[0] if result.warnings else "Ingestion error"
        })
        return False, file_hash, telemetry

    # 3. Ingested / merged / partial success
    stages_succeeded.extend(["CAS_STORE", "TEXT_PARSING", "DOCUMENT_CLASSIFICATION", "PROFILE_EXTRACTION"])
    if result.resolution_action == ResolutionAction.MERGE:
        stages_succeeded.append("ENTITY_MERGE")
    else:
        stages_succeeded.append("CANDIDATE_CREATION")
    stages_succeeded.extend(["DATABASE_INSERTION", "FTS_INDEXING"])

    cand = db.query(Candidate).filter(Candidate.id == result.candidate_id).first() if result.candidate_id else None
    full_name = f"{cand.first_name} {cand.last_name}".strip() if cand else None

    file_warnings.extend(result.warnings)

    vector_ok = not any(w.startswith("Vector indexing skipped") for w in result.warnings)
    if vector_ok:
        stages_succeeded.append("VECTOR_INDEXING")

    if ext == ".doc":
        file_warnings.append("Legacy .doc format extracted via raw text fallback.")

    # Bulk keeps writing its own diary rows (D3: TimelineMode.NONE above)
    db.add(CandidateTimelineEvent(
        id=str(uuid.uuid4()),
        candidate_id=result.candidate_id,
        event_type="RESUME_INGESTED",
        title="Resume Ingested (Batch)",
        description=f"File {filepath.name} imported from folder '{folder_tag}'",
        created_by="System"
    ))

    telemetry.update({
        "candidate_id": result.candidate_id,
        "candidate_name": full_name,
        "ai_used": result.used_ai_fallback,
        "how_processed": _derive_how_processed(ext, result.warnings),
        "status": "PARTIAL_SUCCESS" if (file_warnings or not vector_ok) else "SUCCESS",
        "category": "VALID_RESUME"
    })
    return True, file_hash, telemetry

def run_bulk_ingest(
    source_dir: str,
    batch_size: int,
    output_dir: Optional[str] = "bulk-ingestions/reports",
    checkpoint_file: Optional[str] = None,
    report_file: Optional[str] = None,
    unprocessed_log: Optional[str] = None,
    summary_file: Optional[str] = None,
    exclude_dirs: Optional[List[str]] = None,
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

    cas_mgr = CASManager(get_settings().cas_root_dir)
    SessionLocal = _get_sessionmaker(get_settings().db_path)
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
    
    excluded_dirs_set = {d.strip().lower() for d in (exclude_dirs or [])} | DEFAULT_EXCLUDED_DIRS

    # Generator-based traversal
    for root, dirs, files in os.walk(base_dir):
        # Prune excluded subdirectories in-place so os.walk does not descend into them
        dirs[:] = [d for d in dirs if d.lower() not in excluded_dirs_set]

        # Guard: check if current root path is inside an excluded directory
        try:
            rel_root = Path(root).relative_to(base_dir)
            if any(part.lower() in excluded_dirs_set for part in rel_root.parts):
                continue
        except Exception:
            pass

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
    parser.add_argument("--output-dir", type=str, default="bulk-ingestions/reports", help="Directory where all generated reports, summaries, and checkpoints are stored")
    parser.add_argument("--checkpoint-file", type=str, default=None, help="Name or path to checkpoint JSON file (saved in output-dir by default)")
    parser.add_argument("--report-file", type=str, default=None, help="Name or path to master audit JSON report (saved in output-dir by default)")
    parser.add_argument("--unprocessed-log", type=str, default=None, help="Name or path to unprocessed non-resume log JSON file (saved in output-dir by default)")
    parser.add_argument("--summary-file", type=str, default=None, help="Name or path to generated Markdown summary report (saved in output-dir by default)")
    parser.add_argument("--exclude-dirs", nargs="*", default=["Candidate details"], help="Directory names to skip during ingestion traversal")
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
        exclude_dirs=args.exclude_dirs,
        dry_run=args.dry_run
    )
