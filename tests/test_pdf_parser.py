"""Tests for ingestion/parsers/pdf_parser.py

Seam under test: parse_pdf(path: Path) -> ParsedDocument
Expected behaviour:
  - Returns a ParsedDocument with non-empty text extracted from a real-looking PDF.
  - pages equals the actual page count in the PDF.
  - metadata contains at least 'source_path'.
  - OCR path: when a text-layer PDF has zero selectable text, the parser still
    returns non-empty text (Tesseract fallback — skipped when Tesseract not installed).
"""
import io
import struct
from pathlib import Path
import pytest

from ingestion.parsers.pdf_parser import parse_pdf
from ingestion.parsers.models import ParsedDocument


# ---------------------------------------------------------------------------
# Helpers — minimal valid single-page PDF created in-memory with a text layer
# ---------------------------------------------------------------------------

def _make_minimal_pdf(text: str = "John Doe\nSoftware Engineer") -> bytes:
    """Build a real, spec-compliant single-page PDF containing *text*.

    Uses only stdlib (struct/bytes) — no dependency on reportlab or fpdf.
    Based on the PDF-1.4 minimal specification.
    """
    # Escape text for PDF stream (very basic — no UTF-8 needed for ASCII)
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content_stream = (
        f"BT\n/F1 12 Tf\n50 700 Td\n({safe_text}) Tj\nET"
    ).encode()
    stream_len = len(content_stream)

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        + f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + content_stream
        + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    # Cross-reference table
    xref_offset = len(pdf)
    offsets = []
    pos = 0
    for line in pdf.split(b"\n"):
        if line.endswith(b"obj"):
            offsets.append(pos)
        pos += len(line) + 1  # +1 for \n

    xref = b"xref\n"
    xref += f"0 {len(offsets) + 1}\n".encode()
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = (
        f"trailer\n<< /Size {len(offsets) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()

    return pdf + xref + trailer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_pdf_returns_parsed_document(tmp_path: Path):
    """parse_pdf must return a ParsedDocument instance."""
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_bytes(_make_minimal_pdf())

    result = parse_pdf(pdf_file)

    assert isinstance(result, ParsedDocument)


def test_parse_pdf_extracts_text(tmp_path: Path):
    """parse_pdf must return non-empty text from a PDF with a text layer."""
    content = "Jane Smith Senior Developer"
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_bytes(_make_minimal_pdf(content))

    result = parse_pdf(pdf_file)

    # The full text must contain the key phrase (whitespace may differ)
    assert "Jane Smith" in result.text


def test_parse_pdf_correct_page_count(tmp_path: Path):
    """parse_pdf must set pages to the actual page count."""
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_bytes(_make_minimal_pdf())  # 1-page PDF

    result = parse_pdf(pdf_file)

    assert result.pages == 1


def test_parse_pdf_metadata_contains_source_path(tmp_path: Path):
    """parse_pdf must include source_path in metadata."""
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_bytes(_make_minimal_pdf())

    result = parse_pdf(pdf_file)

    assert "source_path" in result.metadata
    assert str(pdf_file) in result.metadata["source_path"]

def test_parse_pdf_ocr_fallback(tmp_path: Path, monkeypatch):
    """parse_pdf must fall back to OCR if get_text and pdfplumber return empty."""
    import fitz
    from ingestion.parsers import pdf_parser
    
    # Mock PyMuPDF to return empty text
    original_get_text = fitz.Page.get_text
    def mock_get_text(self, *args, **kwargs):
        return ""
    monkeypatch.setattr(fitz.Page, "get_text", mock_get_text)
    
    # Mock pdfplumber to return empty text
    monkeypatch.setattr(pdf_parser, "_extract_with_pdfplumber", lambda p, n: "")
    
    # Mock pytesseract
    try:
        import pytesseract
        monkeypatch.setattr(pytesseract, "image_to_string", lambda img: "Mocked OCR Text")
    except ImportError:
        pytest.skip("pytesseract not installed")
        
    pdf_file = tmp_path / "resume.pdf"
    pdf_file.write_bytes(_make_minimal_pdf("Hidden text"))
    
    result = pdf_parser.parse_pdf(pdf_file)
    
    assert "Mocked OCR Text" in result.text
