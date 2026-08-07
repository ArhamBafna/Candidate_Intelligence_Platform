"""Section-aware text chunker with context injection.

Public interface:
    chunk_document(
        doc: ParsedDocument,
        candidate_id: str,
        section_name: str,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> list[TextChunk]
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from ingestion.parsers.models import ParsedDocument


@dataclass
class TextChunk:
    """A single text chunk produced by the chunker.

    Attributes:
        chunk_id:      UUIDv4 uniquely identifying this chunk.
        text:          The chunk's content (≤ chunk_size characters).
        candidate_id:  Injected context: FK to the owning candidate.
        section_name:  Injected context: e.g. 'WORK_EXPERIENCE', 'EDUCATION'.
        start_offset:  Character offset (inclusive) in the source document text.
        end_offset:    Character offset (exclusive) in the source document text.
    """
    chunk_id: str
    text: str
    candidate_id: str
    section_name: str
    start_offset: int
    end_offset: int


def chunk_document(
    doc: ParsedDocument,
    candidate_id: str,
    section_name: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[TextChunk]:
    """Split a ParsedDocument's text into overlapping fixed-size chunks.

    Strategy:
      - Slides a window of ``chunk_size`` characters over the source text,
        advancing by ``(chunk_size - chunk_overlap)`` characters each step.
      - Empty documents return an empty list.
      - Documents shorter than ``chunk_size`` yield exactly one chunk.
      - Each chunk receives a freshly generated UUIDv4 and context fields
        (``candidate_id``, ``section_name``).

    Args:
        doc:          The ParsedDocument whose ``text`` is to be chunked.
        candidate_id: Candidate identifier injected into every chunk.
        section_name: Section label (e.g. 'WORK_EXPERIENCE') injected into every chunk.
        chunk_size:   Maximum number of characters per chunk (default 512).
        chunk_overlap: Number of characters of overlap between consecutive chunks (default 64).

    Returns:
        A list of TextChunk objects in document order.
    """
    text = doc.text
    if not text:
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks: list[TextChunk] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]
        chunks.append(
            TextChunk(
                chunk_id=str(uuid.uuid4()),
                text=chunk_text,
                candidate_id=candidate_id,
                section_name=section_name,
                start_offset=start,
                end_offset=end,
            )
        )
        if end == len(text):
            break
        start += step

    return chunks
