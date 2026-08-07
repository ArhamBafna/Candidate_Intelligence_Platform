"""DOCX parser using python-docx.

Public interface:
    parse_docx(path: Path) -> ParsedDocument
"""
from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table

from ingestion.parsers.models import ParsedDocument


def parse_docx(path: Path) -> ParsedDocument:
    """Extract text and metadata from a Word (.docx) file.

    Extraction order:
      1. All paragraphs in document body order.
      2. All table cells (row-by-row, cell-by-cell), separated by tabs/newlines.

    Note: DOCX documents have no native rendered page count accessible without
    a Word rendering engine. ``pages`` is therefore set to 1 as a safe default.
    A future iteration can integrate ``python-docx2txt`` or COM automation for
    approximate page counts.

    Args:
        path: Absolute or relative path to the .docx file.

    Returns:
        ParsedDocument with full extracted text, pages=1, and metadata.
    """
    path = Path(path)
    doc = DocxDocument(str(path))

    text_parts: list[str] = []

    # 1. Paragraphs
    for para in doc.paragraphs:
        stripped = para.text.strip()
        if stripped:
            text_parts.append(stripped)

    # 2. Tables — iterate all tables in the document body
    for table in doc.tables:
        for row in table.rows:
            row_text = "\t".join(cell.text.strip() for cell in row.cells)
            if row_text.strip():
                text_parts.append(row_text)

    return ParsedDocument(
        text="\n".join(text_parts),
        pages=1,
        metadata={"source_path": str(path)},
    )
