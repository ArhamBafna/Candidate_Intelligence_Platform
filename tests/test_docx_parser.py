"""Tests for ingestion/parsers/docx_parser.py

Seam under test: parse_docx(path: Path) -> ParsedDocument
Expected behaviour:
  - Returns a ParsedDocument with text extracted from paragraphs.
  - pages is 1 (DOCX has no native page count; we default to 1).
  - metadata contains 'source_path'.
  - Tables are included in extracted text.
"""
from pathlib import Path
import pytest

from ingestion.parsers.docx_parser import parse_docx
from ingestion.parsers.models import ParsedDocument


# ---------------------------------------------------------------------------
# Helpers — create a minimal .docx in-memory using python-docx
# ---------------------------------------------------------------------------

def _make_docx(tmp_path: Path, paragraphs: list[str], table_data: list[list[str]] | None = None) -> Path:
    """Write a .docx file with the given paragraphs (and optional table)."""
    from docx import Document

    doc = Document()
    for para in paragraphs:
        doc.add_paragraph(para)

    if table_data:
        rows = len(table_data)
        cols = len(table_data[0]) if rows else 0
        table = doc.add_table(rows=rows, cols=cols)
        for r_idx, row_cells in enumerate(table_data):
            for c_idx, cell_text in enumerate(row_cells):
                table.rows[r_idx].cells[c_idx].text = cell_text

    docx_path = tmp_path / "resume.docx"
    doc.save(str(docx_path))
    return docx_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_docx_returns_parsed_document(tmp_path: Path):
    """parse_docx must return a ParsedDocument instance."""
    docx_path = _make_docx(tmp_path, ["Alice Johnson", "Product Manager"])

    result = parse_docx(docx_path)

    assert isinstance(result, ParsedDocument)


def test_parse_docx_extracts_paragraph_text(tmp_path: Path):
    """parse_docx must include paragraph text in the result."""
    docx_path = _make_docx(tmp_path, ["Alice Johnson", "Product Manager at Acme Corp"])

    result = parse_docx(docx_path)

    assert "Alice Johnson" in result.text
    assert "Product Manager" in result.text


def test_parse_docx_default_page_count(tmp_path: Path):
    """parse_docx must set pages to 1 (DOCX has no native page count)."""
    docx_path = _make_docx(tmp_path, ["Text"])

    result = parse_docx(docx_path)

    assert result.pages == 1


def test_parse_docx_metadata_contains_source_path(tmp_path: Path):
    """parse_docx must include source_path in metadata."""
    docx_path = _make_docx(tmp_path, ["Text"])

    result = parse_docx(docx_path)

    assert "source_path" in result.metadata
    assert str(docx_path) in result.metadata["source_path"]


def test_parse_docx_extracts_table_text(tmp_path: Path):
    """parse_docx must include text from tables in the result."""
    docx_path = _make_docx(
        tmp_path,
        paragraphs=["Skills"],
        table_data=[["Python", "5 years"], ["SQL", "3 years"]],
    )

    result = parse_docx(docx_path)

    assert "Python" in result.text
    assert "SQL" in result.text
