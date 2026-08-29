import os
from functools import lru_cache
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    db_path: str = os.path.join(BASE_DIR, "storage", "cip_main.db")
    cas_root_dir: str = os.path.join(BASE_DIR, "storage", "documents")
    vector_db_path: str = os.path.join(BASE_DIR, "storage", "lancedb")
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    llm_model: str = "llama3.2"
    fallback_llm_model: str = "llama3.2"
    llm_provider: str = "ollama"
    openrouter_api_key: str = ""
    openrouter_model: str = "stealth/ox-alpha"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    extraction_confidence_threshold: float = 0.40
    entity_res_auto_merge_threshold: float = 0.85
    entity_res_review_threshold: float = 0.70
    rrf_k: int = 60
    keyword_weight: float = 1.0
    vector_weight: float = 1.0
    vector_pool_size: int = 100
    rerank_pool_size: int = 50
    default_top_k: int = 10

    model_config = {
        "env_prefix": "CIP_",
        "env_file": os.path.join(BASE_DIR, ".env"),
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings singleton.

    Cached after the first call so the env file is parsed exactly once.
    Call ``get_settings.cache_clear()`` in tests that need a fresh instance.
    """
    return Settings()
