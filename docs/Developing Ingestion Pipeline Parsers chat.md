# Ingestion Pipeline Parsers Development Summary

> **Purpose**: Concise context summary for AI agents working on this workspace.

## Summary of Accomplishments (Stage 2 - Parsers & Chunker)

Followed TDD (`pytest`) to build and test the ingestion parsers and document chunker:

1. **`ingestion/parsers/models.py`**
   - Defined `ParsedDocument` Dataclass / Pydantic model (`text`, `pages`, `metadata`, `attachments`, `layout_json`).

2. **`ingestion/parsers/pdf_parser.py`**
   - Multi-stage PDF extraction: `PyMuPDF` (fitz) text/page extraction, `pdfplumber` layout analysis, with optional Tesseract OCR fallback for scanned PDFs.
   - Verified with unit tests in `tests/test_pdf_parser.py`.

3. **`ingestion/parsers/docx_parser.py`**
   - Word document parser using `python-docx` to extract text from paragraphs, tables, and header structures.
   - Verified with unit tests in `tests/test_docx_parser.py`.

4. **`ingestion/parsers/email_parser.py`**
   - Email parsing for `.eml` and `.msg` formats using Python's `email` module and `extract-msg`.
   - Extracts subject, sender/recipient metadata, body text, and attachments.
   - Verified with unit tests in `tests/test_email_parser.py`.
   - *Key fix*: Windows `.eml` test fixtures must write binary bytes directly (`write_bytes(content.encode('utf-8'))`) to prevent `\r\n` -> `\r\r\n` translation corruption.

5. **`ingestion/chunker.py`**
   - Hierarchical section-aware text chunker with candidate ID and section header context injection.
   - Verified with unit tests in `tests/test_chunker.py`.

## Hand-off Status / Next Action

- **Completed**: Ingestion Parsers (`pdf`, `docx`, `email`) & `chunker.py`.
- **In Progress / Next Task**: Implement `ingestion/entity_resolution.py` (Tier 1 deterministic exact key match + Tier 2 probabilistic name similarity match).
- **Test File Ready**: `tests/test_entity_resolution.py` has already been written. Implement `ingestion/entity_resolution.py` using `jellyfish` (Jaro-Winkler) to pass the test suite.