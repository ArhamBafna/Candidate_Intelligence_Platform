import uuid

import pytest
from sqlalchemy.orm import Session

from storage.db_models import Candidate
from storage.index_writer import StorageIndexWriter, _has_candidate_vectors_table


class VectorDBWithDeleteCandidateVectors:
    """Vector DB that has delete_candidate_vectors method (modern API)."""
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_candidate_vectors(self, candidate_id: str) -> None:
        self.deleted.append(candidate_id)


class VectorDBWithTableFallback:
    """Vector DB without delete_candidate_vectors — falls back to table.delete()."""
    def __init__(self) -> None:
        self.deleted_preds: list[str] = []

    def list_tables(self) -> list[str]:
        return ["candidate_vectors"]

    def open_table(self, name: str) -> "MockTable":
        t = MockTable()
        t._parent = self
        return t


class MockTable:
    def __init__(self) -> None:
        self._parent: VectorDBWithTableFallback | None = None

    def delete(self, predicate: str) -> None:
        if self._parent is not None:
            self._parent.deleted_preds.append(predicate)


class VectorDBNoTable:
    """Vector DB with no candidate_vectors table — _delete_vectors is a no-op."""
    def list_tables(self) -> list[str]:
        return []


# --- _has_candidate_vectors_table ---

def test_has_candidate_vectors_table_with_list_tables():
    class FakeDB:
        def list_tables(self) -> list[str]:
            return ["candidate_vectors", "other"]
    assert _has_candidate_vectors_table(FakeDB()) is True


def test_has_candidate_vectors_table_with_table_names():
    class FakeDB:
        def table_names(self) -> list[str]:
            return ["candidate_vectors"]
    assert _has_candidate_vectors_table(FakeDB()) is True


def test_has_candidate_vectors_table_missing():
    assert _has_candidate_vectors_table(VectorDBNoTable()) is False


def test_has_candidate_vectors_table_exception():
    class BadDB:
        def list_tables(self) -> list[str]:
            raise RuntimeError("db error")
    assert _has_candidate_vectors_table(BadDB()) is False


# --- _delete_vectors ---

def test_delete_vectors_uses_delete_candidate_vectors(db_session: Session):
    vdb = VectorDBWithDeleteCandidateVectors()
    writer = StorageIndexWriter(db_session, vdb)
    cid = str(uuid.uuid4())
    writer._delete_vectors(cid)
    assert vdb.deleted == [cid]


def test_delete_vectors_falls_back_to_table_delete(db_session: Session):
    vdb = VectorDBWithTableFallback()
    writer = StorageIndexWriter(db_session, vdb)
    cid = str(uuid.uuid4())
    writer._delete_vectors(cid)
    assert len(vdb.deleted_preds) == 1
    assert cid in vdb.deleted_preds[0]


def test_delete_vectors_escapes_quotes_in_candidate_id(db_session: Session):
    vdb = VectorDBWithTableFallback()
    writer = StorageIndexWriter(db_session, vdb)
    malicious_id = 'test"id'
    writer._delete_vectors(malicious_id)
    assert len(vdb.deleted_preds) == 1
    pred = vdb.deleted_preds[0]
    assert '""' in pred
    assert 'test""id' in pred


def test_delete_vectors_noop_when_vector_db_is_none(db_session: Session):
    writer = StorageIndexWriter(db_session, None)
    writer._delete_vectors(str(uuid.uuid4()))


def test_delete_vectors_noop_when_no_candidate_vectors_table(db_session: Session):
    vdb = VectorDBNoTable()
    writer = StorageIndexWriter(db_session, vdb)
    writer._delete_vectors(str(uuid.uuid4()))
