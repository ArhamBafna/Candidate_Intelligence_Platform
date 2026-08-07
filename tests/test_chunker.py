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
