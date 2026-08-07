"""Shared data model for all ingestion parsers."""
from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    """Canonical output of every parser.

    Attributes:
        text:      Full extracted plain-text, stripped of formatting noise.
        pages:     Number of pages / slides / messages parsed.
        metadata:  Source-specific key-value metadata (headers, filenames, etc.).
    """
    text: str
    pages: int
    metadata: dict = field(default_factory=dict)
