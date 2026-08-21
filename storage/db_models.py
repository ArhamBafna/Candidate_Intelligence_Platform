from sqlalchemy import (
    Column, String, Boolean, Float, Integer, Date, 
    DateTime, ForeignKey, JSON, text
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine

Base = declarative_base()

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(String, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    primary_email = Column(String, unique=True)
    primary_phone = Column(String)
    linkedin_url = Column(String, unique=True)
    current_city = Column(String, index=True)
    current_country = Column(String)
    current_title = Column(String)
    current_company = Column(String)
    total_yoe = Column(Float, default=0.0)
    desired_salary_min = Column(Integer)
    desired_salary_max = Column(Integer)
    currency = Column(String, default='USD')
    availability_status = Column(String, default='ACTIVE')
    custom_attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class ResumeVersion(Base):
    __tablename__ = 'resume_versions'
    id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    cas_file_hash = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    raw_text = Column(String, nullable=False)
    layout_metadata = Column(JSON, nullable=False)
    is_primary = Column(Boolean, default=False)
    ingested_at = Column(DateTime, server_default=func.current_timestamp())

class CandidateClaim(Base):
    __tablename__ = 'candidate_claims'
    id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    resume_version_id = Column(String, ForeignKey('resume_versions.id', ondelete='SET NULL'))
    source_type = Column(String, nullable=False)
    claim_category = Column(String, nullable=False)
    claim_key = Column(String, nullable=False)
    claim_value = Column(String, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    confidence_score = Column(Float, default=1.0)
    source_char_offset_start = Column(Integer)
    source_char_offset_end = Column(Integer)
    extracted_by = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class CandidateTimelineEvent(Base):
    __tablename__ = 'candidate_timeline_events'
    id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    event_metadata = Column(JSON, default=dict)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())

class EntityResolutionAudit(Base):
    __tablename__ = 'entity_resolution_audit'
    id = Column(String, primary_key=True)
    primary_candidate_id = Column(String, nullable=False)
    merged_candidate_id = Column(String, nullable=False)
    resolution_type = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    matching_criteria = Column(JSON, nullable=False)
    merged_at = Column(DateTime, server_default=func.current_timestamp())

def init_db(engine: Engine):
    """
    Creates all declarative tables, FTS5 virtual tables, and performance indexes.
    """
    Base.metadata.create_all(engine)
    
    with engine.begin() as conn:
        # Performance indexes on FK columns (not auto-created by SQLAlchemy)
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_resume_versions_candidate_id ON resume_versions(candidate_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_candidate_claims_candidate_id ON candidate_claims(candidate_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_candidate_claims_resume_version_id ON candidate_claims(resume_version_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_candidate_timeline_events_candidate_id ON candidate_timeline_events(candidate_id)"))
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
