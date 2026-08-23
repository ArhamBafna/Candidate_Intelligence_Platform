"""Tests for ingestion/chunker.py

Seam under test:
    chunk_document(
        doc: ParsedDocument,
        candidate_id: str,
        section_name: str,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> list[TextChunk]

Expected behaviours:
  - Returns a list of TextChunk instances.
  - Each chunk has a non-empty unique chunk_id (UUIDv4).
  - Each chunk's text is ≤ chunk_size characters.
  - Consecutive chunks overlap by ≈ chunk_overlap characters (within tolerance).
  - Each chunk carries the candidate_id and section_name injected as context.
  - start_offset and end_offset span the right slice of the source text.
  - A short document (< chunk_size) yields exactly one chunk.
  - An empty document yields an empty list.
"""
import uuid
from pathlib import Path
import pytest

from ingestion.chunker import chunk_document, TextChunk
from ingestion.parsers.models import ParsedDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(text: str) -> ParsedDocument:
    return ParsedDocument(text=text, pages=1, metadata={"source_path": "test.pdf"})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_chunk_document_returns_list_of_text_chunks():
    """chunk_document must return a list of TextChunk instances."""
    doc = _make_doc("A" * 600)
    result = chunk_document(doc, candidate_id="cand-1", section_name="WORK_EXPERIENCE")
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(c, TextChunk) for c in result)


def test_chunk_ids_are_unique_uuids():
    """Every TextChunk must have a unique, valid UUIDv4 chunk_id."""
    doc = _make_doc("B" * 1200)
    result = chunk_document(doc, candidate_id="cand-1", section_name="SKILLS")
    ids = [c.chunk_id for c in result]
    # All IDs must be valid UUID strings
    for chunk_id in ids:
        uuid.UUID(chunk_id, version=4)
    # IDs must be unique
    assert len(ids) == len(set(ids))


def test_chunk_size_not_exceeded():
    """No chunk's text may exceed chunk_size characters."""
    chunk_size = 200
    doc = _make_doc("C " * 500)  # 1000 chars
    result = chunk_document(doc, candidate_id="cand-1", section_name="EDUCATION", chunk_size=chunk_size)
    for chunk in result:
        assert len(chunk.text) <= chunk_size, f"Chunk too long: {len(chunk.text)}"


def test_chunk_carries_context_fields():
    """Each chunk must carry candidate_id and section_name."""
    doc = _make_doc("D" * 600)
    cid = "candidate-abc-123"
    section = "SUMMARY"
    result = chunk_document(doc, candidate_id=cid, section_name=section)
    for chunk in result:
        assert chunk.candidate_id == cid
        assert chunk.section_name == section


def test_chunk_offsets_span_source_text():
    """start_offset and end_offset must correctly index into the source text."""
    source = "Hello World " * 100  # 1200 chars
    doc = _make_doc(source)
    result = chunk_document(doc, candidate_id="cand-1", section_name="WORK_EXPERIENCE", chunk_size=200, chunk_overlap=20)
    for chunk in result:
        assert chunk.start_offset >= 0
        assert chunk.end_offset <= len(source)
        assert chunk.start_offset < chunk.end_offset
        # The text must be a substring of (or derived from) the source
        assert source[chunk.start_offset:chunk.end_offset].strip()


def test_short_document_yields_single_chunk():
    """A document shorter than chunk_size must yield exactly one chunk."""
    doc = _make_doc("Short resume text.")
    result = chunk_document(doc, candidate_id="cand-1", section_name="SUMMARY", chunk_size=512)
    assert len(result) == 1


def test_empty_document_yields_empty_list():
    """An empty document must yield an empty list (no ghost chunks)."""
    doc = _make_doc("")
    result = chunk_document(doc, candidate_id="cand-1", section_name="SUMMARY")
    assert result == []


# ---------------------------------------------------------------------------
# Section-aware splitting (chunk_resume)
# ---------------------------------------------------------------------------

from ingestion.chunker import chunk_resume, split_resume_sections

RESUME_TEXT = """Arham Bafna
Backend engineer based in NYC.

SUMMARY
Five years building data platforms and search systems.

SKILLS
Python, SQL, FastAPI, LanceDB, Docker.

WORK_EXPERIENCE
Senior Engineer at Acme (2021-2024). Built hybrid search pipelines.
Engineer at Globex (2018-2021). Shipped ETL tooling.

EDUCATION
B.Tech in Computer Science, State University.
"""


def test_split_resume_sections_detects_true_types():
    sections = split_resume_sections(RESUME_TEXT)
    names = [name for name, _ in sections]
    assert names == ["SUMMARY", "SKILLS", "WORK_EXPERIENCE", "EDUCATION"]
    by_name = dict(sections)
    assert "data platforms" in by_name["SUMMARY"]
    assert "FastAPI" in by_name["SKILLS"]
    assert "Acme" in by_name["WORK_EXPERIENCE"]
    assert "State University" in by_name["EDUCATION"]


def test_split_resume_sections_preamble_becomes_summary():
    text = "Jane Doe\nContact line.\nSKILLS\nPython"
    sections = split_resume_sections(text)
    assert sections[0][0] == "SUMMARY"
    assert "Jane Doe" in sections[0][1]


def test_split_resume_sections_no_headers_single_summary():
    text = "Plain resume with no headers at all.\nJust prose."
    sections = split_resume_sections(text)
    assert len(sections) == 1
    assert sections[0][0] == "SUMMARY"


def test_split_resume_sections_case_insensitive_and_colon():
    text = "TECHNICAL SKILLS:\nPython\nEducation\nSome school"
    sections = split_resume_sections(text)
    names = [name for name, _ in sections]
    assert names == ["SKILLS", "EDUCATION"]


def test_chunk_resume_labels_chunks_with_section_types():
    doc = _make_doc(RESUME_TEXT)
    chunks = chunk_resume(doc, candidate_id="cand-1")

    assert len(chunks) > 0
    labeled = {c.section_name for c in chunks}
    assert {"SUMMARY", "SKILLS", "WORK_EXPERIENCE", "EDUCATION"} <= labeled
    # Skills content never lands under a different section label.
    for chunk in chunks:
        if "FastAPI" in chunk.text:
            assert chunk.section_name == "SKILLS"


def test_chunk_resume_respects_chunk_size_per_section():
    doc = _make_doc("SKILLS\n" + ("python rust go " * 200))
    chunks = chunk_resume(doc, candidate_id="cand-1", chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 100
        assert chunk.section_name == "SKILLS"


def test_chunk_resume_offsets_index_source_text():
    doc = _make_doc(RESUME_TEXT)
    source = doc.text
    chunks = chunk_resume(doc, candidate_id="cand-1")

    for chunk in chunks:
        assert 0 <= chunk.start_offset < chunk.end_offset <= len(source)
        assert source[chunk.start_offset:chunk.end_offset].strip()


def test_chunk_resume_whole_doc_as_one_summary_is_gone():
    doc = _make_doc(RESUME_TEXT)
    chunks = chunk_resume(doc, candidate_id="cand-1")
    assert len({c.section_name for c in chunks}) > 1


def test_chunk_resume_empty_document_yields_empty_list():
    doc = _make_doc("")
    assert chunk_resume(doc, candidate_id="cand-1") == []
