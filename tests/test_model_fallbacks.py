import pytest
from config.settings import Settings

EMBEDDINGS_MODULE = "candidate_intelligence_platform.intelligence.embeddings"
RERANKER_MODULE = "candidate_intelligence_platform.search.reranker"


@pytest.fixture(autouse=True)
def reset_lazy_model_globals():
    """Reset lazy-loaded model singletons so every test starts fresh."""
    import candidate_intelligence_platform.intelligence.embeddings as emb
    import candidate_intelligence_platform.search.reranker as rer

    emb._embedding_model = None
    emb._embedding_model_name = None
    rer._reranker_model = None
    rer._reranker_model_name = None
    yield
    emb._embedding_model = None
    emb._embedding_model_name = None
    rer._reranker_model = None
    rer._reranker_model_name = None


@pytest.fixture(autouse=True)
def clean_model_env(monkeypatch):
    monkeypatch.delenv("CIP_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("CIP_RERANKER_MODEL", raising=False)


class SentinelModel:
    pass


class SpyLogger:
    """Stands in for the module-level structlog logger (which may already be
    cached-on-first-use by earlier tests, making capture_logs unreliable)."""

    def __init__(self):
        self.events = []

    def _record(self, method_name, event, kwargs):
        self.events.append({"level": method_name, "event": event, **kwargs})

    def info(self, event, **kwargs):
        self._record("info", event, kwargs)

    def warning(self, event, **kwargs):
        self._record("warning", event, kwargs)

    def error(self, event, **kwargs):
        self._record("error", event, kwargs)


def test_embedding_model_loaded_from_settings(monkeypatch):
    import candidate_intelligence_platform.intelligence.embeddings as emb

    monkeypatch.setenv("CIP_EMBEDDING_MODEL", "custom/embed-model")
    calls = []

    def fake_load(model_name):
        calls.append(model_name)
        return SentinelModel()

    monkeypatch.setattr(f"{EMBEDDINGS_MODULE}._load_text_embedding", fake_load)

    model = emb._get_embedding_model()

    assert isinstance(model, SentinelModel)
    assert calls == ["custom/embed-model"]
    assert emb.get_embedding_model_name() == "custom/embed-model"


def test_invalid_embedding_model_falls_back_to_default_with_warning(monkeypatch):
    import candidate_intelligence_platform.intelligence.embeddings as emb
    from candidate_intelligence_platform.intelligence.embeddings import DEFAULT_EMBEDDING_MODEL

    monkeypatch.setenv("CIP_EMBEDDING_MODEL", "not-a-real-model")
    spy = SpyLogger()
    monkeypatch.setattr(emb, "logger", spy)
    calls = []

    def fake_load(model_name):
        calls.append(model_name)
        if model_name == "not-a-real-model":
            raise RuntimeError("model not found")
        return SentinelModel()

    monkeypatch.setattr(f"{EMBEDDINGS_MODULE}._load_text_embedding", fake_load)

    model = emb._get_embedding_model()

    assert isinstance(model, SentinelModel)
    assert calls == ["not-a-real-model", DEFAULT_EMBEDDING_MODEL]
    assert emb.get_embedding_model_name() == DEFAULT_EMBEDDING_MODEL

    events = [e for e in spy.events if e["event"] == "ai_embedding_model_fallback"]
    assert len(events) == 1
    assert events[0]["configured_model"] == "not-a-real-model"
    assert events[0]["fallback_model"] == DEFAULT_EMBEDDING_MODEL
    assert events[0]["action"] == "loading_documented_default"


def test_reranker_model_loaded_from_settings(monkeypatch):
    import candidate_intelligence_platform.search.reranker as rer

    monkeypatch.setenv("CIP_RERANKER_MODEL", "custom/rerank-model")
    calls = []

    def fake_load(model_name):
        calls.append(model_name)
        return SentinelModel()

    monkeypatch.setattr(f"{RERANKER_MODULE}._load_text_cross_encoder", fake_load)

    model = rer._get_reranker()

    assert isinstance(model, SentinelModel)
    assert calls == ["custom/rerank-model"]
    assert rer.get_reranker_model_name() == "custom/rerank-model"


def test_invalid_reranker_model_falls_back_to_default_with_warning(monkeypatch):
    import candidate_intelligence_platform.search.reranker as rer
    from candidate_intelligence_platform.search.reranker import DEFAULT_RERANKER_MODEL

    monkeypatch.setenv("CIP_RERANKER_MODEL", "also-not-real")
    spy = SpyLogger()
    monkeypatch.setattr(rer, "logger", spy)
    calls = []

    def fake_load(model_name):
        calls.append(model_name)
        if model_name == "also-not-real":
            raise RuntimeError("model not found")
        return SentinelModel()

    monkeypatch.setattr(f"{RERANKER_MODULE}._load_text_cross_encoder", fake_load)

    model = rer._get_reranker()

    assert isinstance(model, SentinelModel)
    assert calls == ["also-not-real", DEFAULT_RERANKER_MODEL]
    assert rer.get_reranker_model_name() == DEFAULT_RERANKER_MODEL

    events = [e for e in spy.events if e["event"] == "ai_reranker_model_fallback"]
    assert len(events) == 1
    assert events[0]["configured_model"] == "also-not-real"
    assert events[0]["fallback_model"] == DEFAULT_RERANKER_MODEL
    assert events[0]["action"] == "loading_documented_default"
