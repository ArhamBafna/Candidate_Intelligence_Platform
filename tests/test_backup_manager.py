import pytest
import sqlite3
import os
import shutil
from pathlib import Path
from backups.backup_manager import BackupManager

def test_live_backup(tmp_path: Path):
    source_db = tmp_path / "source.db"
    backup_db = tmp_path / "backup.db"
    
    # Setup source db with some data
    with sqlite3.connect(source_db) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('dummy data')")
        conn.commit()

    manager = BackupManager()
    manager.perform_live_backup(str(source_db), str(backup_db))

    # Verify backup db
    assert backup_db.exists()
    with sqlite3.connect(backup_db) as conn:
        result = conn.execute("SELECT name FROM test").fetchone()
        assert result[0] == 'dummy data'

def test_cas_storage_sync(tmp_path: Path):
    source_cas = tmp_path / "source_cas"
    backup_cas = tmp_path / "backup_cas"
    source_cas.mkdir(parents=True)
    
    # Create mock cas files in subdirectories
    file1 = source_cas / "ab" / "cd"
    file1.mkdir(parents=True)
    (file1 / "abcdef.pdf").write_text("dummy")

    manager = BackupManager()
    manager.sync_cas_storage(str(source_cas), str(backup_cas))

    assert (backup_cas / "ab" / "cd" / "abcdef.pdf").exists()

def test_generate_manifest(tmp_path: Path, monkeypatch):
    source_db = tmp_path / "source.db"
    source_db.write_text("dummy sqlite content")
    
    cas_dir = tmp_path / "cas"
    cas_dir.mkdir()
    (cas_dir / "12").mkdir()
    (cas_dir / "12" / "12345.txt").write_text("test")
    (cas_dir / "ab").mkdir()
    (cas_dir / "ab" / "abcde.pdf").write_text("test")

    # We mock lancedb connection for this test
    manager = BackupManager()
    
    # Mock lance row count
    monkeypatch.setattr(manager, "_get_lance_row_count", lambda path: 42)
    
    manifest = manager.generate_manifest(str(source_db), str(cas_dir), str(tmp_path / "lance"))
    
    assert "db_sha256" in manifest
    assert manifest["cas_file_count"] == 2
    assert manifest["vector_count"] == 42
