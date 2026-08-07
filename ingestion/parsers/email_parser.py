"""Email parser supporting .eml (RFC-2822) and .msg (Outlook) files.

Public interface:
    parse_email(path: Path) -> ParsedDocument
"""
from __future__ import annotations

import email as email_lib
import email.header as email_header
from pathlib import Path

from ingestion.parsers.models import ParsedDocument


def parse_email(path: Path) -> ParsedDocument:
    """Extract body text and header metadata from an email file.

    Dispatch:
      - ``.msg`` extension → ``extract_msg`` library (Outlook MAPI format).
      - All other extensions (``.eml``, ``.txt``) → stdlib ``email`` parser
        (RFC-2822 / MIME format).

    Multipart messages:
      - ``text/plain`` parts are preferred and concatenated.
      - If no ``text/plain`` exists, ``text/html`` parts are stripped of tags
        and used as fallback.

    Args:
        path: Absolute or relative path to the email file.

    Returns:
        ParsedDocument with body text (pages=1) and header metadata.
    """
    path = Path(path)

    if path.suffix.lower() == ".msg":
        return _parse_msg(path)
    else:
        return _parse_eml(path)


# ---------------------------------------------------------------------------
# .eml / RFC-2822 parser
# ---------------------------------------------------------------------------

def _decode_header(value: str | None) -> str:
    """Collapse RFC-2822 encoded-word headers into a plain Unicode string.

    Handles both unencoded ASCII values and encoded-word sequences like
    ``=?utf-8?q?Application_for_SWE_Role?=``.
    """
    if not value:
        return ""
    parts = email_header.decode_header(value)
    decoded_parts: list[str] = []
    for payload, charset in parts:
        if isinstance(payload, bytes):
            decoded_parts.append(payload.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(payload)
    return " ".join(decoded_parts).strip()


def _parse_eml(path: Path) -> ParsedDocument:
    """Parse a standard RFC-2822 / MIME email file."""
    raw = path.read_bytes()
    msg = email_lib.message_from_bytes(raw)

    subject = _decode_header(msg.get("Subject"))
    sender = _decode_header(msg.get("From"))
    recipient = _decode_header(msg.get("To"))

    body_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip())
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body_parts.append(payload.decode(charset, errors="replace").strip())

    return ParsedDocument(
        text="\n".join(body_parts),
        pages=1,
        metadata={
            "subject": subject,
            "from": sender,
            "to": recipient,
            "source_path": str(path),
        },
    )


# ---------------------------------------------------------------------------
# .msg (Outlook MAPI) parser
# ---------------------------------------------------------------------------

def _parse_msg(path: Path) -> ParsedDocument:
    """Parse an Outlook .msg file using the extract_msg library."""
    import extract_msg  # type: ignore[import]

    with extract_msg.openMsg(str(path)) as msg:
        subject = msg.subject or ""
        sender = msg.sender or ""
        recipient = msg.to or ""
        body = (msg.body or "").strip()

    return ParsedDocument(
        text=body,
        pages=1,
        metadata={
            "subject": subject,
            "from": sender,
            "to": recipient,
            "source_path": str(path),
        },
    )
