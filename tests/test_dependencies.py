import pytest
from sqlalchemy.orm import Session
from config.settings import Settings
from api.dependencies import get_settings, get_db, get_vector_db
import lancedb

def test_get_settings():
    settings = get_settings()
    assert isinstance(settings, Settings)

def test_get_db():
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    
    # Check that it closes properly
    try:
        next(db_gen)
    except StopIteration:
        pass
    else:
        pytest.fail("Generator did not stop")

def test_get_vector_db():
    vector_db = get_vector_db()
    assert isinstance(vector_db, lancedb.DBConnection)
