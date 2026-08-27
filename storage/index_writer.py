from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
import logging

from storage.db_models import Candidate, ResumeVersion
from storage.vector_store import CandidateSectionVector
from ingestion.chunker import chunk_resume
from ingestion.parsers.models import ParsedDocument
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings

logger = logging.getLogger(__name__)

def _has_candidate_vectors_table(vector_db: Any) -> bool:
    """Check for the candidate_vectors table across lancedb API variants."""
    try:
        if hasattr(vector_db, "list_tables"):
            result = vector_db.list_tables()
            names = getattr(result, "tables", result)
            return "candidate_vectors" in names
        if hasattr(vector_db, "table_names"):
            return "candidate_vectors" in vector_db.table_names()
    except Exception:
        return False
    return False

class StorageIndexWriter:
    """Single owner of SQLite FTS5 and LanceDB vector index synchronization."""
    
    def __init__(self, db_session: Session, vector_db: Any):
        self.db = db_session
        self.vector_db = vector_db
        
    def write_candidate_indices(
        self, candidate: Candidate, resume_version_id: str, raw_text: str,
        chunks: Any = None, embeddings: Any = None
    ) -> None:
        """Atomic write to SQLite FTS5 table and LanceDB vector chunks."""
        if self.vector_db is not None and chunks is None:
            doc = ParsedDocument(text=raw_text, pages=1)
            chunks = chunk_resume(doc, candidate.id)
            if chunks:
                texts = [c.text for c in chunks]
                embeddings = generate_embeddings(texts)

        nested = self.db.begin_nested()
        try:
            self._update_fts(candidate, raw_text)
            self._update_vectors_with_precomputed(candidate.id, resume_version_id, chunks, embeddings)
            nested.commit()
        except Exception as e:
            nested.rollback()
            logger.error("index_writer_sync_failed", extra={"candidate_id": candidate.id, "error": str(e)})
            raise
        
    def delete_candidate_indices(self, candidate_id: str) -> None:
        """Atomic deletion from both search stores."""
        nested = self.db.begin_nested()
        try:
            self._delete_fts(candidate_id)
            self._delete_vectors(candidate_id)
            nested.commit()
        except Exception as e:
            nested.rollback()
            logger.error("index_writer_delete_failed", extra={"candidate_id": candidate_id, "error": str(e)})
            raise
            
    def _update_fts(self, candidate: Candidate, raw_text: str) -> None:
        self.db.execute(text("DELETE FROM candidate_fts WHERE candidate_id = :cid"), {"cid": candidate.id})
        self.db.execute(
            text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
            {
                "cid": candidate.id,
                "fname": f"{candidate.first_name} {candidate.last_name}",
                "title": candidate.current_title or "",
                "company": candidate.current_company or "",
                "content": raw_text
            }
        )

    def _delete_fts(self, candidate_id: str) -> None:
        self.db.execute(text("DELETE FROM candidate_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
        self.db.execute(text("DELETE FROM claims_fts WHERE candidate_id = :cid"), {"cid": candidate_id})

    def _update_vectors_with_precomputed(self, candidate_id: str, rv_id: str, chunks: Any, embeddings: Any) -> None:
        self._delete_vectors(candidate_id)
        if self.vector_db is None or not chunks:
            return
        if hasattr(self.vector_db, "create_table"):
            table = self.vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
            records = []
            for i, chunk in enumerate(chunks):
                records.append(CandidateSectionVector.create_record(chunk, rv_id, embeddings[i]))
            table.add(records)

    def _delete_vectors(self, candidate_id: str) -> None:
        if self.vector_db is None:
            return
        if hasattr(self.vector_db, "delete_candidate_vectors"):
            self.vector_db.delete_candidate_vectors(candidate_id)
        elif _has_candidate_vectors_table(self.vector_db):
            table = self.vector_db.open_table("candidate_vectors")
            safe_id = candidate_id.replace('"', '""')
            table.delete(f'candidate_id = "{safe_id}"')
