import pytest
import structlog
from candidate_intelligence_platform.intelligence.chat_model import (
    chat_retry_candidates,
    normalize_model_name,
    resolve_chat_model,
    reset_chat_model_cache,
)


class FakeModelEntry:
    def __init__(self, name: str):
        self.model = name


class FakeListResponse:
    def __init__(self, names):
        self.models = [FakeModelEntry(n) for n in names]


@pytest.fixture(autouse=True)
def clean_env_and_cache(monkeypatch):
    monkeypatch.delenv("CIP_LLM_MODEL", raising=False)
    monkeypatch.delenv("CIP_FALLBACK_LLM_MODEL", raising=False)
    reset_chat_model_cache()
    yield
    reset_chat_model_cache()


def test_normalize_name_strips_tag():
    assert normalize_model_name("llama3.2:latest") == "llama3.2"
    assert normalize_model_name("LLaMA3.2 ") == "llama3.2"
    assert normalize_model_name("") == ""


def test_chat_retry_candidates_chain_and_dedup():
    assert chat_retry_candidates("mistral", "qwen2.5") == ["qwen2.5", "llama3.2"]
    assert chat_retry_candidates("mistral", "llama3.2") == ["llama3.2"]
    assert chat_retry_candidates("llama3.2", "llama3.2") == []
    assert chat_retry_candidates("mistral", "llama3.2", failed_model="qwen2.5") == ["llama3.2"]


def test_configured_chat_model_available(monkeypatch):
    monkeypatch.setattr("ollama.list", lambda: FakeListResponse(["llama3.2:latest", "mistral:7b"]))

    resolved = resolve_chat_model()

    assert resolved == "llama3.2"


def test_invalid_chat_model_retries_with_llama32_fallback(monkeypatch):
    monkeypatch.setenv("CIP_LLM_MODEL", "not-installed-model")
    monkeypatch.setattr("ollama.list", lambda: FakeListResponse(["llama3.2:latest"]))

    with structlog.testing.capture_logs() as cap_logs:
        resolved = resolve_chat_model()

    assert resolved == "llama3.2"
    events = [log for log in cap_logs if log.get("event") == "ai_chat_model_fallback"]
    assert len(events) == 1
    assert events[0]["configured_model"] == "not-installed-model"
    assert events[0]["fallback_model"] == "llama3.2"


def test_total_chat_failure_returns_none(monkeypatch):
    monkeypatch.setenv("CIP_LLM_MODEL", "ghost-model")
    monkeypatch.setattr("ollama.list", lambda: FakeListResponse(["mistral:7b"]))

    with structlog.testing.capture_logs() as cap_logs:
        resolved = resolve_chat_model()

    assert resolved is None
    events = [log for log in cap_logs if log.get("event") == "ai_chat_unavailable"]
    assert len(events) == 1


def test_ollama_probe_failure_treated_as_no_models(monkeypatch):
    def boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr("ollama.list", boom)

    with structlog.testing.capture_logs() as cap_logs:
        resolved = resolve_chat_model()

    assert resolved is None
    events = [log for log in cap_logs if log.get("event") == "ai_chat_probe_failed"]
    assert len(events) == 1


def test_resolution_is_cached(monkeypatch):
    calls = {"count": 0}

    def fake_list():
        calls["count"] += 1
        return FakeListResponse(["llama3.2:latest"])

    monkeypatch.setattr("ollama.list", fake_list)

    first = resolve_chat_model()
    second = resolve_chat_model()

    assert first == second == "llama3.2"
    assert calls["count"] == 1

    refreshed = resolve_chat_model(force_refresh=True)
    assert refreshed == "llama3.2"
    assert calls["count"] == 2


def test_dict_shaped_ollama_response_supported(monkeypatch):
    monkeypatch.setattr(
        "ollama.list",
        lambda: {"models": [{"name": "llama3.2:latest"}]},
    )

    assert resolve_chat_model() == "llama3.2"
