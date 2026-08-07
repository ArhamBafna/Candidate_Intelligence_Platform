import lancedb
from lancedb.pydantic import LanceModel, Vector

class CandidateSectionVector(LanceModel):
    chunk_id: str                      # UUIDv4 of vector chunk
    candidate_id: str                  # Relational FK to candidates.id
    resume_version_id: str             # Relational FK to resume_versions.id
    section_type: str                  # 'WORK_EXPERIENCE', 'EDUCATION', 'SKILLS', 'SUMMARY'
    chunk_text: str                    # Prepared text block with context injection
    vector: Vector(384)                # Dense float32 embedding for BAAI/bge-small-en-v1.5
    start_offset: int                  # Document character offset start
    end_offset: int                    # Document character offset end

def get_lancedb_connection(db_path: str) -> lancedb.DBConnection:
    """
    Connect to the embedded LanceDB instance at the specified path.
    """
    return lancedb.connect(db_path)
