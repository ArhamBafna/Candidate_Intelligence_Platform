from datetime import date, datetime
from typing import Dict, Any, Optional

from sqlalchemy import (
    String, Boolean, Float, Integer, Date, 
    DateTime, ForeignKey, JSON, text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine

class Base(DeclarativeBase):
    pass

class Candidate(Base):
    __tablename__ = 'candidates'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    primary_email: Mapped[Optional[str]] = mapped_column(String, unique=True)
    primary_phone: Mapped[Optional[str]] = mapped_column(String)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String, unique=True)
    current_city: Mapped[Optional[str]] = mapped_column(String, index=True)
    current_country: Mapped[Optional[str]] = mapped_column(String)
    current_title: Mapped[Optional[str]] = mapped_column(String)
    current_company: Mapped[Optional[str]] = mapped_column(String)
    total_yoe: Mapped[float] = mapped_column(Float, default=0.0)
    desired_salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    desired_salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default='USD')
    availability_status: Mapped[str] = mapped_column(String, default='ACTIVE')
    custom_attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class ResumeVersion(Base):
    __tablename__ = 'resume_versions'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    cas_file_hash: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str] = mapped_column(String, nullable=False)
    layout_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

class CandidateClaim(Base):
    __tablename__ = 'candidate_claims'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    resume_version_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey('resume_versions.id', ondelete='SET NULL'))
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    claim_category: Mapped[str] = mapped_column(String, nullable=False)
    claim_key: Mapped[str] = mapped_column(String, nullable=False)
    claim_value: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    source_char_offset_start: Mapped[Optional[int]] = mapped_column(Integer)
    source_char_offset_end: Mapped[Optional[int]] = mapped_column(Integer)
    extracted_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

class CandidateTimelineEvent(Base):
    __tablename__ = 'candidate_timeline_events'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    event_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

class EntityResolutionAudit(Base):
    __tablename__ = 'entity_resolution_audit'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    primary_candidate_id: Mapped[str] = mapped_column(String, nullable=False)
    merged_candidate_id: Mapped[str] = mapped_column(String, nullable=False)
    resolution_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    matching_criteria: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    merged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

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
