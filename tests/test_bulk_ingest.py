import importlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import bulk_ingest module from bulk-ingestions folder
_bulk_ingest_path = Path(__file__).resolve().parent.parent / "bulk-ingestions" / "bulk_ingest.py"
_spec = importlib.util.spec_from_file_location("bulk_ingest", str(_bulk_ingest_path))
bulk_ingest_module = importlib.util.module_from_spec(_spec)
sys.modules["bulk_ingest"] = bulk_ingest_module
_spec.loader.exec_module(bulk_ingest_module)

run_bulk_ingest = bulk_ingest_module.run_bulk_ingest
get_file_hash = bulk_ingest_module.get_file_hash
process_single_file = bulk_ingest_module.process_single_file
generate_markdown_summary = bulk_ingest_module.generate_markdown_summary

from candidate_intelligence_platform.ingestion.intake import classify_document

def test_get_file_hash(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    
    hash1 = get_file_hash(test_file)
    assert hash1 is not None
    assert len(hash1) == 64

def test_classify_document():
    # 1. Scanned / empty text
    is_res, cat, _ = classify_document("short", "sample.pdf")
    assert not is_res
    assert cat == "SCANNED_IMAGE_REQUIRES_OCR"

    # 2. Legal agreement
    contract_text = "This Referral Agreement is entered into by and between the parties hereto. Governing law and indemnification terms apply."
    is_res, cat, _ = classify_document(contract_text, "REFERRAL AGREEMENT.pdf")
    assert not is_res
    assert cat == "NON_RESUME_LEGAL_CONTRACT"

    # 3. Immigration / ID document
    visa_text = "Department of Homeland Security U.S. Citizenship and Immigration Services Form I-797 Notice of Action"
    is_res, cat, _ = classify_document(visa_text, "H1 Approval.pdf")
    assert not is_res
    assert cat == "NON_RESUME_IMMIGRATION_OR_ID"

    # 4. Valid Resume
    resume_text = """
    John Doe
    Senior Python Developer
    john.doe@example.com | 555-123-4567
    
    Summary:
    Experienced Python software engineer with 8 years of experience building APIs and data pipelines.
    
    Technical Skills:
    Python, FastAPI, Docker, PostgreSQL, AWS
    
    Professional Experience:
    Senior Developer at Acme Corp (2020 - Present)
    - Developed microservices
    
    Education:
    BS in Computer Science
    """
    is_res, cat, _ = classify_document(resume_text, "John_Doe_Resume.docx")
    assert is_res
    assert cat == "VALID_RESUME"

@patch("bulk_ingest.CASManager")
@patch("bulk_ingest._get_sessionmaker")
def test_bulk_ingest_dry_run(mock_sessionmaker, mock_cas_mgr, tmp_path):
    source_dir = tmp_path / "Resumes"
    source_dir.mkdir()
    
    java_dir = source_dir / "Java Developer"
    java_dir.mkdir()
    
    (java_dir / "resume1.docx").write_text("fake docx")
    (java_dir / "desktop.ini").write_text("ignore me")
    (java_dir / "~$lock.docx").write_text("lock file")
    
    checkpoint_file = tmp_path / "checkpoint.json"
    report_file = tmp_path / "report.json"
    unprocessed_log = tmp_path / "unprocessed.json"
    
    run_bulk_ingest(
        source_dir=str(source_dir),
        batch_size=500,
        checkpoint_file=str(checkpoint_file),
        report_file=str(report_file),
        unprocessed_log=str(unprocessed_log),
        dry_run=True
    )
    
    assert not checkpoint_file.exists()
    assert not report_file.exists()
    assert not unprocessed_log.exists()

@patch("bulk_ingest.process_single_file")
@patch("bulk_ingest.CASManager")
@patch("bulk_ingest._get_sessionmaker")
def test_bulk_ingest_master_report_logging(mock_sessionmaker, mock_cas_mgr, mock_process, tmp_path):
    source_dir = tmp_path / "Resumes"
    source_dir.mkdir()
    
    (source_dir / "valid_resume.docx").write_text("valid content")
    (source_dir / "contract.pdf").write_text("referral agreement terms")
    
    # 1st file: success
    # 2nd file: non-resume
    mock_process.side_effect = [
        (True, "hash1", {
            "file_path": "valid_resume.docx",
            "file_name": "valid_resume.docx",
            "file_type": ".docx",
            "candidate_name": "Jane Smith",
            "candidate_id": "uuid-123",
            "status": "SUCCESS",
            "how_processed": "Docx_Parser",
            "ai_used": False,
            "confidence_score": 0.95,
            "stages_succeeded": ["CAS_STORE", "TEXT_PARSING", "PROFILE_EXTRACTION", "DATABASE_INSERTION", "FTS_INDEXING", "VECTOR_INDEXING"],
            "stages_failed": [],
            "warnings": [],
            "category": "VALID_RESUME",
            "error": None,
            "timestamp": "2026-08-21T14:00:00"
        }),
        (False, "hash2", {
            "file_path": "contract.pdf",
            "file_name": "contract.pdf",
            "file_type": ".pdf",
            "candidate_name": None,
            "candidate_id": None,
            "status": "SKIPPED_NON_RESUME",
            "how_processed": "PyMuPDF_Parser",
            "ai_used": False,
            "confidence_score": 0.0,
            "stages_succeeded": ["CAS_STORE", "TEXT_PARSING"],
            "stages_failed": ["DOCUMENT_CLASSIFICATION"],
            "warnings": [],
            "category": "NON_RESUME_LEGAL_CONTRACT",
            "error": "Document identified as legal contract",
            "timestamp": "2026-08-21T14:00:01"
        })
    ]
    
    checkpoint_file = tmp_path / "checkpoint.json"
    report_file = tmp_path / "report.json"
    unprocessed_log = tmp_path / "unprocessed.json"
    summary_file = tmp_path / "summary.md"
    
    run_bulk_ingest(
        source_dir=str(source_dir),
        batch_size=10,
        checkpoint_file=str(checkpoint_file),
        report_file=str(report_file),
        unprocessed_log=str(unprocessed_log),
        summary_file=str(summary_file),
        dry_run=False
    )
    
    # Master report must contain BOTH records
    assert report_file.exists()
    reports = json.loads(report_file.read_text())
    assert len(reports) == 2
    assert reports[0]["candidate_name"] == "Jane Smith"
    assert reports[0]["status"] == "SUCCESS"
    assert reports[0]["how_processed"] == "Docx_Parser"
    assert "VECTOR_INDEXING" in reports[0]["stages_succeeded"]
    
    assert reports[1]["status"] == "SKIPPED_NON_RESUME"
    assert reports[1]["category"] == "NON_RESUME_LEGAL_CONTRACT"
    assert "DOCUMENT_CLASSIFICATION" in reports[1]["stages_failed"]
    
    # Unprocessed log must contain only the non-resume
    assert unprocessed_log.exists()
    unprocessed = json.loads(unprocessed_log.read_text())
    assert len(unprocessed) == 1
    assert unprocessed[0]["category"] == "NON_RESUME_LEGAL_CONTRACT"

def test_process_single_file_delegates_to_intake(db_session, tmp_path, monkeypatch):
    """Adapter maps IntakeResult to legacy telemetry strings; adds resolution_action."""
    bi = bulk_ingest_module
    from storage.cas import CASManager

    monkeypatch.setattr(bi, "get_vector_db", lambda: None)
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.deterministic_ner.extract_facts",
        lambda text: [],
    )
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: {
            "first_name": "Jane", "last_name": "Doe", "primary_email": "jane.doe@example.com",
            "primary_phone": "555-123-4567", "current_title": "Engineer",
            "warnings": [], "used_ai_fallback": False,
        },
    )

    resume_text = (
        "Jane Candidate\nSenior Python Developer\njane.doe@example.com | 555-123-4567\n\n"
        "Summary:\nExperienced Python software engineer building APIs and data pipelines.\n\n"
        "Technical Skills:\nPython, FastAPI, Docker, PostgreSQL, AWS\n\n"
        "Professional Experience:\nSenior Developer at Acme Corp (2020 - Present)\n\n"
        "Education:\nBS in Computer Science\n"
    ).encode("utf-8")
    f = tmp_path / "resumes"
    f.mkdir()
    target = f / "jane_resume.txt"
    target.write_bytes(resume_text)

    cas_mgr = CASManager(str(tmp_path / "cas"))
    success, file_hash, telemetry = bi.process_single_file(target, f, db_session, cas_mgr)
    db_session.commit()

    assert success is True
    assert telemetry["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert telemetry["category"] == "VALID_RESUME"
    assert telemetry["how_processed"] == "Raw_Text_Fallback"
    assert telemetry["candidate_name"] == "Jane Doe"
    assert "resolution_action" in telemetry
    assert telemetry["resolution_action"] == "NEW"

    # Same file again -> duplicate via pipeline dedup-before-CAS (D5)
    success2, _, telemetry2 = bi.process_single_file(target, f, db_session, cas_mgr)
    assert success2 is True
    assert telemetry2["status"] == "SKIPPED_DUPLICATE"
    assert telemetry2["category"] == "DUPLICATE_FILE"
    assert telemetry2["candidate_id"] == telemetry["candidate_id"]

    # Non-resume -> legacy category preserved, nothing persisted beyond CAS blob
    contract = f / "REFERRAL AGREEMENT.pdf"
    contract.write_text("This Referral Agreement is entered into by and between the parties hereto. Governing law and indemnification terms apply.")
    success3, _, telemetry3 = bi.process_single_file(contract, f, db_session, cas_mgr)
    assert success3 is False
    assert telemetry3["status"] == "SKIPPED_NON_RESUME"
    assert telemetry3["category"] == "NON_RESUME_LEGAL_CONTRACT"


def test_generate_markdown_summary_candidate_breakdown(tmp_path):
    records = [
        {
            "status": "SUCCESS",
            "resolution_action": "NEW",
            "candidate_id": "cand-1",
            "candidate_name": "Alice Smith",
            "how_processed": "PyMuPDF_Parser",
            "ai_used": False,
            "folder_tag": "Engineering",
            "file_name": "alice.pdf",
        },
        {
            "status": "SUCCESS",
            "resolution_action": "MERGE",
            "candidate_id": "cand-1",
            "candidate_name": "Alice Smith",
            "how_processed": "PyMuPDF_Parser",
            "ai_used": False,
            "folder_tag": "Engineering",
            "file_name": "alice_v2.pdf",
        },
        {
            "status": "PARTIAL_SUCCESS",
            "resolution_action": "NEW",
            "candidate_id": "cand-2",
            "candidate_name": "Bob Jones",
            "how_processed": "Docx_Parser",
            "ai_used": True,
            "folder_tag": "Marketing",
            "file_name": "bob.docx",
        },
        {
            "status": "SKIPPED_NON_RESUME",
            "category": "NON_RESUME_IMMIGRATION_OR_ID",
            "file_name": "passport.pdf",
        },
        {
            "status": "SKIPPED_DUPLICATE",
            "file_name": "duplicate.docx",
        },
    ]

    out_file = tmp_path / "summary.md"
    generate_markdown_summary(records, out_file)

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    assert "- **Total Files Evaluated:** 5" in content
    assert "- **Ingested Resumes (Files Processed):** 3" in content
    assert "  - **New Candidates Created:** 2" in content
    assert "  - **Resumes Merged into Existing:** 1" in content
    assert "  - **Unique Candidate Cards in UI:** 2" in content
    assert "| `Merge` |" in content
    assert "| `New` |" in content

