import pytest
from config.settings import Settings

def test_default_settings():
    """Verify that default settings conform to the architectural directives."""
    settings = Settings()
    
    assert settings.db_path == "storage/cip_main.db"
    assert settings.cas_root_dir == "storage/documents"
    assert settings.vector_db_path == "storage/lancedb"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.entity_resolution_auto_merge_threshold == 0.92
