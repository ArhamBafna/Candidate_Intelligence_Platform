"""Consolidated storage and persistence tests.

Covers:
- Database configuration, SQLite WAL mode, and schema tables
- Settings and configuration overrides
- Content Addressable Storage (CAS)
- BackupManager (live backup, CAS sync, manifest)
- Vector store (LanceDB)
- Index writer vector deletion
"""
import hashlib
import os
import sqlite3
import uuid
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from config.database import get_engine
from config.settings import Settings, get_settings
from backups.backup_manager import BackupManager
from storage.cas import CASManager
from storage.db_models import Base, Candidate, init_db
from storage.index_writer import StorageIndexWriter, _has_candidate_vectors_table
from storage.vector_store import (
    CandidateSectionVector,
    get_lancedb_connection,
)


# ---------------------------------------------------------------------------
# Database & Schema
# ---------------------------------------------------------------------------

def test_sqlite_wal_mode(tmp_path: Path):
    """Verify engine connects and sets WAL mode."""
    db_file = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode;")).scalar()
        assert result.lower() == "wal"


def test_engine_connect_event_non_sqlite():
    engine = get_engine("sqlite:///:memory:")
    listeners = engine.pool.dispatch.connect.listeners
    connect_listener = next(l for l in listeners if l.__name__ == "set_sqlite_pragma")

    class MockConnection:
        def __init__(self):
            self.cursor_called = False

        def cursor(self):
            self.cursor_called = True
            return None

    mock_conn = MockConnection()
    connect_listener(mock_conn, None)
    assert not mock_conn.cursor_called


def test_db_schema_creation():
    """Verify all relational and FTS5 tables are created successfully."""
    engine = get_engine("sqlite:///:memory:")
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
        "claims_fts",
    }
    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' not found in database."


# ---------------------------------------------------------------------------
# Settings & Configuration
# ---------------------------------------------------------------------------

SETTINGS_DEFAULTS = [
    "CIP_EMBEDDING_MODEL",
    "CIP_RERANKER_MODEL",
    "CIP_LLM_MODEL",
    "CIP_FALLBACK_LLM_MODEL",
    "CIP_RRF_K",
    "CIP_KEYWORD_WEIGHT",
    "CIP_VECTOR_WEIGHT",
    "CIP_VECTOR_POOL_SIZE",
    "CIP_RERANK_POOL_SIZE",
    "CIP_DEFAULT_TOP_K",
]


def test_default_settings(monkeypatch):
    for key in SETTINGS_DEFAULTS + ["CIP_DB_PATH", "CIP_CAS_ROOT_DIR", "CIP_VECTOR_DB_PATH"]:
        monkeypatch.delenv(key, raising=False)
    settings = Settings()

    assert settings.db_path.endswith("cip_main.db")
    assert settings.cas_root_dir.endswith("documents")
    assert settings.vector_db_path.endswith("lancedb")
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.reranker_model == "Xenova/ms-marco-MiniLM-L-6-v2"
    assert settings.llm_model == "llama3.2"
    assert settings.fallback_llm_model == "llama3.2"
    assert settings.rrf_k == 60
    assert settings.default_top_k == 10


def test_model_and_tuning_settings_support_env_overrides(monkeypatch):
    monkeypatch.setenv("CIP_EMBEDDING_MODEL", "custom/embedding")
    monkeypatch.setenv("CIP_RERANKER_MODEL", "custom/reranker")
    monkeypatch.setenv("CIP_LLM_MODEL", "mistral")
    monkeypatch.setenv("CIP_FALLBACK_LLM_MODEL", "qwen2.5")
    monkeypatch.setenv("CIP_RRF_K", "42")
    monkeypatch.setenv("CIP_KEYWORD_WEIGHT", "0.7")
    monkeypatch.setenv("CIP_VECTOR_WEIGHT", "1.3")
    monkeypatch.setenv("CIP_VECTOR_POOL_SIZE", "25")
    monkeypatch.setenv("CIP_RERANK_POOL_SIZE", "8")
    monkeypatch.setenv("CIP_DEFAULT_TOP_K", "5")

    settings = Settings()
    assert settings.embedding_model == "custom/embedding"
    assert settings.reranker_model == "custom/reranker"
    assert settings.llm_model == "mistral"
    assert settings.fallback_llm_model == "qwen2.5"
    assert settings.rrf_k == 42
    assert settings.keyword_weight == 0.7
    assert settings.vector_weight == 1.3
    assert settings.vector_pool_size == 25
    assert settings.rerank_pool_size == 8
    assert settings.default_top_k == 5


def test_get_settings_singleton_and_cache_clear():
    a = get_settings()
    b = get_settings()
    assert a is b
    get_settings.cache_clear()
    c = get_settings()
    assert a is not c
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# CAS (Content Addressable Storage)
# ---------------------------------------------------------------------------

def test_cas_storage_and_deduplication(tmp_path: Path):
    cas_manager = CASManager(root_dir=tmp_path)
    content = b"Candidate Intelligence Resume V1"

    file_hash, cas_path = cas_manager.store(content, extension=".pdf")
    expected_hash = hashlib.sha256(content).hexdigest()
    assert file_hash == expected_hash

    expected_path = tmp_path / expected_hash[:2] / expected_hash[2:4] / f"{expected_hash}.pdf"
    assert Path(cas_path) == expected_path
    assert expected_path.exists()
    assert not os.access(expected_path, os.W_OK)

    # Idempotent storage
    file_hash_2, cas_path_2 = cas_manager.store(content, extension=".pdf")
    assert file_hash == file_hash_2
    assert cas_path == cas_path_2


def test_cas_delete_removes_read_only_and_missing_is_noop(tmp_path: Path):
    cas_manager = CASManager(root_dir=tmp_path)
    _, cas_path = cas_manager.store(b"rejected doc", extension=".pdf")
    stored = Path(cas_path)
    assert stored.exists()
    assert not os.access(stored, os.W_OK)

    assert cas_manager.delete(cas_path) is True
    assert not stored.exists()
    assert cas_manager.delete(tmp_path / "aa" / "bb" / "absent.txt") is True


# ---------------------------------------------------------------------------
# Backup Manager
# ---------------------------------------------------------------------------

def test_backup_manager_live_backup_and_sync(tmp_path: Path):
    source_db = tmp_path / "source.db"
    backup_db = tmp_path / "backup.db"
    with sqlite3.connect(source_db) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('dummy data')")
        conn.commit()

    manager = BackupManager()
    manager.perform_live_backup(str(source_db), str(backup_db))

    assert backup_db.exists()
    with sqlite3.connect(backup_db) as conn:
        result = conn.execute("SELECT name FROM test").fetchone()
        assert result[0] == "dummy data"

    source_cas = tmp_path / "source_cas"
    backup_cas = tmp_path / "backup_cas"
    f1 = source_cas / "ab" / "cd"
    f1.mkdir(parents=True)
    (f1 / "abcdef.pdf").write_text("dummy")

    manager.sync_cas_storage(str(source_cas), str(backup_cas))
    assert (backup_cas / "ab" / "cd" / "abcdef.pdf").exists()


def test_backup_manager_manifest_and_lance_count(tmp_path: Path, monkeypatch):
    source_db = tmp_path / "source.db"
    source_db.write_text("dummy sqlite content")
    cas_dir = tmp_path / "cas"
    (cas_dir / "12").mkdir(parents=True)
    (cas_dir / "12" / "12345.txt").write_text("test")

    manager = BackupManager()
    monkeypatch.setattr(manager, "_get_lance_row_count", lambda path: 42)

    manifest = manager.generate_manifest(str(source_db), str(cas_dir), str(tmp_path / "lance"))
    assert "db_sha256" in manifest
    assert manifest["cas_file_count"] == 1
    assert manifest["vector_count"] == 42


def test_lance_row_count_uses_candidate_vectors_table(tmp_path: Path):
    import lancedb
    db_path = str(tmp_path / "lancedb_manifest")
    db = lancedb.connect(db_path)
    tbl = db.create_table("candidate_vectors", schema=CandidateSectionVector)
    tbl.add([{
        "chunk_id": f"chunk_{i}",
        "candidate_id": "cand_1",
        "resume_version_id": "rv1",
        "section_type": "SUMMARY",
        "chunk_text": "sample",
        "vector": [0.0] * 384,
        "start_offset": 0,
        "end_offset": 0,
    } for i in range(3)])

    manager = BackupManager()
    assert manager._get_lance_row_count(db_path) == 3

    empty_dir = tmp_path / "empty_vectors"
    empty_dir.mkdir()
    assert manager._get_lance_row_count(str(empty_dir)) == 0


# ---------------------------------------------------------------------------
# Vector Store (LanceDB)
# ---------------------------------------------------------------------------

def test_lancedb_initialization_and_vector_search(tmp_path: Path):
    db_path = str(tmp_path / "lancedb_test")
    db = get_lancedb_connection(db_path)
    table = db.create_table("candidate_sections", schema=CandidateSectionVector, exist_ok=True)
    assert table.name == "candidate_sections"
    assert "chunk_id" in table.schema.names
    assert "vector" in table.schema.names

    vec_tbl = db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
    vec_tbl.add([{
        "chunk_id": "chunk-0",
        "candidate_id": "cand-0",
        "resume_version_id": "res-0",
        "section_type": "WORK_EXPERIENCE",
        "chunk_text": "Senior Cloud Architect AWS Kubernetes",
        "vector": [1.0] + [0.0] * 383,
        "start_offset": 0,
        "end_offset": 37,
    }])
    results = vec_tbl.search([1.0] + [0.0] * 383).limit(1).to_list()
    assert len(results) == 1
    assert results[0]["candidate_id"] == "cand-0"


# ---------------------------------------------------------------------------
# Index Writer
# ---------------------------------------------------------------------------

class _VectorDBWithDelete:
    def __init__(self):
        self.deleted = []

    def delete_candidate_vectors(self, candidate_id: str):
        self.deleted.append(candidate_id)


class _VectorDBWithFallback:
    def __init__(self):
        self.deleted_preds = []

    def list_tables(self):
        return ["candidate_vectors"]

    def open_table(self, name: str):
        class _T:
            def delete(_self, predicate: str):
                self.deleted_preds.append(predicate)
        return _T()


def test_index_writer_table_checks():
    class DB1:
        def list_tables(self):
            return ["candidate_vectors"]

    class DB2:
        def table_names(self):
            return ["candidate_vectors"]

    class DB3:
        def list_tables(self):
            return []

    class DBError:
        def list_tables(self):
            raise RuntimeError("fail")

    assert _has_candidate_vectors_table(DB1()) is True
    assert _has_candidate_vectors_table(DB2()) is True
    assert _has_candidate_vectors_table(DB3()) is False
    assert _has_candidate_vectors_table(DBError()) is False


def test_index_writer_delete_vectors(db_session: Session):
    vdb1 = _VectorDBWithDelete()
    writer1 = StorageIndexWriter(db_session, vdb1)
    cid = str(uuid.uuid4())
    writer1._delete_vectors(cid)
    assert vdb1.deleted == [cid]

    vdb2 = _VectorDBWithFallback()
    writer2 = StorageIndexWriter(db_session, vdb2)
    malicious_id = 'test"id'
    writer2._delete_vectors(malicious_id)
    assert len(vdb2.deleted_preds) == 1
    assert 'test""id' in vdb2.deleted_preds[0]

    writer_none = StorageIndexWriter(db_session, None)
    writer_none._delete_vectors("some-id")
