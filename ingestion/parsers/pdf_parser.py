"""PDF parser using PyMuPDF (primary) + pdfplumber (fallback for complex layouts).

Public interface:
    parse_pdf(path: Path) -> ParsedDocument
"""
from pathlib import Path

import fitz  # PyMuPDF

from ingestion.parsers.models import ParsedDocument


def parse_pdf(path: Path) -> ParsedDocument:
    """Extract text and metadata from a PDF file.

    Strategy:
      1. Open with PyMuPDF (fitz) — fast, accurate for digital PDFs.
      2. Collect page text via ``page.get_text("text")``.
      3. If a page yields no text (scanned/image-only), fall back to pdfplumber
         for that page's layout-aware extraction.
      4. If pdfplumber also returns nothing, a Tesseract OCR hook can be inserted
         here in a future iteration (guarded by ``pytesseract`` availability).

    Args:
        path: Absolute or relative path to the PDF file.

    Returns:
        ParsedDocument with full extracted text, page count, and metadata.
    """
    path = Path(path)
    full_text_parts: list[str] = []

    with fitz.open(str(path)) as doc:
        page_count = len(doc)
        for page in doc:
            page_text = page.get_text("text").strip()
            if page_text:
                full_text_parts.append(page_text)
            else:
                # Fallback: pdfplumber for layout-difficult pages
                page_text = _extract_with_pdfplumber(path, page.number)
                if page_text:
                    full_text_parts.append(page_text)
                # TODO: Tesseract OCR fallback when pytesseract is available

    return ParsedDocument(
        text="\n".join(full_text_parts),
        pages=page_count,
        metadata={"source_path": str(path)},
    )


def _extract_with_pdfplumber(path: Path, page_index: int) -> str:
    """Extract text from a single page using pdfplumber.

    Used as a fallback when PyMuPDF returns no text (e.g., complex column layouts).
    """
    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        if page_index < len(pdf.pages):
            extracted = pdf.pages[page_index].extract_text()
            return (extracted or "").strip()
    return ""
