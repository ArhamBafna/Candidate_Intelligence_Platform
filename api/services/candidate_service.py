from sqlalchemy.orm import Session
from sqlalchemy import text
from storage.db_models import Candidate, ResumeVersion, CandidateClaim, CandidateTimelineEvent
from storage.vector_store import CandidateSectionVector
from ingestion.chunker import chunk_document
from ingestion.parsers.models import ParsedDocument
from candidate_intelligence_platform.intelligence.embeddings import generate_embeddings

class CandidateService:
    @staticmethod
    def delete_candidate(db: Session, candidate_id: str, vector_db) -> bool:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return False

        try:
            db.execute(text("DELETE FROM candidate_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
            db.execute(text("DELETE FROM claims_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
        except Exception:
            pass

        # Delete related child records
        db.query(ResumeVersion).filter(ResumeVersion.candidate_id == candidate_id).delete()
        db.query(CandidateClaim).filter(CandidateClaim.candidate_id == candidate_id).delete()
        db.query(CandidateTimelineEvent).filter(CandidateTimelineEvent.candidate_id == candidate_id).delete()

        db.delete(candidate)
        db.commit()

        if vector_db:
            if hasattr(vector_db, "delete_candidate_vectors"):
                vector_db.delete_candidate_vectors(candidate_id)
            else:
                try:
                    tables = vector_db.list_tables() if hasattr(vector_db, "list_tables") else vector_db.table_names()
                    if "candidate_vectors" in tables:
                        table = vector_db.open_table("candidate_vectors")
                        table.delete(f'candidate_id = "{candidate_id}"')
                except Exception:
                    pass
        return True

    @staticmethod
    def update_fts_index(db: Session, candidate_id: str, candidate_name: str, candidate: Candidate, raw_text: str):
        db.execute(text("DELETE FROM candidate_fts WHERE candidate_id = :cid"), {"cid": candidate_id})
        db.execute(
            text("INSERT INTO candidate_fts (candidate_id, full_name, current_title, current_company, resume_content) VALUES (:cid, :fname, :title, :company, :content)"),
            {
                "cid": candidate_id,
                "fname": candidate_name,
                "title": candidate.current_title or "",
                "company": candidate.current_company or "",
                "content": raw_text
            }
        )
        db.commit()

    @staticmethod
    def update_vector_index(vector_db, candidate_id: str, raw_text: str, rv_id: str):
        if hasattr(vector_db, "delete_candidate_vectors"):
            vector_db.delete_candidate_vectors(candidate_id)
        else:
            tables = vector_db.list_tables() if hasattr(vector_db, "list_tables") else vector_db.table_names()
            if "candidate_vectors" in tables:
                table = vector_db.open_table("candidate_vectors")
                table.delete(f'candidate_id = "{candidate_id}"')

        doc = ParsedDocument(text=raw_text, pages=1)
        chunks = chunk_document(doc, candidate_id, "SUMMARY")
        if chunks:
            texts = [c.text for c in chunks]
            embeddings = generate_embeddings(texts)
            if hasattr(vector_db, "create_table"):
                table = vector_db.create_table("candidate_vectors", schema=CandidateSectionVector, exist_ok=True)
                records = []
                for i, chunk in enumerate(chunks):
                    records.append(CandidateSectionVector.create_record(chunk, rv_id, embeddings[i]))
                table.add(records)
