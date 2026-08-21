"""Tests for ingestion/parsers/email_parser.py

Seam under test: parse_email(path: Path) -> ParsedDocument
Expected behaviour:
  - Returns a ParsedDocument from a plain .eml file.
  - text contains the email body.
  - pages is 1.
  - metadata contains 'subject', 'from', 'to', and 'source_path'.
"""
import email
from pathlib import Path
import pytest

from ingestion.parsers.email_parser import parse_email
from ingestion.parsers.models import ParsedDocument


# ---------------------------------------------------------------------------
# Helpers — write a minimal RFC-2822 .eml file
# ---------------------------------------------------------------------------

def _make_eml(tmp_path: Path, subject: str = "Resume", body: str = "Dear Recruiter,\n\nPlease find my resume attached.") -> Path:
    """Write a minimal plain-text .eml file and return its path."""
    eml_path = tmp_path / "message.eml"
    # NOTE: RFC-2822 requires headers to start at column 0 (no leading whitespace).
    content = (
        f"From: candidate@example.com\r\n"
        f"To: recruiter@company.com\r\n"
        f"Subject: {subject}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}\r\n"
    )
    eml_path.write_bytes(content.encode("utf-8"))
    return eml_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_email_functional_flow(tmp_path: Path):
    """parse_email must return ParsedDocument, extract body text, pages, and metadata headers."""
    body = "Please find my resume attached. I have 7 years of Python experience."
    eml_path = _make_eml(tmp_path, subject="Application for SWE Role", body=body)

    result = parse_email(eml_path)

    assert isinstance(result, ParsedDocument)
    assert "resume attached" in result.text
    assert "Python experience" in result.text
    assert result.pages == 1
    assert "subject" in result.metadata
    assert "Application for SWE Role" in result.metadata["subject"]
    assert "from" in result.metadata
    assert "candidate@example.com" in result.metadata["from"]
    assert "to" in result.metadata
    assert "source_path" in result.metadata
    assert str(eml_path) in result.metadata["source_path"]
