import logging
import os
import sys
import threading
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

LOG_BUFFER = deque(maxlen=100)
_buffer_lock = threading.Lock()

POLLING_PREFIXES = ("/logs", "/health")

# GET /logs serves LOG_BUFFER without authentication, so candidate-identifying
# fields are stripped from buffered copies only; the console renderer still
# receives the full event dict and keeps its rich upload cards.
REDACTED_BUFFER_KEYS = frozenset({"candidate_name", "file_name"})

EVENT_PHRASES = {
    "embedding_model_loaded": "Embedding Model Loaded",
    "reranker_model_loaded": "Reranker Model Loaded",
    "gpu_available": "GPU Available",
    "gpu_unavailable": "GPU Unavailable",
}

RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"

LEVEL_COLORS = {"info": CYAN, "warning": YELLOW, "error": RED, "debug": DIM, "critical": RED}


def is_polling_path(path: str) -> bool:
    return path.startswith(POLLING_PREFIXES)


class UvicornAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return False


def memory_buffer_processor(logger: Any, method_name: str, event_dict: structlog.types.EventDict) -> structlog.types.EventDict:
    with _buffer_lock:
        LOG_BUFFER.appendleft({key: value for key, value in event_dict.items() if key not in REDACTED_BUFFER_KEYS})
    return event_dict


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with _buffer_lock:
        return list(LOG_BUFFER)[:limit]


def _enable_windows_ansi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _resolve_format(format_name: Optional[str] = None) -> str:
    chosen = (format_name or os.getenv("CIP_LOG_FORMAT", "console")).strip().lower()
    return chosen if chosen in ("console", "json") else "console"


def _use_color() -> bool:
    return "NO_COLOR" not in os.environ and bool(sys.stdout.isatty())


def _paint(text: str, code: str, enabled: bool) -> str:
    return f"{code}{text}{RESET}" if enabled else text


def _local_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


ACRONYMS = {"ai": "AI", "llm": "LLM", "gpu": "GPU", "cas": "CAS", "ocr": "OCR", "sse": "SSE", "api": "API", "url": "URL", "id": "ID", "fts": "FTS", "json": "JSON"}


def _fallback_phrase(event: str) -> str:
    if " " in event:
        return event
    words = []
    for token in event.split("_"):
        words.append(ACRONYMS.get(token.lower(), token.title()))
    return " ".join(words)


def _title_words(value: str) -> str:
    return value.replace("_", " ").title()


def _short_extras(event_dict: structlog.types.EventDict, enabled: bool) -> str:
    parts = []
    for key, value in event_dict.items():
        if key in ("event", "level", "timestamp", "request_id", "path", "method", "duration_ms"):
            continue
        parts.append(str(value))
    detail = " ".join(parts).strip()
    if len(detail) > 160:
        detail = detail[:157] + "..."
    return _paint(f" {detail}", DIM, enabled) if detail else ""


def _render_block(lines: List[str], color: str, enabled: bool) -> str:
    head = _paint(lines[0], f"{BOLD}{color}".strip(), enabled)
    body = [_paint(f"   {line}", RESET, False) for line in lines[1:]]
    return "\n".join([head] + body)


def _render_upload(event_dict: structlog.types.EventDict, level: str, enabled: bool) -> str:
    ts = _paint(_local_time(), DIM, enabled)
    lvl = _paint(level.upper(), LEVEL_COLORS.get(level, ""), enabled)
    status = event_dict.get("status")
    duration = event_dict.get("duration_s")
    tail = _paint(f" in {duration}s", DIM, enabled) if isinstance(duration, (int, float)) else ""

    if status == "success":
        name = str(event_dict.get("candidate_name") or "").strip()
        fname = str(event_dict.get("file_name") or "").strip()
        who = f"{name} ({fname})" if name and fname else (name or fname or "Unnamed Candidate")
        classified = _title_words(str(event_dict.get("classified_as") or ""))
        lines = [
            f"{ts} {lvl} RESUME UPLOADED{tail}",
            f"Candidate: {who}",
            f"Classified = {classified}" if classified else "Classified = Unknown",
        ]
        return _render_block(lines, GREEN, enabled)

    if status == "skipped":
        reason = event_dict.get("skip_reason")
        fname = str(event_dict.get("file_name") or "").strip()
        if reason == "cas_duplicate":
            lines = [
                f"{ts} {lvl} DUPLICATE SKIPPED{tail}",
                f"File: {fname or 'unknown'} (already stored)",
            ]
        else:
            classified = _title_words(str(event_dict.get("category") or event_dict.get("classified_as") or ""))
            lines = [
                f"{ts} {lvl} NOT A RESUME{tail}",
                f"File: {fname or 'unknown'}",
                f"Classified = {classified}" if classified else "",
            ]
            lines = [line for line in lines if line]
        return _render_block(lines, YELLOW, enabled)

    if status == "failed":
        fname = str(event_dict.get("file_name") or "").strip()
        lines = [f"{ts} {lvl} UPLOAD FAILED{tail}"]
        if fname:
            lines.append(f"File: {fname}")
        error = str(event_dict.get("error") or "").strip()
        if error:
            lines.append(f"Error: {error}")
        return _render_block(lines, RED, enabled)

    phrase = _fallback_phrase(str(event_dict.get("event", "")))
    return f"{ts} {lvl} {_paint(phrase, BOLD, enabled)}{_short_extras(event_dict, enabled)}"


def _render_single_line(event_dict: structlog.types.EventDict, level: str, phrase: str, enabled: bool, show_extras: bool = True) -> str:
    ts = _paint(_local_time(), DIM, enabled)
    lvl = _paint(level.upper(), LEVEL_COLORS.get(level, ""), enabled)
    extras = _short_extras(event_dict, enabled) if show_extras else ""
    return f"{ts} {lvl} {_paint(phrase, BOLD, enabled)}{extras}"


def _render_http_request(event_dict: structlog.types.EventDict, level: str, enabled: bool) -> str:
    ts = _paint(_local_time(), DIM, enabled)
    method = str(event_dict.get("method") or event_dict.get("http_method") or "")
    path = str(event_dict.get("path") or "")
    status_code = event_dict.get("status_code", "")
    duration = event_dict.get("duration_s")
    dur = f" {duration}s" if isinstance(duration, (int, float)) else ""
    request_id = str(event_dict.get("request_id") or "")
    status_color = ""
    try:
        code_int = int(status_code)
        status_color = RED if code_int >= 500 else (YELLOW if code_int >= 400 else "")
    except (TypeError, ValueError):
        pass
    status_part = _paint(str(status_code), status_color, enabled) if status_color else str(status_code)
    body = _paint(f"{method} {path} {status_part}{dur} req={request_id}", DIM, enabled)
    return f"{ts} {body}"


def _render_search(event_dict: structlog.types.EventDict, level: str, enabled: bool) -> str:
    ts = _paint(_local_time(), DIM, enabled)
    lvl = _paint(level.upper(), LEVEL_COLORS.get(level, ""), enabled)
    query = str(event_dict.get("query") or "")
    count = event_dict.get("candidates_returned", "")
    total_ms = event_dict.get("total_duration_ms", "")
    detail = _paint(f' "{query}" | {count} results | {total_ms}ms', DIM, enabled)
    return f"{ts} {lvl} {_paint('SEARCH COMPLETE', BOLD, enabled)}{detail}"


def _render_delete(event_dict: structlog.types.EventDict, level: str, enabled: bool) -> str:
    ts = _paint(_local_time(), DIM, enabled)
    lvl = _paint(level.upper(), LEVEL_COLORS.get(level, ""), enabled)
    requested = event_dict.get("requested_count", "?")
    deleted = event_dict.get("deleted_count", "?")
    lines = [
        f"{ts} {lvl} CANDIDATES DELETED",
        f"Requested = {requested} | Deleted = {deleted}",
    ]
    return _render_block(lines, GREEN if requested == deleted else YELLOW, enabled)


def _model_device_detail(event_dict: structlog.types.EventDict, enabled: bool) -> str:
    if "gpu" in event_dict:
        return _paint(f" (device={'gpu' if event_dict['gpu'] else 'cpu'})", DIM, enabled)
    return ""


def _gpu_detail(event_dict: structlog.types.EventDict, enabled: bool) -> str:
    providers = event_dict.get("available_providers")
    if isinstance(providers, list):
        names = ", ".join(str(p).replace("ExecutionProvider", "") for p in providers)
        return _paint(f" (providers: {names})", DIM, enabled)
    if "provider" in event_dict:
        return _paint(f" ({str(event_dict['provider']).replace('ExecutionProvider', '')})", DIM, enabled)
    if "reason" in event_dict:
        return _paint(f" ({event_dict['reason']})", DIM, enabled)
    return ""


def console_renderer(logger: Any, method_name: str, event_dict: structlog.types.EventDict) -> str:
    enabled = _use_color()
    level = str(event_dict.get("level", method_name))
    event = str(event_dict.get("event", ""))
    rendered = dict(event_dict)

    if event == "http_request":
        return _render_http_request(rendered, level, enabled)

    if event == "resume_upload_complete":
        return _render_upload(rendered, level, enabled)

    if event == "candidates_deleted":
        return _render_delete(rendered, level, enabled)

    if event == "candidate_search_complete":
        return _render_search(rendered, level, enabled)

    if event in ("embedding_model_loaded", "reranker_model_loaded"):
        phrase = EVENT_PHRASES[event] + _model_device_detail(rendered, enabled)
        return _render_single_line(rendered, level, phrase, enabled, show_extras=False)

    if event in ("gpu_available", "gpu_unavailable"):
        phrase = EVENT_PHRASES[event] + _gpu_detail(rendered, enabled)
        return _render_single_line(rendered, level, phrase, enabled, show_extras=False)

    if "error" in rendered and level in ("warning", "error"):
        phrase = _fallback_phrase(event)
        ts = _paint(_local_time(), DIM, enabled)
        lvl = _paint(level.upper(), LEVEL_COLORS.get(level, ""), enabled)
        err = str(rendered["error"])
        if len(err) > 160:
            err = err[:157] + "..."
        return f"{ts} {lvl} {_paint(phrase, BOLD, enabled)}{_paint(f' - {err}', DIM, enabled)}"

    if event == "candidate_deleted":
        return _render_single_line(rendered, level, "Candidate Deleted", enabled, show_extras=False)

    return _render_single_line(rendered, level, _fallback_phrase(event), enabled)


def json_renderer(logger: Any, method_name: str, event_dict: structlog.types.EventDict) -> str:
    return structlog.processors.JSONRenderer()(logger, method_name, event_dict)


class _DynamicStdoutLogger:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def msg(self, message: str) -> None:
        with self._lock:
            print(message, flush=True)

    log = msg
    debug = msg
    info = msg
    warning = msg
    error = msg
    fatal = msg


def setup_logging(format_name: Optional[str] = None) -> None:
    _enable_windows_ansi()
    chosen = _resolve_format(format_name)
    renderer = json_renderer if chosen == "json" else console_renderer
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            memory_buffer_processor,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=lambda *_args, **_kw: _DynamicStdoutLogger(),
        cache_logger_on_first_use=True
    )
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, UvicornAccessFilter) for f in access_logger.filters):
        access_logger.addFilter(UvicornAccessFilter())
