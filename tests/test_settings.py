import pytest
from config.settings import Settings

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
    assert settings.extraction_confidence_threshold == 0.40
    assert settings.entity_res_auto_merge_threshold == 0.85
    assert settings.entity_res_review_threshold == 0.70
