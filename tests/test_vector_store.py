import pytest
import os
from storage.vector_store import get_lancedb_connection, CandidateSectionVector

def test_lancedb_initialization(tmp_path):
    """Verify LanceDB connection and table initialization."""
    db_path = str(tmp_path / "lancedb")
    
    db = get_lancedb_connection(db_path)
    
    # Initialize or get the table
    table = db.create_table(
        "candidate_sections", 
        schema=CandidateSectionVector, 
        exist_ok=True
    )
    
    assert table.name == "candidate_sections"
    assert "chunk_id" in table.schema.names
    assert "vector" in table.schema.names
