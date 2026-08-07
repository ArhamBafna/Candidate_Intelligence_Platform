import pytest
from sqlalchemy import text
from config.database import get_engine

def test_sqlite_wal_mode(tmp_path):
    """Verify that the database engine connects and sets WAL mode correctly."""
    # SQLite memory databases do not support WAL mode, so we use a temp file
    db_file = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_file}")
    
    with engine.connect() as conn:
        # Check if WAL mode is enabled
        result = conn.execute(text("PRAGMA journal_mode;")).scalar()
        assert result.lower() == "wal"
