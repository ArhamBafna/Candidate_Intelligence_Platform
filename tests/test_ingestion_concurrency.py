"""Regression: parallel ingest_file must not fail with 'database is locked'.

Reproduces the /upload-stream failure mode: N concurrent pipelines sharing one
WAL SQLite file. The pipeline historically opened its write transaction at
db.flush() and held it through embedding generation, starving parallel writers
past PRAGMA busy_timeout. Embeddings are mocked with a sleep longer than the
engine's busy_timeout to force the contention deterministically.
"""
import threading
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from candidate_intelligence_platform.ingestion.intake import (
    IntakeSource,
    IntakeStatus,
    TimelineMode,
    ingest_file,
)
from config.settings import Settings
from conftest import MockVectorStore
from storage.db_models import Base, Candidate


RESUME_TEMPLATE = """
{name}
Analyst
{email} | 555-123-4567

Summary:
Experienced analyst with 8 years of experience building reports.

Professional Experience:
Analyst at Acme Corp (2020 - Present)

Education:
BS in Computer Science
"""


def make_engine(db_file: str) -> Any:
    """Same pragma set as config.database.get_engine but short busy_timeout."""
    engine = create_engine(f"sqlite:///{db_file}")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.execute("PRAGMA page_size=4096;")
        cursor.execute("PRAGMA cache_size=-64000;")
        cursor.execute("PRAGMA busy_timeout=300;")
        cursor.close()

    return engine


@pytest.fixture
def concurrency_env(tmp_path: Any, monkeypatch: Any) -> Dict[str, Any]:
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.deterministic_ner.extract_facts",
        lambda text: [],
    )

    def fake_extract(text: str, **kwargs: Any) -> Dict[str, Any]:
        idx = fake_extract.call_index  # type: ignore[attr-defined]
        fake_extract.call_index += 1  # type: ignore[attr-defined]
        return {
            "first_name": f"Jane{idx}",
            "last_name": "Doe",
            "primary_email": f"jane{idx}@example.com",
            "primary_phone": "555-123-4567",
            "current_title": "Analyst",
            "warnings": [],
            "used_ai_fallback": False,
        }

    fake_extract.call_index = 0  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        fake_extract,
    )

    embed_calls: List[int] = []

    def slow_embeddings(texts: List[str]) -> List[List[float]]:
        embed_calls.append(len(texts))
        # Simulates FastEmbed model load: holds the caller for longer than
        # the engine busy_timeout (300ms) while its write txn is open.
        import time

        time.sleep(1.0)
        return [[0.0] * 4 for _ in texts]

    monkeypatch.setattr(
        "api.services.candidate_service.generate_embeddings", slow_embeddings
    )

    db_file = str(tmp_path / "conc.db")
    engine = make_engine(db_file)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS candidate_fts USING fts5(
                candidate_id UNINDEXED, full_name, current_title,
                current_company, resume_content,
                tokenize = 'porter unicode61'
            );
        """))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    settings = Settings(
        db_path=db_file,
        cas_root_dir=str(tmp_path / "cas"),
        vector_db_path=str(tmp_path / "vector"),
    )

    yield {"SessionLocal": SessionLocal, "settings": settings, "embed_calls": embed_calls}
    engine.dispose()


def test_parallel_ingest_no_database_locked(concurrency_env: Dict[str, Any]) -> None:
    env = concurrency_env
    SessionLocal = env["SessionLocal"]
    settings = env["settings"]
    n_threads = 3
    barrier = threading.Barrier(n_threads)

    outcomes: Dict[str, List[Any]] = {"ok": [], "locked": [], "other": []}
    lock = threading.Lock()

    def worker(i: int) -> None:
        content = RESUME_TEMPLATE.format(
            name=f"Jane{i} Doe", email=f"jane{i}@example.com"
        ).encode("utf-8")
        db: Session = SessionLocal()
        try:
            barrier.wait(timeout=10)
            result = ingest_file(
                content=content,
                filename=f"resume{i}.txt",
                db=db,
                cas_mgr=CAS_MANAGER_SHIM(settings),
                vector_db=MockVectorStore(),
                settings=settings,
                source=IntakeSource.UPLOAD_STREAM,
                timeline_mode=TimelineMode.LEDGER,
            )
            db.commit()
            with lock:
                outcomes["ok"].append(result.status)
        except Exception as e:  # noqa: BLE001
            with lock:
                if "database is locked" in str(e):
                    outcomes["locked"].append(type(e).__name__)
                else:
                    outcomes["other"].append(f"{type(e).__name__}: {e}")
        finally:
            db.close()

    from storage.cas import CASManager

    def CAS_MANAGER_SHIM(s: Settings) -> Any:  # noqa: N802
        return CASManager(s.cas_root_dir)

    threads = [
        threading.Thread(target=worker, args=(i,), name=f"ingest-{i}")
        for i in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not outcomes["other"], f"Unexpected errors: {outcomes['other']}"
    assert not outcomes["locked"], (
        f"{len(outcomes['locked'])} of {n_threads} ingests failed with "
        f"'database is locked' (write txn held across embedding generation)"
    )
    assert sorted(outcomes["ok"]) == [IntakeStatus.INGESTED] * n_threads

    check_db: Session = SessionLocal()
    try:
        assert check_db.query(Candidate).count() == n_threads
    finally:
        check_db.close()
