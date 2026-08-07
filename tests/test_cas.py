import os
from pathlib import Path
import pytest
from storage.cas import CASManager

def test_cas_storage(tmp_path):
    """Verify CAS saves files at the correct sharded paths and deduplicates identical contents."""
    cas_manager = CASManager(root_dir=tmp_path)
    
    # Create a dummy file to ingest
    content = b"Candidate Intelligence Resume V1"
    
    # 1. Store the file
    file_hash, cas_path = cas_manager.store(content, extension=".pdf")
    
    # Expected SHA256 for the content
    import hashlib
    expected_hash = hashlib.sha256(content).hexdigest()
    assert file_hash == expected_hash
    
    # 2. Check the path sharding structure
    expected_path = tmp_path / expected_hash[:2] / expected_hash[2:4] / f"{expected_hash}.pdf"
    assert Path(cas_path) == expected_path
    assert expected_path.exists()
    
    # 3. Read-only verification
    assert not os.access(expected_path, os.W_OK)

    # 4. Idempotency (storing same content again should just return the path, no error)
    file_hash_2, cas_path_2 = cas_manager.store(content, extension=".pdf")
    assert file_hash == file_hash_2
    assert cas_path == cas_path_2
