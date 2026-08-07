from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
import sqlite3

def get_engine(db_path: str) -> Engine:
    """
    Create a SQLAlchemy engine configured for SQLite with WAL mode.
    """
    engine = create_engine(db_path)
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        # Apply pragmas required by the Architecture Design Document
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
            cursor.execute("PRAGMA page_size=4096;")
            cursor.execute("PRAGMA cache_size=-64000;")
            cursor.close()
            
    return engine
