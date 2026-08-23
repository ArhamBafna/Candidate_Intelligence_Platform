import logging
import pytest
import structlog
from config.logging import (
    setup_logging,
    UvicornAccessFilter,
    LOG_BUFFER,
    get_recent_logs,
    memory_buffer_processor,
    console_renderer,
    is_polling_path,
    _resolve_format,
)


def _render(event_dict):
    return console_renderer(None, event_dict.get("level", "info"), dict(event_dict))


def test_uvicorn_access_filter_silences_all_access_lines():
    log_filter = UvicornAccessFilter()

    for msg in [
        '127.0.0.1:60998 - "GET /logs HTTP/1.1" 200 OK',
        '127.0.0.1:60998 - "GET /api/candidates HTTP/1.1" 200 OK',
        '127.0.0.1:60998 - "POST /candidates/upload-stream HTTP/1.1" 200 OK',
    ]:
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        assert log_filter.filter(record) is False


def test_setup_logging_configures_structlog():
    setup_logging()

    assert structlog.is_configured()

    logger = structlog.get_logger()
    logger = logger.bind(test_key="test_value")

    access_logger = logging.getLogger("uvicorn.access")
    assert any(isinstance(f, UvicornAccessFilter) for f in access_logger.filters)


def test_get_recent_logs_truncation():
    LOG_BUFFER.clear()
    for i in range(10):
        LOG_BUFFER.appendleft({"msg": f"log {i}"})

    logs = get_recent_logs(limit=5)
    assert len(logs) == 5
    assert logs[0] == {"msg": "log 9"}


def test_memory_buffer_processor():
    LOG_BUFFER.clear()

    event_dict = {"event": "test_event", "level": "info"}

    result = memory_buffer_processor(None, "info", event_dict)

    assert result == event_dict
    assert len(LOG_BUFFER) == 1
    assert LOG_BUFFER[0] == event_dict


def test_buffer_redacts_candidate_identity_but_console_keeps_it():
    """PR #25 review: /logs buffer drops PII; the console card keeps it."""
    LOG_BUFFER.clear()

    event = {
        "event": "resume_upload_complete",
        "status": "success",
        "candidate_name": "Jane Doe",
        "file_name": "jane-resume.pdf",
        "classified_as": "VALID_RESUME",
        "duration_s": 1.5,
    }
    line = _render(dict(event))
    memory_buffer_processor(None, "info", event)

    buffered = LOG_BUFFER[0]
    assert "candidate_name" not in buffered
    assert "file_name" not in buffered

    assert "Candidate: Jane Doe (jane-resume.pdf)" in line


def test_is_polling_path():
    assert is_polling_path("/logs") is True
    assert is_polling_path("/health") is True
    assert is_polling_path("/candidates") is False
    assert is_polling_path("/candidates/batch-delete") is False


def test_resolve_format_defaults_to_console(monkeypatch):
    monkeypatch.delenv("CIP_LOG_FORMAT", raising=False)
    assert _resolve_format() == "console"


def test_resolve_format_json_toggle(monkeypatch):
    monkeypatch.setenv("CIP_LOG_FORMAT", "json")
    assert _resolve_format() == "json"


def test_resolve_format_invalid_falls_back_to_console(monkeypatch):
    monkeypatch.setenv("CIP_LOG_FORMAT", "yaml")
    assert _resolve_format() == "console"


def test_console_upload_success_block_no_underscores():
    line = _render({
        "level": "info",
        "event": "resume_upload_complete",
        "status": "success",
        "candidate_name": "John Doe",
        "file_name": "john-doe-resume.pdf",
        "classified_as": "VALID_RESUME",
        "duration_s": 3.1,
        "request_id": "a22fde4c-d516-4b9e-9d64-0129ad45fd2f",
        "path": "/candidates/upload-stream",
        "method": "POST",
    })

    assert "RESUME UPLOADED" in line
    assert "in 3.1s" in line
    assert "Candidate: John Doe (john-doe-resume.pdf)" in line
    assert "Classified = Valid Resume" in line
    assert "_" not in line.split("\n", 1)[1]


def test_console_upload_success_without_name_uses_file():
    line = _render({
        "level": "info",
        "event": "resume_upload_complete",
        "status": "success",
        "candidate_name": "",
        "file_name": "mystery.pdf",
        "classified_as": "VALID_RESUME",
    })
    assert "Candidate: mystery.pdf" in line


def test_console_duplicate_skip_block():
    line = _render({
        "level": "info",
        "event": "resume_upload_complete",
        "status": "skipped",
        "skip_reason": "cas_duplicate",
        "file_name": "dupe.pdf",
    })
    assert "DUPLICATE SKIPPED" in line
    assert "dupe.pdf (already stored)" in line


def test_console_non_resume_skip_block():
    line = _render({
        "level": "info",
        "event": "resume_upload_complete",
        "status": "skipped",
        "skip_reason": "non_resume",
        "category": "SPAM_DOCUMENT",
        "file_name": "notes.txt",
    })
    assert "NOT A RESUME" in line
    assert "notes.txt" in line
    assert "Classified = Spam Document" in line


def test_console_failed_upload_block():
    line = _render({
        "level": "error",
        "event": "resume_upload_complete",
        "status": "failed",
        "file_name": "broken.pdf",
        "error": "parser exploded",
    })
    assert "UPLOAD FAILED" in line
    assert "File: broken.pdf" in line
    assert "Error: parser exploded" in line


def test_console_http_request_line():
    line = _render({
        "level": "info",
        "event": "http_request",
        "http_method": "POST",
        "path": "/candidates/upload-stream",
        "status_code": 200,
        "duration_s": 3.24,
        "request_id": "a22fde4c-d516-4b9e-9d64-0129ad45fd2f",
    })
    assert "POST /candidates/upload-stream 200 3.24s req=a22fde4c-d516-4b9e-9d64-0129ad45fd2f" in line


def test_console_batch_delete_block():
    line = _render({
        "level": "info",
        "event": "candidates_deleted",
        "requested_count": 5,
        "deleted_count": 5,
    })
    assert "CANDIDATES DELETED" in line
    assert "Requested = 5 | Deleted = 5" in line


def test_console_model_loaded_device():
    line = _render({"level": "info", "event": "embedding_model_loaded", "gpu": False})
    assert "Embedding Model Loaded" in line
    assert "(device=cpu)" in line


def test_console_gpu_unavailable_providers():
    line = _render({
        "level": "info",
        "event": "gpu_unavailable",
        "available_providers": ["AzureExecutionProvider", "CPUExecutionProvider"],
    })
    assert "GPU Unavailable" in line
    assert "(providers: Azure, CPU)" in line


def test_console_search_complete_line():
    line = _render({
        "level": "info",
        "event": "candidate_search_complete",
        "query": "python backend",
        "candidates_returned": 12,
        "total_duration_ms": 45.2,
    })
    assert "SEARCH COMPLETE" in line
    assert '"python backend"' in line
    assert "12 results" in line


def test_console_warning_with_error_shows_message():
    line = _render({
        "level": "warning",
        "event": "ai_vector_search_failed",
        "query": "q",
        "error": "lance boom",
        "action": "falling_back_to_keyword_search",
    })
    assert "AI Vector Search Failed" in line
    assert "lance boom" in line
    assert "falling_back_to_keyword_search" not in line


def test_console_unknown_event_falls_back_to_title_case():
    line = _render({"level": "info", "event": "some_new_event"})
    assert "Some New Event" in line


def test_console_plain_sentence_event_passthrough():
    line = _render({"level": "info", "event": "SSE connection closed by client"})
    assert "SSE connection closed by client" in line


def test_setup_logging_json_mode_renders_parseable_json(capsys):
    setup_logging("json")

    logger = structlog.get_logger("json_mode_probe")
    logger.info("probe_event", detail="x")

    captured = capsys.readouterr()
    assert '"probe_event"' in captured.out

    setup_logging("console")
