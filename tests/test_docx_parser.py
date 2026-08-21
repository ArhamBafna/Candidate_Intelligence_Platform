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

def test_parse_docx_functional_flow(tmp_path: Path):
    """parse_docx must return ParsedDocument, extract text, tables, have correct pages, and metadata."""
    docx_path = _make_docx(
        tmp_path,
        paragraphs=["Alice Johnson", "Product Manager at Acme Corp", "Skills"],
        table_data=[["Python", "5 years"], ["SQL", "3 years"]],
    )

    result = parse_docx(docx_path)

    assert isinstance(result, ParsedDocument)
    assert "Alice Johnson" in result.text
    assert "Product Manager" in result.text
    assert "Python" in result.text
    assert "SQL" in result.text
    assert result.pages == 1
    assert "source_path" in result.metadata
    assert str(docx_path) in result.metadata["source_path"]
