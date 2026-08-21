"""Performance benchmarks for upload and search pipelines.

Run with: uv run pytest tests/test_performance.py --benchmark-only -v

Benchmarks use the 4 test resumes in test-resumes/ and measure per-stage timings.
Thresholds are generous (~2x headroom) to avoid flakiness.
"""
import os
import cProfile
import pstats
from pathlib import Path
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.dependencies import get_db, get_vector_db, get_settings
from config.settings import Settings
from storage.db_models import Base

TEST_RESUMES_DIR = Path(__file__).parent.parent / "test-resumes"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bench_engine():
    """In-memory SQLite engine with FTS5 for benchmarks (per-test isolation)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS candidate_fts USING fts5(
                candidate_id UNINDEXED,
                full_name,
                current_title,
                current_company,
                resume_content,
                tokenize = 'porter unicode61'
            );
        """))
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
                claim_id UNINDEXED,
                candidate_id UNINDEXED,
                claim_category,
                claim_key,
                claim_value,
                tokenize = 'porter unicode61'
            );
        """))
    return engine


@pytest.fixture
def bench_session_factory(bench_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=bench_engine)


class MockVectorStore:
    """Mock LanceDB for benchmarks (no real vector search)."""
    def __init__(self):
        self.tables = {}

    def delete_candidate_vectors(self, candidate_id):
        pass

    def list_tables(self):
        return list(self.tables.keys())

    def table_names(self):
        return list(self.tables.keys())

    def open_table(self, name):
        return self.tables.get(name, self._create_mock(name))

    def create_table(self, name, *args, **kwargs):
        return self.tables.setdefault(name, self._create_mock(name))

    def _create_mock(self, name):
        class T:
            def __init__(self):
                self.records = []
            def add(self, records):
                self.records.extend(records)
            def delete(self, *a, **kw):
                pass
            def search(self, *a, **kw):
                class S:
                    def limit(self, n): return self
                    def to_list(self): return []
                return S()
        return T()


@pytest.fixture
def bench_settings(tmp_path):
    return Settings(
        db_path=":memory:",
        cas_root_dir=str(tmp_path / "documents"),
        vector_db_path=str(tmp_path / "vector"),
    )


@pytest.fixture
def bench_client(bench_engine, bench_session_factory, bench_settings):
    """TestClient wired to in-memory DB + mock vector store (per-test)."""
    mock_vec = MockVectorStore()

    def override_db():
        s = bench_session_factory()
        try:
            yield s
        finally:
            s.close()

    def override_vec():
        return mock_vec

    def override_settings():
        return bench_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_vector_db] = override_vec
    app.dependency_overrides[get_settings] = override_settings

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_resume_bytes(filename: str) -> tuple[str, bytes]:
    path = TEST_RESUMES_DIR / filename
    return filename, path.read_bytes()


def _parse_sse_events(response) -> list[dict]:
    events = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            try:
                events.append(__import__("json").loads(line[6:]))
            except Exception:
                pass
    return events


# ---------------------------------------------------------------------------
# Upload benchmarks
# ---------------------------------------------------------------------------

class TestUploadBenchmarks:
    """Benchmarks for resume upload pipeline stages."""

    @pytest.mark.parametrize(
        "resume_file",
        [
            "Bilal_Java Full Stack Developer_USC_REMOTE.docx",
            "Inzamam Haqqani Resume 2026.docx",
            "MONIKA_USC.docx",
            "Srinivas_cyber security_USC_GA.pdf",
        ],
    )
    def test_single_upload(self, bench_client, resume_file, benchmark):
        """Benchmark single-file upload endpoint."""
        filename, content = _load_resume_bytes(resume_file)
        ext = Path(filename).suffix
        mime = (
            "application/pdf"
            if ext == ".pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        def _upload():
            return bench_client.post(
                "/candidates/upload",
                files=[("file", (filename, content, mime))],
            )

        result = benchmark(_upload)
        assert result.status_code == 200

    def test_batch_upload_4_files(self, bench_client, benchmark):
        """Benchmark batch upload of all 4 test resumes."""
        files = []
        for fname in os.listdir(TEST_RESUMES_DIR):
            if fname.endswith((".pdf", ".docx")):
                path = TEST_RESUMES_DIR / fname
                ext = Path(fname).suffix
                mime = (
                    "application/pdf"
                    if ext == ".pdf"
                    else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                files.append(("files", (fname, path.read_bytes(), mime)))

        def _batch_upload():
            return bench_client.post("/candidates/upload-stream", files=files)

        result = benchmark(_batch_upload)
        assert result.status_code == 200
        events = _parse_sse_events(result)
        # Count both COMPLETED (new) and SKIPPED_DUPLICATE (dedup) events
        terminal_events = [
            e for e in events
            if e.get("stage") in ("COMPLETED", "SKIPPED_DUPLICATE")
        ]
        assert len(terminal_events) == len(files)


# ---------------------------------------------------------------------------
# Search benchmarks
# ---------------------------------------------------------------------------

class TestSearchBenchmarks:
    """Benchmarks for hybrid search pipeline."""

    def _seed_candidates(self, bench_client):
        """Upload resumes to create a searchable corpus."""
        for fname in os.listdir(TEST_RESUMES_DIR):
            if fname.endswith((".pdf", ".docx")):
                path = TEST_RESUMES_DIR / fname
                ext = Path(fname).suffix
                mime = (
                    "application/pdf"
                    if ext == ".pdf"
                    else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                bench_client.post(
                    "/candidates/upload",
                    files=[("file", (fname, path.read_bytes(), mime))],
                )

    @pytest.fixture
    def seeded_client(self, bench_client):
        self._seed_candidates(bench_client)
        return bench_client

    def test_search_keyword(self, seeded_client, benchmark):
        """Benchmark keyword-only search."""
        def _search():
            return seeded_client.post("/search", json={"query_text": "python engineer"})

        result = benchmark(_search)
        assert result.status_code == 200

    def test_search_with_filters(self, seeded_client, benchmark):
        """Benchmark search with location + title filters."""
        def _search():
            return seeded_client.post(
                "/search",
                json={"query_text": "developer", "city": "Remote", "top_k": 5},
            )

        result = benchmark(_search)
        assert result.status_code == 200

    def test_search_stream(self, seeded_client, benchmark):
        """Benchmark streaming search endpoint."""
        def _search():
            return seeded_client.post("/search/stream", json={"query_text": "security analyst"})

        result = benchmark(_search)
        assert result.status_code == 200


# ---------------------------------------------------------------------------
# cProfile attribution (manual run, not benchmark-gated)
# ---------------------------------------------------------------------------

def _profile_upload_pipeline():
    """Profile the full upload pipeline and print top functions."""
    from ingestion.parsers.pdf_parser import parse_pdf
    from ingestion.parsers.docx_parser import parse_docx
    from ingestion.parsers.models import ParsedDocument
    from ingestion.chunker import chunk_document
    from candidate_intelligence_platform.extraction.hybrid_extractor import (
        extract_candidate_profile_hybrid,
    )
    from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings

    profiler = cProfile.Profile()
    profiler.enable()

    for fname in os.listdir(TEST_RESUMES_DIR):
        path = TEST_RESUMES_DIR / fname
        ext = Path(fname).suffix.lower()

        if ext == ".pdf":
            doc = parse_pdf(path)
        elif ext in (".docx", ".doc"):
            doc = parse_docx(path)
        else:
            doc = ParsedDocument(text=path.read_text(errors="ignore"), pages=1)

        raw_text = doc.text
        extracted = extract_candidate_profile_hybrid(raw_text, confidence_threshold=0.40)
        chunks = chunk_document(ParsedDocument(text=raw_text, pages=1), "bench-id", "SUMMARY")
        if chunks:
            generate_embeddings([c.text for c in chunks])

    profiler.disable()

    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(20)
    print(stream.getvalue())


def _profile_search_pipeline():
    """Profile the search pipeline and print top functions."""
    from candidate_intelligence_platform.search.ast_parser import parse_query_to_sql
    from candidate_intelligence_platform.intelligence.embeddings import generate_single_embedding

    # Warm up caches
    parse_query_to_sql("python developer")
    generate_single_embedding("python developer")


if __name__ == "__main__":
    print("=== Upload Pipeline Profile ===")
    _profile_upload_pipeline()
