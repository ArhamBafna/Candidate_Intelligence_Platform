import pytest
from sqlalchemy import inspect
from config.database import get_engine
from storage.db_models import Base, init_db

def test_db_schema_creation():
    """Verify that all relational and FTS5 tables are created successfully."""
    engine = get_engine("sqlite:///:memory:")
    
    # Initialize the database (this should create tables and FTS5 virtual tables)
    init_db(engine)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = {
        "candidates",
        "resume_versions",
        "candidate_claims",
        "candidate_timeline_events",
        "entity_resolution_audit",
        "candidate_fts",
        "claims_fts"
    }
    
    # Some SQLite versions might return internal tables or FTS shadow tables,
    # so we just check if our expected tables are a subset of all created tables.
    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' not found in database."
