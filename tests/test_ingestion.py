"""Consolidated test suite for ingestion, chunking, entity resolution, CRM lifecycle, and bulk ingestion.

Covers:
- Text chunking & resume section-aware splitting
- Entity resolution (Tier 1 exact match & Tier 2 probabilistic scoring)
- Core intake pipeline (dedup, CAS storage, error handling, rollback, FTS updates)
- Concurrency & SQLite WAL locking under parallel ingestion
- Candidate state machine transitions & timeline ledger auditing
- Bulk ingestion CLI runner, reports, and summary generation
"""
import hashlib
import importlib
import json
import os
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

import candidate_intelligence_platform.ingestion.intake as intake_module
from candidate_intelligence_platform.ingestion.intake import (
    IntakeProgress,
    IntakeResult,
    IntakeSource,
    IntakeStatus,
    TimelineMode,
    classify_document,
    ingest_file,
    reprocess_text,
)
from config.settings import Settings
from conftest import MockVectorStore
from crm.state_machine import CandidateStateMachine, InvalidStateTransition, TransitionContext
from crm.timeline_ledger import TimelineLedger
from ingestion.chunker import TextChunk, chunk_document, chunk_resume, split_resume_sections
from ingestion.entity_resolution import (
    CandidateIdentifiers,
    ResolutionAction,
    ResolutionResult,
    resolve,
)
from ingestion.parsers.models import ParsedDocument
from storage.cas import CASManager
from storage.db_models import (
    Base,
    Candidate,
    CandidateTimelineEvent,
    EntityResolutionAudit,
    ResumeVersion,
)

# Dynamically import bulk_ingest from bulk-ingestions
_bulk_ingest_path = Path(__file__).resolve().parent.parent / "bulk-ingestions" / "bulk_ingest.py"
_spec = importlib.util.spec_from_file_location("bulk_ingest", str(_bulk_ingest_path))
bulk_ingest_module = importlib.util.module_from_spec(_spec)
sys.modules["bulk_ingest"] = bulk_ingest_module
_spec.loader.exec_module(bulk_ingest_module)
run_bulk_ingest = bulk_ingest_module.run_bulk_ingest
get_file_hash = bulk_ingest_module.get_file_hash
process_single_file = bulk_ingest_module.process_single_file
generate_markdown_summary = bulk_ingest_module.generate_markdown_summary


# ---------------------------------------------------------------------------
# Test Data & Helpers
# ---------------------------------------------------------------------------

RESUME_TEXT = """
Jane Candidate
Senior Python Developer
jane.doe@example.com | 555-123-4567

Summary:
Experienced Python software engineer with 8 years of experience building APIs and data pipelines.

Technical Skills:
Python, FastAPI, Docker, PostgreSQL, AWS

Professional Experience:
Senior Developer at Acme Corp (2020 - Present)
- Developed microservices

Education:
BS in Computer Science
"""

CONTRACT_TEXT = "This Referral Agreement is entered into by and between the parties hereto. Governing law and indemnification terms apply."

EXTRACTED_JANE: Dict[str, Any] = {
    "first_name": "Jane",
    "last_name": "Doe",
    "primary_email": "jane.doe@example.com",
    "primary_phone": "555-123-4567",
    "current_title": "Engineer",
    "warnings": [],
    "used_ai_fallback": False,
}

SECTIONED_RESUME = """Arham Bafna
Backend engineer based in NYC.

SUMMARY
Five years building data platforms and search systems.

SKILLS
Python, SQL, FastAPI, LanceDB, Docker.

WORK_EXPERIENCE
Senior Engineer at Acme (2021-2024). Built hybrid search pipelines.
Engineer at Globex (2018-2021). Shipped ETL tooling.

EDUCATION
B.Tech in Computer Science, State University.
"""


def _make_doc(text: str) -> ParsedDocument:
    return ParsedDocument(text=text, pages=1, metadata={"source_path": "test.pdf"})


def _make_candidate_id(
    candidate_id: str = "cand-1",
    email: str | None = None,
    phone: str | None = None,
    linkedin_url: str | None = None,
    full_name: str = "",
) -> CandidateIdentifiers:
    return CandidateIdentifiers(
        candidate_id=candidate_id,
        email=email,
        phone=phone,
        linkedin_url=linkedin_url,
        full_name=full_name,
    )


def make_settings(tmp_path: Any, **overrides: Any) -> Settings:
    return Settings(
        db_path=str(tmp_path / "s.db"),
        cas_root_dir=str(tmp_path / "cas"),
        vector_db_path=str(tmp_path / "vector"),
        **overrides,
    )


def _cas_file_count(cas_root_dir: str) -> int:
    root = Path(cas_root_dir)
    return sum(1 for p in root.rglob("*") if p.is_file()) if root.exists() else 0


# ---------------------------------------------------------------------------
# Section 1: Text Chunker & Resume Section Splitting
# ---------------------------------------------------------------------------

def test_chunk_document_returns_list_of_text_chunks() -> None:
    doc = _make_doc("A" * 600)
    result = chunk_document(doc, candidate_id="cand-1", section_name="WORK_EXPERIENCE")
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(c, TextChunk) for c in result)


def test_chunk_ids_are_unique_uuids() -> None:
    doc = _make_doc("B" * 1200)
    result = chunk_document(doc, candidate_id="cand-1", section_name="SKILLS")
    ids = [c.chunk_id for c in result]
    for chunk_id in ids:
        uuid.UUID(chunk_id, version=4)
    assert len(ids) == len(set(ids))


def test_chunk_size_not_exceeded() -> None:
    chunk_size = 200
    doc = _make_doc("C " * 500)
    result = chunk_document(doc, candidate_id="cand-1", section_name="EDUCATION", chunk_size=chunk_size)
    for chunk in result:
        assert len(chunk.text) <= chunk_size


def test_chunk_carries_context_fields() -> None:
    doc = _make_doc("D" * 600)
    cid = "candidate-abc-123"
    result = chunk_document(doc, candidate_id=cid, section_name="SUMMARY")
    for chunk in result:
        assert chunk.candidate_id == cid
        assert chunk.section_name == "SUMMARY"


def test_chunk_offsets_span_source_text() -> None:
    source = "Hello World " * 100
    doc = _make_doc(source)
    result = chunk_document(doc, candidate_id="cand-1", section_name="WORK_EXPERIENCE", chunk_size=200, chunk_overlap=20)
    for chunk in result:
        assert chunk.start_offset >= 0
        assert chunk.end_offset <= len(source)
        assert chunk.start_offset < chunk.end_offset
        assert source[chunk.start_offset:chunk.end_offset].strip()


def test_short_document_yields_single_chunk() -> None:
    doc = _make_doc("Short resume text.")
    result = chunk_document(doc, candidate_id="cand-1", section_name="SUMMARY", chunk_size=512)
    assert len(result) == 1


def test_empty_document_yields_empty_list() -> None:
    assert chunk_document(_make_doc(""), candidate_id="cand-1", section_name="SUMMARY") == []


def test_split_resume_sections_detects_true_types() -> None:
    sections = split_resume_sections(SECTIONED_RESUME)
    names = [name for name, _ in sections]
    assert names == ["SUMMARY", "SKILLS", "WORK_EXPERIENCE", "EDUCATION"]
    by_name = dict(sections)
    assert "data platforms" in by_name["SUMMARY"]
    assert "FastAPI" in by_name["SKILLS"]
    assert "Acme" in by_name["WORK_EXPERIENCE"]
    assert "State University" in by_name["EDUCATION"]


def test_split_resume_sections_preamble_becomes_summary() -> None:
    text_content = "Jane Doe\nContact line.\nSKILLS\nPython"
    sections = split_resume_sections(text_content)
    assert sections[0][0] == "SUMMARY"
    assert "Jane Doe" in sections[0][1]


def test_split_resume_sections_no_headers_single_summary() -> None:
    sections = split_resume_sections("Plain resume with no headers at all.\nJust prose.")
    assert len(sections) == 1
    assert sections[0][0] == "SUMMARY"


def test_split_resume_sections_case_insensitive_and_colon() -> None:
    sections = split_resume_sections("TECHNICAL SKILLS:\nPython\nEducation\nSome school")
    assert [name for name, _ in sections] == ["SKILLS", "EDUCATION"]


def test_chunk_resume_labels_chunks_with_section_types() -> None:
    chunks = chunk_resume(_make_doc(SECTIONED_RESUME), candidate_id="cand-1")
    assert len(chunks) > 0
    labeled = {c.section_name for c in chunks}
    assert {"SUMMARY", "SKILLS", "WORK_EXPERIENCE", "EDUCATION"} <= labeled
    for chunk in chunks:
        if "FastAPI" in chunk.text:
            assert chunk.section_name == "SKILLS"


def test_chunk_resume_respects_chunk_size_per_section() -> None:
    doc = _make_doc("SKILLS\n" + ("python rust go " * 200))
    chunks = chunk_resume(doc, candidate_id="cand-1", chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 100
        assert chunk.section_name == "SKILLS"


def test_chunk_resume_empty_document_yields_empty_list() -> None:
    assert chunk_resume(_make_doc(""), candidate_id="cand-1") == []


# ---------------------------------------------------------------------------
# Section 2: Entity Resolution
# ---------------------------------------------------------------------------

def test_tier1_email_match_returns_merge() -> None:
    incoming = _make_candidate_id("new", email="alice@example.com")
    existing = [_make_candidate_id("c1", email="bob@example.com"), _make_candidate_id("c2", email="alice@example.com")]
    res = resolve(incoming, existing)
    assert res.action == ResolutionAction.MERGE
    assert res.matched_id == "c2"
    assert res.tier == 1
    assert res.confidence == 1.0


def test_tier1_phone_match_returns_merge() -> None:
    incoming = _make_candidate_id("new", phone="+1-555-0199")
    existing = [_make_candidate_id("c1", phone="+1-555-0199")]
    res = resolve(incoming, existing)
    assert res.action == ResolutionAction.MERGE
    assert res.matched_id == "c1"
    assert res.tier == 1


def test_tier1_linkedin_match_returns_merge() -> None:
    incoming = _make_candidate_id("new", linkedin_url="https://linkedin.com/in/alice-dev")
    existing = [_make_candidate_id("c1", linkedin_url="https://linkedin.com/in/alice-dev")]
    res = resolve(incoming, existing)
    assert res.action == ResolutionAction.MERGE
    assert res.matched_id == "c1"


def test_tier2_exact_name_match_returns_merge() -> None:
    incoming = _make_candidate_id("new", full_name="Alice Smith")
    existing = [_make_candidate_id("c1", full_name="Alice Smith")]
    res = resolve(incoming, existing)
    assert res.action == ResolutionAction.MERGE
    assert res.matched_id == "c1"
    assert res.tier == 2


def test_tier2_dissimilar_name_returns_new() -> None:
    incoming = _make_candidate_id("new", full_name="Alexander Hamilton")
    existing = [_make_candidate_id("c1", full_name="Zoe Washington")]
    res = resolve(incoming, existing)
    assert res.action == ResolutionAction.NEW
    assert res.matched_id is None


def test_empty_existing_returns_new() -> None:
    incoming = _make_candidate_id("new", email="first@example.com", full_name="First Candidate")
    res = resolve(incoming, [])
    assert res.action == ResolutionAction.NEW
    assert res.matched_id is None


def test_incoming_with_no_identifiers_returns_new() -> None:
    incoming = _make_candidate_id("new")
    existing = [_make_candidate_id("c1", email="a@example.com", full_name="Alice")]
    res = resolve(incoming, existing)
    assert res.action == ResolutionAction.NEW


# ---------------------------------------------------------------------------
# Section 3: Core Intake Orchestration
# ---------------------------------------------------------------------------

@pytest.fixture
def intake_env(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.deterministic_ner.extract_facts",
        lambda text: [],
    )
    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        lambda text, **kwargs: dict(EXTRACTED_JANE),
    )
    monkeypatch.setattr(
        "candidate_intelligence_platform.intelligence.embeddings.generate_embeddings",
        lambda texts: [[0.0] * 4 for _ in texts],
    )
    settings = make_settings(tmp_path)
    cas_mgr = CASManager(settings.cas_root_dir)
    vector_db = MockVectorStore()
    return {"settings": settings, "cas_mgr": cas_mgr, "vector_db": vector_db}


def test_duplicate_checked_before_cas_store(db_session: Session, intake_env: Dict[str, Any]) -> None:
    env = intake_env
    res1 = ingest_file(
        content=RESUME_TEXT.encode(),
        filename="jane.txt",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert res1.status == IntakeStatus.INGESTED

    res2 = ingest_file(
        content=RESUME_TEXT.encode(),
        filename="jane.txt",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    assert res2.status == IntakeStatus.SKIPPED_DUPLICATE
    assert res2.candidate_id == res1.candidate_id


def test_non_resume_persists_nothing(db_session: Session, intake_env: Dict[str, Any]) -> None:
    env = intake_env
    res = ingest_file(
        content=CONTRACT_TEXT.encode(),
        filename="contract.pdf",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    assert res.status == IntakeStatus.SKIPPED_NON_RESUME
    assert db_session.query(Candidate).count() == 0
    assert db_session.query(ResumeVersion).count() == 0


def test_merge_demotes_old_primary_version(db_session: Session, intake_env: Dict[str, Any]) -> None:
    env = intake_env
    existing_id = str(uuid.uuid4())
    existing = Candidate(id=existing_id, first_name="Jane", last_name="Doe", primary_email="old@example.com")
    old_rv = ResumeVersion(
        id=str(uuid.uuid4()), candidate_id=existing_id, cas_file_hash="oldhash",
        original_filename="old.txt", file_type="TXT", raw_text="old", layout_metadata={}, is_primary=True,
    )
    db_session.add_all([existing, old_rv])
    db_session.commit()

    res = ingest_file(
        content=RESUME_TEXT.encode("utf-8"),
        filename="resume.txt",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert res.status == IntakeStatus.MERGED
    assert res.candidate_id == existing_id
    assert db_session.query(Candidate).count() == 1
    db_session.refresh(old_rv)
    assert old_rv.is_primary is False
    new_rv = db_session.query(ResumeVersion).filter(ResumeVersion.id != old_rv.id).first()
    assert new_rv is not None and new_rv.is_primary is True


def test_review_creates_audit_row(db_session: Session, intake_env: Dict[str, Any], tmp_path: Any) -> None:
    env = intake_env
    lookalike_id = str(uuid.uuid4())
    db_session.add(Candidate(id=lookalike_id, first_name="Jon", last_name="Doee"))
    db_session.commit()

    settings = make_settings(tmp_path, entity_res_auto_merge_threshold=1.01, entity_res_review_threshold=0.70)
    res = ingest_file(
        content=RESUME_TEXT.encode("utf-8"),
        filename="resume.txt",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=settings,
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert res.status == IntakeStatus.INGESTED
    assert res.resolution_action.value == "REVIEW"
    assert res.matched_candidate_id == lookalike_id
    assert res.candidate_id != lookalike_id

    audit = db_session.query(EntityResolutionAudit).one()
    assert audit.resolution_type == "REVIEW"
    assert audit.primary_candidate_id == res.candidate_id
    assert audit.merged_candidate_id == lookalike_id


def test_classifier_rejection_purges_cas_file(db_session: Session, intake_env: Dict[str, Any]) -> None:
    env = intake_env
    res = ingest_file(
        content=CONTRACT_TEXT.encode(),
        filename="contract.pdf",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    assert res.status == IntakeStatus.SKIPPED_NON_RESUME
    assert _cas_file_count(env["settings"].cas_root_dir) == 0


def test_successful_ingest_keeps_exactly_one_cas_file(db_session: Session, intake_env: Dict[str, Any]) -> None:
    env = intake_env
    res = ingest_file(
        content=RESUME_TEXT.encode(),
        filename="jane.txt",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert res.status == IntakeStatus.INGESTED
    assert _cas_file_count(env["settings"].cas_root_dir) == 1


def test_vector_failure_yields_partial(db_session: Session, intake_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    env = intake_env
    from storage.index_writer import StorageIndexWriter

    monkeypatch.setattr(StorageIndexWriter, "_update_vectors_with_precomputed", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    res = ingest_file(
        content=RESUME_TEXT.encode(),
        filename="jane.txt",
        db=db_session,
        cas_mgr=env["cas_mgr"],
        vector_db=env["vector_db"],
        settings=env["settings"],
        source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert res.status == IntakeStatus.PARTIAL
    assert db_session.query(Candidate).count() == 1


# ---------------------------------------------------------------------------
# Section 4: Concurrency & Lock-Free WAL Execution
# ---------------------------------------------------------------------------

def test_parallel_ingest_no_database_locked(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = str(tmp_path / "conc.db")
    engine = create_engine(f"sqlite:///{db_file}")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=50;")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS candidate_fts USING fts5(
                candidate_id UNINDEXED, full_name, current_title,
                current_company, resume_content, tokenize = 'porter unicode61'
            );
        """))

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    settings = Settings(db_path=db_file, cas_root_dir=str(tmp_path / "cas"), vector_db_path=str(tmp_path / "vec"))

    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.deterministic_ner.extract_facts",
        lambda text: [],
    )

    idx_lock = threading.Lock()
    call_idx = [0]

    def fake_extract_concurrent(text: str, **kwargs: Any) -> Dict[str, Any]:
        with idx_lock:
            cur = call_idx[0]
            call_idx[0] += 1
        return {
            "first_name": f"Jane{cur}",
            "last_name": "Doe",
            "primary_email": f"jane{cur}@example.com",
            "primary_phone": f"555-123-000{cur}",
            "current_title": "Analyst",
            "warnings": [],
            "used_ai_fallback": False,
        }

    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        fake_extract_concurrent,
    )

    def fast_embeddings(texts: List[str]) -> List[List[float]]:
        import time
        time.sleep(0.08)
        return [[0.0] * 4 for _ in texts]

    monkeypatch.setattr("candidate_intelligence_platform.intelligence.embeddings.generate_embeddings", fast_embeddings)

    n_threads = 3
    barrier = threading.Barrier(n_threads)
    outcomes: Dict[str, List[Any]] = {"ok": [], "locked": [], "other": []}
    lock = threading.Lock()

    def worker(i: int) -> None:
        content = RESUME_TEXT.replace("Jane", f"Jane{i}").replace("jane.doe", f"jane{i}.doe").encode("utf-8")
        db: Session = SessionLocal()
        try:
            barrier.wait(timeout=10)
            res = ingest_file(
                content=content,
                filename=f"resume{i}.txt",
                db=db,
                cas_mgr=CASManager(settings.cas_root_dir),
                vector_db=MockVectorStore(),
                settings=settings,
                source=IntakeSource.UPLOAD_STREAM,
                timeline_mode=TimelineMode.LEDGER,
            )
            db.commit()
            with lock:
                outcomes["ok"].append(res.status)
        except Exception as e:
            with lock:
                if "database is locked" in str(e):
                    outcomes["locked"].append(type(e).__name__)
                else:
                    outcomes["other"].append(f"{type(e).__name__}: {e}")
        finally:
            db.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not outcomes["other"]
    assert not outcomes["locked"]
    assert len(outcomes["ok"]) == n_threads
    engine.dispose()


# ---------------------------------------------------------------------------
# Section 5: CRM State Machine & Timeline Ledger
# ---------------------------------------------------------------------------

def test_transition_state_success(db_session: Session) -> None:
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(id=candidate_id, first_name="Test", last_name="State", availability_status="ACTIVE")
    db_session.add(candidate)
    db_session.commit()

    sm = CandidateStateMachine()
    context = TransitionContext(
        session=db_session,
        candidate_id=candidate_id,
        new_status="PLACED",
        recruiter_name="recruiter_bob",
        reason="Offer accepted",
    )
    sm.transition_state(context)
    db_session.commit()

    db_session.refresh(candidate)
    assert candidate.availability_status == "PLACED"

    events = db_session.query(CandidateTimelineEvent).filter_by(candidate_id=candidate_id).all()
    assert len(events) == 1
    assert events[0].event_type == "STAGE_CHANGED"
    assert events[0].event_metadata["to_status"] == "PLACED"


def test_invalid_state_transition(db_session: Session) -> None:
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(id=candidate_id, first_name="Test", last_name="State", availability_status="ACTIVE")
    db_session.add(candidate)
    db_session.commit()

    sm = CandidateStateMachine()
    with pytest.raises(InvalidStateTransition):
        context = TransitionContext(
            session=db_session,
            candidate_id=candidate_id,
            new_status="UNKNOWN_STATUS",
            recruiter_name="recruiter_bob",
        )
        sm.transition_state(context)


def test_log_event_and_get_timeline(db_session: Session) -> None:
    candidate_id = str(uuid.uuid4())
    db_session.add(Candidate(id=candidate_id, first_name="Test", last_name="User", primary_email="u@example.com"))
    db_session.commit()

    ledger = TimelineLedger()
    ledger.log_event(
        session=db_session,
        candidate_id=candidate_id,
        event_type="STAGE_CHANGED",
        title="Moved to Interview",
        description="Candidate passed screen",
        metadata={"from": "NEW", "to": "INTERVIEW"},
        created_by="recruiter_jane",
    )
    db_session.commit()

    events = ledger.get_events(session=db_session, candidate_id=candidate_id)
    assert len(events) == 1
    assert events[0].title == "Moved to Interview"


def test_events_returned_in_descending_order(db_session: Session) -> None:
    candidate_id = str(uuid.uuid4())
    db_session.add(Candidate(id=candidate_id, first_name="Test2", last_name="User2", primary_email="u2@example.com"))
    db_session.commit()

    ledger = TimelineLedger()
    now = datetime.now(timezone.utc)
    ledger.log_event(db_session, candidate_id, "RESUME_INGESTED", "Ingested", None, {}, "system", created_at=now - timedelta(minutes=5))
    ledger.log_event(db_session, candidate_id, "NOTE_ADDED", "Note", "Good candidate", {}, "jane", created_at=now)
    db_session.commit()

    events = ledger.get_events(db_session, candidate_id)
    assert len(events) == 2
    assert events[0].event_type == "NOTE_ADDED"
    assert events[1].event_type == "RESUME_INGESTED"


# ---------------------------------------------------------------------------
# Section 6: Bulk Ingestion Runner & Summary Reports
# ---------------------------------------------------------------------------

def test_get_file_hash(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    hash_val = get_file_hash(test_file)
    assert hash_val is not None
    assert len(hash_val) == 64


def test_bulk_ingest_dry_run(tmp_path: Path) -> None:
    source_dir = tmp_path / "Resumes"
    source_dir.mkdir()
    (source_dir / "resume1.docx").write_text("fake docx")

    checkpoint_file = tmp_path / "checkpoint.json"
    report_file = tmp_path / "report.json"
    unprocessed_log = tmp_path / "unprocessed.json"

    with patch("bulk_ingest.CASManager"), patch("bulk_ingest._get_sessionmaker"):
        run_bulk_ingest(
            source_dir=str(source_dir),
            batch_size=500,
            checkpoint_file=str(checkpoint_file),
            report_file=str(report_file),
            unprocessed_log=str(unprocessed_log),
            dry_run=True,
        )

    assert not checkpoint_file.exists()
    assert not report_file.exists()


def test_generate_markdown_summary_candidate_breakdown(tmp_path: Path) -> None:
    records = [
        {"status": "SUCCESS", "resolution_action": "NEW", "candidate_id": "cand-1", "candidate_name": "Alice", "how_processed": "PyMuPDF", "ai_used": False, "folder_tag": "Eng", "file_name": "a.pdf"},
        {"status": "SUCCESS", "resolution_action": "MERGE", "candidate_id": "cand-1", "candidate_name": "Alice", "how_processed": "PyMuPDF", "ai_used": False, "folder_tag": "Eng", "file_name": "a2.pdf"},
        {"status": "SKIPPED_NON_RESUME", "category": "NON_RESUME_IMMIGRATION_OR_ID", "file_name": "passport.pdf"},
        {"status": "SKIPPED_DUPLICATE", "file_name": "dup.docx"},
    ]
    out_file = tmp_path / "summary.md"
    generate_markdown_summary(records, out_file)
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "- **Total Files Evaluated:** 4" in content
    assert "| `Merge` |" in content
    assert "| `New` |" in content
