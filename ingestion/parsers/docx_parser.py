"""DOCX parser using python-docx.

Public interface:
    parse_docx(path: Path) -> ParsedDocument
"""
from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table

from ingestion.parsers.models import ParsedDocument


def _extract_from_elements(elements, doc: DocxDocument) -> list[str]:
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    
    parts = []
    for el in elements:
        if el.tag.endswith('p'):
            p = Paragraph(el, doc)
            txt = p.text.strip()
            if txt:
                parts.append(txt)
        elif el.tag.endswith('tbl'):
            t = Table(el, doc)
            for row in t.rows:
                row_text = "\t".join(c.text.strip() for c in row.cells)
                if row_text.strip():
                    parts.append(row_text)
    return parts

def parse_docx(path: Path) -> ParsedDocument:
    """Extract text and metadata from a Word (.docx) file.

    Extraction order:
      1. Section Headers (where contact info often lives)
      2. Body elements (paragraphs and tables interleaved in document order)
      3. Section Footers

    Note: DOCX documents have no native rendered page count accessible without
    a Word rendering engine. ``pages`` is therefore set to 1 as a safe default.

    Args:
        path: Absolute or relative path to the .docx file.

    Returns:
        ParsedDocument with full extracted text, pages=1, and metadata.
    """
    path = Path(path)
    doc = DocxDocument(str(path))

    text_parts: list[str] = []

    # 1. Headers
    for section in doc.sections:
        if section.header is not None:
            text_parts.extend(_extract_from_elements(section.header._element, doc))
        # Note: we might also want to check first_page_header if it's different, but standard header._element 
        # usually contains what's actively set. Python-docx exposes different headers depending on section config.
        if section.different_first_page_header_footer and section.first_page_header is not None:
            text_parts.extend(_extract_from_elements(section.first_page_header._element, doc))

    # 2. Body (Paragraphs and Tables interleaved in correct order)
    text_parts.extend(_extract_from_elements(doc.element.body, doc))

    # 3. Footers
    for section in doc.sections:
        if section.footer is not None:
            text_parts.extend(_extract_from_elements(section.footer._element, doc))
        if section.different_first_page_header_footer and section.first_page_footer is not None:
            text_parts.extend(_extract_from_elements(section.first_page_footer._element, doc))

    # Deduplicate lines that appear multiple times sequentially (common with headers repeated per section)
    deduped_parts = []
    for part in text_parts:
        if not deduped_parts or deduped_parts[-1] != part:
            deduped_parts.append(part)

    return ParsedDocument(
        text="\n".join(deduped_parts),
        pages=1,
        metadata={"source_path": str(path)},
    )
