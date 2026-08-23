import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy.orm import Session, sessionmaker

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
from storage.cas import CASManager
from storage.db_models import (
    Candidate,
    EntityResolutionAudit,
    ResumeVersion,
    CandidateTimelineEvent,
)

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


def make_settings(tmp_path, **overrides: Any) -> Settings:
    return Settings(
        db_path=str(tmp_path / "s.db"),
        cas_root_dir=str(tmp_path / "cas"),
        vector_db_path=str(tmp_path / "vector"),
        **overrides,
    )


@pytest.fixture
def cas_mgr(test_settings) -> CASManager:
    return CASManager(test_settings.cas_root_dir)


@pytest.fixture
def vector_db() -> MockVectorStore:
    return MockVectorStore()


@pytest.fixture
def mock_extraction(monkeypatch) -> Dict[str, Any]:
    """Patch facts + hybrid extractor at the intake seam. Ollama never live."""
    payload: Dict[str, Any] = dict(EXTRACTED_JANE)
    calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.deterministic_ner.extract_facts",
        lambda text: [],
    )

    def fake_extract(text: str, **kwargs: Any) -> Dict[str, Any]:
        calls.append({"text": text, **kwargs})
        return dict(payload)

    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid",
        fake_extract,
    )
    monkeypatch.setattr(
        "api.services.candidate_service.generate_embeddings",
        lambda texts: [[0.0] * 4 for _ in texts],
    )
    return payload


# 1. Dedup check runs BEFORE CAS store (D5)
def test_duplicate_checked_before_cas_store(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    content = RESUME_TEXT.encode("utf-8")
    store_calls: List[bytes] = []
    original_store = cas_mgr.store

    def recording_store(c: bytes, extension: str = "") -> tuple:
        store_calls.append(c)
        return original_store(c, extension=extension)

    cas_mgr.store = recording_store  # type: ignore[method-assign]

    first = ingest_file(
        content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert first.status == IntakeStatus.INGESTED
    assert len(store_calls) == 1

    second = ingest_file(
        content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    assert second.status == IntakeStatus.SKIPPED_DUPLICATE
    assert second.candidate_id == first.candidate_id
    assert len(store_calls) == 1


# 2. Non-resume rejection persists nothing (no DB rows)
def test_non_resume_persists_nothing(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    result = ingest_file(
        content=CONTRACT_TEXT.encode("utf-8"), filename="REFERRAL AGREEMENT.pdf", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    assert result.status == IntakeStatus.SKIPPED_NON_RESUME
    assert result.classified_as == "NON_RESUME_LEGAL_CONTRACT"
    assert db_session.query(Candidate).count() == 0
    assert db_session.query(ResumeVersion).count() == 0
    assert db_session.query(EntityResolutionAudit).count() == 0


# 3. MERGE demotes old primary RV and incoming RV becomes primary (D12)
def test_merge_demotes_old_primary_version(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    existing_id = str(uuid.uuid4())
    existing = Candidate(id=existing_id, first_name="Jane", last_name="Doe", primary_email="old@example.com")
    old_rv = ResumeVersion(
        id=str(uuid.uuid4()), candidate_id=existing_id, cas_file_hash="oldhash",
        original_filename="old.txt", file_type="TXT", raw_text="old", layout_metadata={}, is_primary=True,
    )
    db_session.add_all([existing, old_rv])
    db_session.commit()

    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert result.status == IntakeStatus.MERGED
    assert result.candidate_id == existing_id
    assert db_session.query(Candidate).count() == 1
    db_session.refresh(old_rv)
    assert old_rv.is_primary is False
    new_rv = db_session.query(ResumeVersion).filter(ResumeVersion.id != old_rv.id).first()
    assert new_rv is not None and new_rv.is_primary is True


# 4. REVIEW creates NEW candidate + EntityResolutionAudit row (D2), matched id carries look-alike
def test_review_creates_audit_row(db_session, tmp_path, cas_mgr, vector_db, mock_extraction):
    lookalike_id = str(uuid.uuid4())
    db_session.add(Candidate(id=lookalike_id, first_name="Jon", last_name="Doee"))
    db_session.commit()

    settings = make_settings(tmp_path, entity_res_auto_merge_threshold=1.01, entity_res_review_threshold=0.70)
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert result.status == IntakeStatus.INGESTED
    assert result.resolution_action.value == "REVIEW"
    assert result.matched_candidate_id == lookalike_id
    assert result.candidate_id != lookalike_id

    audit = db_session.query(EntityResolutionAudit).one()
    assert audit.resolution_type == "REVIEW"
    assert audit.primary_candidate_id == result.candidate_id
    assert audit.merged_candidate_id == lookalike_id
    criteria = audit.matching_criteria
    assert criteria["source_door"] == "upload"
    assert criteria["matched_candidate_id"] == lookalike_id
    assert criteria["created_candidate_id"] == result.candidate_id


# 5. MERGE writes an audit row; NEW stays silent (#8)
def test_merge_writes_audit_new_is_silent(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    existing_id = str(uuid.uuid4())
    db_session.add(Candidate(id=existing_id, first_name="Jane", last_name="Doe"))
    db_session.commit()

    merged = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert merged.status == IntakeStatus.MERGED
    audit = db_session.query(EntityResolutionAudit).one()
    assert audit.resolution_type == "MERGE"
    assert audit.primary_candidate_id == existing_id
    assert audit.merged_candidate_id == existing_id

    # Distinct contact facts: after #15 the merged Jane carries the extracted
    # phone/email, so an unrelated person must not tier1-match her.
    fresh_text = RESUME_TEXT.replace("Jane", "Zack").replace("jane.doe@example.com", "zack@example.com")
    mock_extraction.update({
        "first_name": "Zack",
        "primary_email": "zack@example.com",
        "primary_phone": "555-987-6543",
    })
    new_result = ingest_file(
        content=fresh_text.encode("utf-8"), filename="zack.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert new_result.status == IntakeStatus.INGESTED
    assert new_result.resolution_action.value == "NEW"
    assert db_session.query(EntityResolutionAudit).count() == 1


# 6. Timeline switch (D3): LEDGER writes event, NONE does not
@pytest.mark.parametrize("mode,writes_event", [(TimelineMode.LEDGER, True), (TimelineMode.NONE, False)])
def test_timeline_mode_switch(db_session, test_settings, cas_mgr, vector_db, mock_extraction, mode, writes_event):
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.BULK,
        timeline_mode=mode,
    )
    db_session.commit()
    assert result.status == IntakeStatus.INGESTED
    events = db_session.query(CandidateTimelineEvent)\
        .filter(CandidateTimelineEvent.event_type == "RESUME_INGESTED").all()
    assert (len(events) == 1) is writes_event


# 7. Progress callback emits canonical stages in order
def test_progress_callback_sequence(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    ticks: List[IntakeProgress] = []
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
        on_progress=ticks.append,
    )
    assert result.status == IntakeStatus.INGESTED
    stages = [t.stage for t in ticks]
    expected_prefix = ["HASHING", "PARSING", "CLASSIFYING", "EXTRACTING", "ENTITY_RESOLUTION"]
    assert stages[: len(expected_prefix)] == expected_prefix
    for later in ["SAVING" in stages, "UPDATING_FTS" in stages, "GENERATING_VECTORS" in stages,
                  "LOGGING_TIMELINE" in stages, "COMPLETED" in stages]:
        assert later
    progresses = [t.progress for t in ticks]
    assert progresses == sorted(progresses)
    assert all(0 <= p <= 100 for p in progresses)


# 8. Thresholds come from Settings, not module constants (D4)
def test_thresholds_driven_by_settings(db_session, tmp_path, cas_mgr, vector_db, mock_extraction):
    lookalike_id = str(uuid.uuid4())
    db_session.add(Candidate(id=lookalike_id, first_name="Jane", last_name="Doex"))
    db_session.commit()

    strict = make_settings(tmp_path, entity_res_auto_merge_threshold=1.01, entity_res_review_threshold=1.01)
    new_result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="a.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=strict, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert new_result.resolution_action.value == "NEW"

    loose = make_settings(tmp_path, entity_res_auto_merge_threshold=0.10, entity_res_review_threshold=0.05)
    loose_result = ingest_file(
        content=RESUME_TEXT.replace("555-123-4567", "555-987-6543").encode("utf-8"),
        filename="b.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=loose, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert loose_result.resolution_action.value in ("MERGE", "REVIEW")


# 9. Extraction called exactly once with precomputed facts (D13)
def test_extraction_called_once_with_facts(db_session, test_settings, cas_mgr, vector_db, mock_extraction, monkeypatch):
    calls: List[Any] = []
    real_extract = __import__(
        "candidate_intelligence_platform.extraction.hybrid_extractor",
        fromlist=["extract_candidate_profile_hybrid"],
    ).extract_candidate_profile_hybrid

    def spy(text: str, **kwargs: Any) -> Dict[str, Any]:
        calls.append(kwargs)
        return real_extract.__wrapped__(text, **kwargs) if hasattr(real_extract, "__wrapped__") else dict(EXTRACTED_JANE)

    monkeypatch.setattr(
        "candidate_intelligence_platform.extraction.hybrid_extractor.extract_candidate_profile_hybrid", spy
    )
    ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert len(calls) == 1
    assert "facts" in calls[0]


# 10. Vector failure degrades to PARTIAL, never fatal
def test_vector_failure_yields_partial(db_session, test_settings, cas_mgr, vector_db, mock_extraction, monkeypatch):
    from api.services.candidate_service import CandidateService
    monkeypatch.setattr(CandidateService, "update_vector_index", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert result.status == IntakeStatus.PARTIAL
    assert any("Vector indexing skipped" in w for w in result.warnings)
    assert db_session.query(Candidate).count() == 1


# 11. reprocess_text applies extracted fields, refreshes FTS, logs REPROCESS_TRIGGERED
def test_reprocess_text_applies_fields(db_session, test_settings, vector_db, mock_extraction):
    cand_id = str(uuid.uuid4())
    rv_id = str(uuid.uuid4())
    db_session.add(Candidate(id=cand_id, first_name="Stale", last_name="Name"))
    db_session.add(ResumeVersion(
        id=rv_id, candidate_id=cand_id, cas_file_hash="h", original_filename="r.txt",
        file_type="TXT", raw_text=RESUME_TEXT, layout_metadata={}, is_primary=True,
    ))
    db_session.commit()

    result = reprocess_text(
        raw_text=RESUME_TEXT, candidate_id=cand_id, resume_version_id=rv_id,
        db=db_session, vector_db=vector_db, settings=test_settings,
    )
    db_session.commit()

    assert result.status == IntakeStatus.INGESTED
    assert result.used_ai_fallback is False
    candidate = db_session.get(Candidate, cand_id)
    assert candidate.first_name == "Jane"
    assert candidate.primary_email == "jane.doe@example.com"

    from sqlalchemy import text as sql_text
    fts_rows = db_session.execute(
        sql_text("SELECT * FROM candidate_fts WHERE candidate_id = :cid"), {"cid": cand_id}
    ).fetchall()
    assert len(fts_rows) == 1

    events = db_session.query(CandidateTimelineEvent)\
        .filter(CandidateTimelineEvent.event_type == "REPROCESS_TRIGGERED").all()
    assert len(events) == 1


def test_classify_document_moved_and_public():
    is_resume, category, _ = classify_document(CONTRACT_TEXT, "REFERRAL AGREEMENT.pdf")
    assert not is_resume
    assert category == "NON_RESUME_LEGAL_CONTRACT"
    is_resume, category, _ = classify_document(RESUME_TEXT, "resume.txt")
    assert is_resume
    assert category == "VALID_RESUME"


def test_ui_duplicate_chip_wired():
    """Possible-duplicate chip reads resolution_action/matched_candidate_id from the queue row."""
    source = Path("ui/src/pages/CandidateList.jsx").read_text(encoding="utf-8")
    assert "resolution_action === 'REVIEW'" in source
    assert "matched_candidate_id" in source
    assert "Possible duplicate?" in source


# ---------------------------------------------------------------------------
# Issue #14: rejected uploads leave zero CAS files behind
# ---------------------------------------------------------------------------

def _cas_file_count(cas_root: str) -> int:
    return sum(1 for p in Path(cas_root).rglob("*") if p.is_file())


def test_classifier_rejection_purges_cas_file(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    result = ingest_file(
        content=CONTRACT_TEXT.encode("utf-8"), filename="REFERRAL AGREEMENT.pdf", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    assert result.status == IntakeStatus.SKIPPED_NON_RESUME
    assert result.classified_as == "NON_RESUME_LEGAL_CONTRACT"
    assert _cas_file_count(test_settings.cas_root_dir) == 0
    assert db_session.query(Candidate).count() == 0
    assert db_session.query(ResumeVersion).count() == 0


def test_dummy_profile_rejection_purges_cas_file(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    mock_extraction.update({
        "first_name": "Uploaded",
        "last_name": "Candidate",
        "primary_email": None,
        "primary_phone": None,
        "current_title": "",
    })
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    assert result.status == IntakeStatus.SKIPPED_NON_RESUME
    assert result.classified_as == "AI_CLASSIFIED_NOT_RESUME"
    assert _cas_file_count(test_settings.cas_root_dir) == 0


def test_error_after_store_purges_cas_file(db_session, test_settings, cas_mgr, vector_db, mock_extraction, monkeypatch):
    import candidate_intelligence_platform.ingestion.intake as intake_module

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("resolution exploded")

    monkeypatch.setattr(intake_module, "resolve", boom)
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    assert result.status == IntakeStatus.ERROR
    assert _cas_file_count(test_settings.cas_root_dir) == 0


def test_successful_ingest_keeps_exactly_one_cas_file(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert result.status == IntakeStatus.INGESTED
    assert _cas_file_count(test_settings.cas_root_dir) == 1


def test_duplicate_skip_never_stores_or_purges(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    content = RESUME_TEXT.encode("utf-8")
    first = ingest_file(
        content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert first.status == IntakeStatus.INGESTED

    second = ingest_file(
        content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    assert second.status == IntakeStatus.SKIPPED_DUPLICATE
    assert _cas_file_count(test_settings.cas_root_dir) == 1


def test_purge_failure_degrades_to_warning(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    cas_mgr.delete = lambda file_path: False  # type: ignore[method-assign]
    result = ingest_file(
        content=CONTRACT_TEXT.encode("utf-8"), filename="REFERRAL AGREEMENT.pdf", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    assert result.status == IntakeStatus.SKIPPED_NON_RESUME
    assert any("CAS purge failed" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# PR #25 review: shared CAS objects must survive other pipelines' failures
# ---------------------------------------------------------------------------

def test_rejection_keeps_file_while_another_holder_shares_hash(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    """Concurrent identical upload: the other pipeline's hold blocks the purge."""
    import candidate_intelligence_platform.ingestion.intake as intake_module

    content = RESUME_TEXT.encode("utf-8")
    file_hash = hashlib.sha256(content).hexdigest()

    mock_extraction.update({
        "first_name": "Uploaded",
        "last_name": "Candidate",
        "primary_email": None,
        "primary_phone": None,
        "current_title": "",
    })

    intake_module._acquire_cas_ref(file_hash)
    try:
        result = ingest_file(
            content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
            vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
            timeline_mode=TimelineMode.LEDGER,
        )
        assert result.status == IntakeStatus.SKIPPED_NON_RESUME
        assert _cas_file_count(test_settings.cas_root_dir) == 1
    finally:
        intake_module._release_cas_ref(file_hash)

    # Once no holder remains and nothing is committed, cleanup works again.
    second = ingest_file(
        content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )
    assert second.status == IntakeStatus.SKIPPED_NON_RESUME
    assert _cas_file_count(test_settings.cas_root_dir) == 0


def test_error_never_deletes_committed_duplicate_object(db_session, test_settings, cas_mgr, vector_db, mock_extraction, monkeypatch):
    """A committed RV sharing the hash pins the CAS file against later purges.

    Simulates the PR #25 race: upload B commits the same bytes while upload A
    is still running; A then fails and must not delete the shared object.
    """
    import candidate_intelligence_platform.ingestion.intake as intake_module

    content = RESUME_TEXT.encode("utf-8")
    file_hash = hashlib.sha256(content).hexdigest()

    def commit_twin_then_resume(db: Session) -> List[Any]:
        twin = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())()
        try:
            owner_id = str(uuid.uuid4())
            twin.add(Candidate(id=owner_id, first_name="Concurrent", last_name="Upload"))
            twin.add(ResumeVersion(
                id=str(uuid.uuid4()), candidate_id=owner_id, cas_file_hash=file_hash,
                original_filename="twin.txt", file_type="TXT", raw_text="same bytes",
                layout_metadata={}, is_primary=True,
            ))
            twin.commit()
        finally:
            twin.close()
        return []

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("resolution exploded")

    monkeypatch.setattr(intake_module, "_load_existing_identifiers", commit_twin_then_resume)
    monkeypatch.setattr(intake_module, "resolve", boom)

    result = ingest_file(
        content=content, filename="resume.txt", db=db_session, cas_mgr=cas_mgr,
        vector_db=vector_db, settings=test_settings, source=IntakeSource.UPLOAD,
        timeline_mode=TimelineMode.LEDGER,
    )

    assert result.status == IntakeStatus.ERROR
    stored = [
        p for p in Path(test_settings.cas_root_dir).rglob("*")
        if p.is_file() and p.name.startswith(file_hash)
    ]
    assert len(stored) == 1


def test_success_release_allows_later_cleanup_of_other_files(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    """Success drops the hold, so unrelated rejections still purge their bytes."""
    ok = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()
    assert ok.status == IntakeStatus.INGESTED

    rejected = ingest_file(
        content=CONTRACT_TEXT.encode("utf-8"), filename="REFERRAL AGREEMENT.pdf", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    assert rejected.status == IntakeStatus.SKIPPED_NON_RESUME
    assert _cas_file_count(test_settings.cas_root_dir) == 1


# ---------------------------------------------------------------------------
# Issue #15: MERGE refreshes candidate profile from the new primary RV
# ---------------------------------------------------------------------------

def test_merge_refreshes_profile_fields_and_fts(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    existing_id = str(uuid.uuid4())
    db_session.add(Candidate(
        id=existing_id,
        first_name="Jane",
        last_name="Doe",
        primary_email="stale@example.com",
        primary_phone="000-000-0000",
        current_title="Old Title",
    ))
    db_session.commit()

    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert result.status == IntakeStatus.MERGED
    cand = db_session.get(Candidate, existing_id)
    assert cand.first_name == "Jane"
    assert cand.last_name == "Doe"
    assert cand.primary_email == "jane.doe@example.com"
    assert cand.primary_phone == "555-123-4567"
    assert cand.current_title == "Engineer"

    audits = db_session.query(EntityResolutionAudit).all()
    assert len(audits) == 1 and audits[0].resolution_type == "MERGE"

    from sqlalchemy import text as sql_text
    fts_rows = db_session.execute(
        sql_text("SELECT full_name, current_title FROM candidate_fts WHERE candidate_id = :cid"),
        {"cid": existing_id},
    ).fetchall()
    assert len(fts_rows) == 1
    assert fts_rows[0].full_name == "Jane Doe"
    assert fts_rows[0].current_title == "Engineer"


def test_merge_preserves_fields_when_extraction_omits_them(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    existing_id = str(uuid.uuid4())
    db_session.add(Candidate(
        id=existing_id,
        first_name="Jane",
        last_name="Doe",
        primary_email="keep@example.com",
        primary_phone="111-222-3333",
        current_title="Keeper Title",
    ))
    db_session.commit()

    mock_extraction.update({"primary_email": "", "primary_phone": "", "current_title": ""})
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert result.status == IntakeStatus.MERGED
    cand = db_session.get(Candidate, existing_id)
    assert cand.primary_email == "keep@example.com"
    assert cand.primary_phone == "111-222-3333"
    assert cand.current_title == "Keeper Title"
    assert cand.first_name == "Jane" and cand.last_name == "Doe"


def test_new_candidate_path_untouched_by_merge_refresh(db_session, test_settings, cas_mgr, vector_db, mock_extraction):
    result = ingest_file(
        content=RESUME_TEXT.encode("utf-8"), filename="resume.txt", db=db_session,
        cas_mgr=cas_mgr, vector_db=vector_db, settings=test_settings,
        source=IntakeSource.UPLOAD, timeline_mode=TimelineMode.LEDGER,
    )
    db_session.commit()

    assert result.status == IntakeStatus.INGESTED
    cand = db_session.get(Candidate, result.candidate_id)
    assert cand.first_name == "Jane"
    assert cand.primary_email == "jane.doe@example.com"
    assert cand.current_title == "Engineer"
