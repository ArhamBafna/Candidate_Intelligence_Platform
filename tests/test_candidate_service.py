"""Tests for api/services/candidate_service.py vector indexing.

Covers section-aware reindexing (issue #20):
  - update_vector_index writes chunks labeled with their true resume section
    type into a temporary real LanceDB store.
  - Whole-resume-as-one-SUMMARY-chunk behavior is gone.
  - Delete-then-reindex per candidate is idempotent.

Heavy embedding model is mocked with a deterministic fake.
"""
import lancedb
import pytest

from api.services.candidate_service import CandidateService
from storage.vector_store import CandidateSectionVector


SECTIONED_RESUME = (
    "Jane Doe\nNYC based engineer.\n\n"
    "SUMMARY\n" + ("Builds search platforms. " * 30) + "\n"
    "SKILLS\nPython, SQL, FastAPI, LanceDB, Docker.\n\n"
    "WORK_EXPERIENCE\nSenior Engineer at Acme (2021-2024). " + ("Shipped pipelines. " * 40) + "\n"
    "EDUCATION\nB.Tech Computer Science, State University.\n"
)


@pytest.fixture()
def real_vector_db(tmp_path):
    return lancedb.connect(str(tmp_path / "lancedb_service"))


@pytest.fixture()
def fake_embeddings(monkeypatch):
    def _fake(texts):
        return [[float(len(t) % 97) / 97.0] * 384 for t in texts]

    monkeypatch.setattr(
        "api.services.candidate_service.generate_embeddings", _fake
    )
    return _fake


def _table_rows(vector_db):
    table = vector_db.open_table("candidate_vectors")
    return table.to_arrow().to_pylist()


def test_update_vector_index_writes_section_typed_chunks(real_vector_db, fake_embeddings):
    CandidateService.update_vector_index(
        real_vector_db, "cand-sec", SECTIONED_RESUME, "rv-1"
    )

    rows = _table_rows(real_vector_db)
    assert len(rows) > 0

    section_types = {row["section_type"] for row in rows}
    assert {"SUMMARY", "SKILLS", "WORK_EXPERIENCE", "EDUCATION"} <= section_types

    for row in rows:
        if "FastAPI" in row["chunk_text"]:
            assert row["section_type"] == "SKILLS"


def test_update_vector_index_no_whole_resume_summary_chunk(real_vector_db, fake_embeddings):
    CandidateService.update_vector_index(
        real_vector_db, "cand-mix", SECTIONED_RESUME, "rv-1"
    )

    rows = _table_rows(real_vector_db)
    assert len({row["section_type"] for row in rows}) > 1


def test_update_vector_index_idempotent_per_candidate(real_vector_db, fake_embeddings):
    CandidateService.update_vector_index(
        real_vector_db, "cand-idem", SECTIONED_RESUME, "rv-1"
    )
    first_rows = _table_rows(real_vector_db)

    CandidateService.update_vector_index(
        real_vector_db, "cand-idem", SECTIONED_RESUME, "rv-1"
    )
    second_rows = _table_rows(real_vector_db)

    assert len(second_rows) == len(first_rows)
    old_ids = {row["chunk_id"] for row in first_rows}
    new_ids = {row["chunk_id"] for row in second_rows}
    assert not (old_ids & new_ids)
    assert all(row["candidate_id"] == "cand-idem" for row in second_rows)


def test_update_vector_index_keeps_other_candidates_intact(real_vector_db, fake_embeddings):
    CandidateService.update_vector_index(
        real_vector_db, "cand-a", SECTIONED_RESUME, "rv-a"
    )
    CandidateService.update_vector_index(
        real_vector_db, "cand-b", SECTIONED_RESUME, "rv-b"
    )
    rows = _table_rows(real_vector_db)

    ids = {row["candidate_id"] for row in rows}
    assert ids == {"cand-a", "cand-b"}
