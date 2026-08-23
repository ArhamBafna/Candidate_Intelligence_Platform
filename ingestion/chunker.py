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
from typing import List, Tuple

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


# Recognized resume section headers. Order matters only for readability;
# matching is exact against these aliases (case-insensitive, optional ':').
_SECTION_ALIASES: List[Tuple[str, Tuple[str, ...]]] = [
    ("SUMMARY", ("summary", "professional summary", "profile", "about me", "about", "objective")),
    ("SKILLS", ("skills", "technical skills", "core skills", "key skills", "competencies")),
    (
        "WORK_EXPERIENCE",
        (
            "experience",
            "work experience",
            "work_experience",
            "professional experience",
            "professional_experience",
            "employment",
            "employment history",
            "employment_history",
            "career history",
            "career_history",
        ),
    ),
    ("EDUCATION", ("education", "academic background", "academic_background", "academics", "qualifications")),
]

_MAX_HEADER_LENGTH = 60


def _match_section_header(line: str) -> str | None:
    """Return the canonical section name if the line is a section header."""
    stripped = line.strip().rstrip(":").strip()
    if not stripped or len(stripped) > _MAX_HEADER_LENGTH:
        return None
    lowered = stripped.lower()
    for canonical, aliases in _SECTION_ALIASES:
        if lowered in aliases:
            return canonical
    return None


def split_resume_sections(text: str) -> List[Tuple[str, str]]:
    """Split raw resume text into (section_name, section_text) pairs.

    Lines that exactly match a known section header start a new section; all
    following lines belong to it until the next header. Text before the first
    recognized header becomes SUMMARY. Returns sections in document order.
    """
    if not text:
        return []

    lines = text.splitlines(keepends=True)
    sections: List[Tuple[str, str]] = []
    current_name: str | None = "SUMMARY"
    current_parts: List[str] = []

    for line in lines:
        header = _match_section_header(line)
        if header is not None:
            pending = "".join(current_parts)
            if pending.strip():
                sections.append((current_name, pending))
            current_name = header
            current_parts = []
        else:
            current_parts.append(line)

    pending = "".join(current_parts)
    if pending.strip():
        sections.append((current_name, pending))

    # Merge adjacent sections that share a label (e.g. preamble + SUMMARY).
    merged: List[Tuple[str, str]] = []
    for name, section_text in sections:
        if merged and merged[-1][0] == name:
            merged[-1] = (name, merged[-1][1] + "\n" + section_text)
        else:
            merged.append((name, section_text))

    return merged


def chunk_resume(
    doc: ParsedDocument,
    candidate_id: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[TextChunk]:
    """Split a resume into section-aware chunks with true section labels.

    The document text is first divided into its natural sections
    (SKILLS, WORK_EXPERIENCE, EDUCATION, SUMMARY); each section is then
    chunked with the same sliding-window strategy as ``chunk_document`` and
    labeled with its real section type. Offsets remain relative to the full
    source document text.
    """
    text = doc.text
    if not text:
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks: list[TextChunk] = []
    search_from = 0

    for section_name, section_text in split_resume_sections(text):
        # Locate the section inside the source to compute absolute offsets.
        base = text.find(section_text.lstrip()[:64], search_from)
        if base == -1:
            base = search_from
        stripped_lead = len(section_text) - len(section_text.lstrip())
        base += stripped_lead
        body = section_text.strip()
        search_from = max(search_from, base + 1)

        local_start = 0
        while local_start < len(body):
            local_end = min(local_start + chunk_size, len(body))
            chunks.append(
                TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=body[local_start:local_end],
                    candidate_id=candidate_id,
                    section_name=section_name,
                    start_offset=base + local_start,
                    end_offset=base + local_end,
                )
            )
            if local_end == len(body):
                break
            local_start += step

    return chunks
