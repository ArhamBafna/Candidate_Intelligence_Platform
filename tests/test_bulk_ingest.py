import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.bulk_ingest import (
    run_bulk_ingest,
    get_file_hash,
    process_single_file,
    classify_document
)

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

@patch("scripts.bulk_ingest.CASManager")
@patch("scripts.bulk_ingest.SessionLocal")
def test_bulk_ingest_dry_run(mock_session_local, mock_cas_mgr, tmp_path):
    source_dir = tmp_path / "Resumes"
    source_dir.mkdir()
    
    java_dir = source_dir / "Java Developer"
    java_dir.mkdir()
    
    (java_dir / "resume1.docx").write_text("fake docx")
    (java_dir / "desktop.ini").write_text("ignore me")
    (java_dir / "~$lock.docx").write_text("lock file")
    
    checkpoint_file = tmp_path / "checkpoint.json"
    unprocessed_log = tmp_path / "unprocessed.json"
    
    run_bulk_ingest(
        source_dir=str(source_dir),
        batch_size=500,
        checkpoint_file=str(checkpoint_file),
        unprocessed_log=str(unprocessed_log),
        dry_run=True
    )
    
    assert not checkpoint_file.exists()
    assert not unprocessed_log.exists()

@patch("scripts.bulk_ingest.process_single_file")
@patch("scripts.bulk_ingest.CASManager")
@patch("scripts.bulk_ingest.SessionLocal")
def test_bulk_ingest_unprocessed_logging(mock_session_local, mock_cas_mgr, mock_process, tmp_path):
    source_dir = tmp_path / "Resumes"
    source_dir.mkdir()
    
    (source_dir / "contract.pdf").write_text("referral agreement terms")
    
    mock_process.return_value = (False, "fakehash", {
        "category": "NON_RESUME_LEGAL_CONTRACT",
        "error": "Document identified as legal contract",
        "trace": ""
    })
    
    checkpoint_file = tmp_path / "checkpoint.json"
    unprocessed_log = tmp_path / "unprocessed.json"
    
    run_bulk_ingest(
        source_dir=str(source_dir),
        batch_size=10,
        checkpoint_file=str(checkpoint_file),
        unprocessed_log=str(unprocessed_log),
        dry_run=False
    )
    
    assert unprocessed_log.exists()
    records = json.loads(unprocessed_log.read_text())
    assert len(records) == 1
    assert records[0]["category"] == "NON_RESUME_LEGAL_CONTRACT"
    assert records[0]["path"] == "contract.pdf"
    
    # Verify it is recorded in checkpoint
    state = json.loads(checkpoint_file.read_text())
    assert "contract.pdf" in state["processed_paths"]
