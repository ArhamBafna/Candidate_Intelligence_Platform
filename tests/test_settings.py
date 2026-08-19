import pytest
from config.settings import Settings

def test_default_settings(monkeypatch):
    """Verify that default settings conform to the architectural directives."""
    monkeypatch.delenv("CIP_DB_PATH", raising=False)
    monkeypatch.delenv("CIP_CAS_ROOT_DIR", raising=False)
    monkeypatch.delenv("CIP_VECTOR_DB_PATH", raising=False)
    settings = Settings()
    
    assert settings.db_path == "storage/cip_main.db"
    assert settings.cas_root_dir == "storage/documents"
    assert settings.vector_db_path == "storage/lancedb"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.entity_resolution_auto_merge_threshold == 0.92
