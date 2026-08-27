"""Golden-set evaluation harness (issue #21).

Opt-in: run with `uv run pytest -m evaluation --run-eval`.
Builds a temporary real store (SQLite WAL + FTS5, LanceDB), ingests the
fixture resumes with REAL local embedding models, runs the full hybrid
search pipeline over the golden queries and reports Recall@10 / MRR
against the recorded baseline.

The default fast suite skips this module entirely (see conftest.py).
"""
import json
import os
from pathlib import Path

import pytest

from config.database import get_engine
from storage.db_models import Base, Candidate, ResumeVersion, init_db
from storage.index_writer import StorageIndexWriter
from candidate_intelligence_platform.search.hybrid_searcher import search_candidates
from sqlalchemy.orm import sessionmaker

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_SET_PATH = FIXTURES_DIR / "golden_search_set.json"
BASELINE_PATH = FIXTURES_DIR / "golden_baseline.json"

TOP_K = 10


def _load_golden_set() -> dict:
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def golden_store(tmp_path_factory):
    """Temporary real store ingested once per module with local models."""
    root = tmp_path_factory.mktemp("golden_eval")
    engine = get_engine(f"sqlite:///{root / 'cip_golden.db'}")
    init_db(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import lancedb
    from storage.vector_store import CandidateSectionVector

    vector_db = lancedb.connect(str(root / "lancedb_golden"))

    golden = _load_golden_set()
    db = TestingSession()
    try:
        for entry in golden["resumes"]:
            cid = entry["id"]
            candidate = Candidate(
                id=cid,
                first_name=entry["first_name"],
                last_name=entry["last_name"],
                current_city=entry["current_city"],
                current_title=entry["current_title"],
                total_yoe=float(entry["total_yoe"]),
                availability_status="ACTIVE",
            )
            rv = ResumeVersion(
                id=f"{cid}_rv1",
                candidate_id=cid,
                cas_file_hash="golden-fixture",
                original_filename="fixture.txt",
                file_type="txt",
                raw_text=entry["resume_text"],
                layout_metadata={},
                is_primary=True,
            )
            db.add(candidate)
            db.add(rv)
            db.commit()

            writer = StorageIndexWriter(db, vector_db)
            writer.write_candidate_indices(candidate, rv, entry["resume_text"])
            db.commit()
    finally:
        db.close()

    yield engine, vector_db
    engine.dispose()


def _run_query(query: str, engine, vector_db) -> list[str]:
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    try:
        ranked_ids: list[str] = []
        for stage, progress, message, data in search_candidates(query, db, vector_db):
            if stage == "COMPLETE":
                ranked_ids = [item["candidate_id"] for item in data]
        return ranked_ids
    finally:
        db.close()


def _metrics(golden: dict, engine, vector_db) -> tuple[float, float]:
    recalls: list[float] = []
    reciprocals: list[float] = []

    for search in golden["searches"]:
        ranked = _run_query(search["query"], engine, vector_db)
        top = ranked[:TOP_K]
        expected = set(search["expected"])

        hits = expected.intersection(top)
        recalls.append(len(hits) / len(expected) if expected else 1.0)

        first_rank = next((i + 1 for i, cid in enumerate(ranked) if cid in expected), 0)
        reciprocals.append(1.0 / first_rank if first_rank else 0.0)

    recall_at_10 = sum(recalls) / len(recalls) if recalls else 0.0
    mrr = sum(reciprocals) / len(reciprocals) if reciprocals else 0.0
    return recall_at_10, mrr


@pytest.mark.evaluation
def test_golden_set_recall_and_mrr_meets_baseline(golden_store, capsys):
    engine, vector_db = golden_store
    golden = _load_golden_set()

    assert len(golden["searches"]) >= 20
    assert len(golden["resumes"]) >= 10

    recall_at_10, mrr = _metrics(golden, engine, vector_db)

    with capsys.disabled():
        print(
            f"\n[golden-eval] Recall@10={recall_at_10:.4f} MRR={mrr:.4f} "
            f"over {len(golden['searches'])} searches"
        )

    assert BASELINE_PATH.exists(), (
        "Missing tests/fixtures/golden_baseline.json; generate it by running "
        "`uv run pytest tests/test_golden_eval.py -m evaluation --run-eval -s --update-baseline`"
    )
    with open(BASELINE_PATH, "r", encoding="utf-8") as fh:
        baseline = json.load(fh)

    tolerance = float(baseline.get("tolerance", 0.2))
    assert recall_at_10 >= float(baseline["recall_at_10"]) - tolerance, (
        f"Recall@10 {recall_at_10:.4f} regressed below baseline "
        f"{baseline['recall_at_10']:.4f} (tolerance {tolerance})"
    )
    assert mrr >= float(baseline["mrr"]) - tolerance, (
        f"MRR {mrr:.4f} regressed below baseline {baseline['mrr']:.4f} "
        f"(tolerance {tolerance})"
    )


@pytest.mark.evaluation
def test_golden_set_update_baseline(golden_store, request):
    """Regenerate the recorded baseline: pytest --run-eval --update-baseline."""
    if not request.config.getoption("--update-baseline"):
        pytest.skip("Add --update-baseline to rewrite the baseline file.")

    engine, vector_db = golden_store
    golden = _load_golden_set()
    recall_at_10, mrr = _metrics(golden, engine, vector_db)

    payload = {
        "version": golden["version"],
        "recall_at_10": round(recall_at_10, 4),
        "mrr": round(mrr, 4),
        "tolerance": 0.2,
        "num_searches": len(golden["searches"]),
    }
    with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    print(f"[gold-baseline] wrote {payload}")
