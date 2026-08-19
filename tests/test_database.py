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

def test_engine_connect_event_non_sqlite():
    from sqlalchemy import event
    from config.database import get_engine
    
    # We can inspect the listeners
    engine = get_engine("sqlite:///:memory:")
    
    # Get the connect listener
    listeners = engine.pool.dispatch.connect.listeners
    connect_listener = next(l for l in listeners if l.__name__ == "set_sqlite_pragma")
    
    class MockConnection:
        def __init__(self):
            self.cursor_called = False
            
        def cursor(self):
            self.cursor_called = True
            return None
            
    mock_conn = MockConnection()
    
    # Call the listener with a non-sqlite connection
    connect_listener(mock_conn, None)
    
    # Cursor should not have been called because it's not a sqlite3.Connection
    assert not mock_conn.cursor_called
