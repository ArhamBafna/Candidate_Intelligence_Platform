import pytest
from config.settings import Settings, get_settings

DEFAULTS = [
    "CIP_EMBEDDING_MODEL",
    "CIP_RERANKER_MODEL",
    "CIP_LLM_MODEL",
    "CIP_FALLBACK_LLM_MODEL",
    "CIP_RRF_K",
    "CIP_KEYWORD_WEIGHT",
    "CIP_VECTOR_WEIGHT",
    "CIP_VECTOR_POOL_SIZE",
    "CIP_RERANK_POOL_SIZE",
    "CIP_DEFAULT_TOP_K",
]

@pytest.fixture(autouse=True)
def clean_model_env(monkeypatch):
    for key in DEFAULTS:
        monkeypatch.delenv(key, raising=False)


def test_default_settings(monkeypatch):
    """Verify that default settings conform to the architectural directives."""
    monkeypatch.delenv("CIP_DB_PATH", raising=False)
    monkeypatch.delenv("CIP_CAS_ROOT_DIR", raising=False)
    monkeypatch.delenv("CIP_VECTOR_DB_PATH", raising=False)
    settings = Settings()
    
    assert settings.db_path.endswith("cip_main.db")
    assert settings.cas_root_dir.endswith("documents")
    assert settings.vector_db_path.endswith("lancedb")
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.reranker_model == "Xenova/ms-marco-MiniLM-L-6-v2"
    assert settings.llm_model == "llama3.2"
    assert settings.fallback_llm_model == "llama3.2"
    assert settings.extraction_confidence_threshold == 0.40
    assert settings.entity_res_auto_merge_threshold == 0.85
    assert settings.entity_res_review_threshold == 0.70
    assert settings.rrf_k == 60
    assert settings.keyword_weight == 1.0
    assert settings.vector_weight == 1.0
    assert settings.vector_pool_size == 100
    assert settings.rerank_pool_size == 50
    assert settings.default_top_k == 10

def test_model_and_tuning_settings_support_env_overrides(monkeypatch):
    monkeypatch.setenv("CIP_EMBEDDING_MODEL", "custom/embedding")
    monkeypatch.setenv("CIP_RERANKER_MODEL", "custom/reranker")
    monkeypatch.setenv("CIP_LLM_MODEL", "mistral")
    monkeypatch.setenv("CIP_FALLBACK_LLM_MODEL", "qwen2.5")
    monkeypatch.setenv("CIP_RRF_K", "42")
    monkeypatch.setenv("CIP_KEYWORD_WEIGHT", "0.7")
    monkeypatch.setenv("CIP_VECTOR_WEIGHT", "1.3")
    monkeypatch.setenv("CIP_VECTOR_POOL_SIZE", "25")
    monkeypatch.setenv("CIP_RERANK_POOL_SIZE", "8")
    monkeypatch.setenv("CIP_DEFAULT_TOP_K", "5")

    settings = Settings()

    assert settings.embedding_model == "custom/embedding"
    assert settings.reranker_model == "custom/reranker"
    assert settings.llm_model == "mistral"
    assert settings.fallback_llm_model == "qwen2.5"
    assert settings.rrf_k == 42
    assert settings.keyword_weight == 0.7
    assert settings.vector_weight == 1.3
    assert settings.vector_pool_size == 25
    assert settings.rerank_pool_size == 8
    assert settings.default_top_k == 5

def test_get_settings_returns_cached_singleton():
    """get_settings() must return the same object on repeated calls (lru_cache contract)."""
    a = get_settings()
    b = get_settings()
    assert a is b, "get_settings() should return the same cached instance"

def test_get_settings_cache_clear_produces_new_instance():
    """cache_clear() must invalidate the singleton so tests can get a fresh instance."""
    a = get_settings()
    get_settings.cache_clear()
    b = get_settings()
    assert a is not b, "get_settings() after cache_clear() should return a new instance"
