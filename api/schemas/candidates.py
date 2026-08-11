from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class CandidateBase(BaseModel):
    first_name: str
    last_name: str
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    current_city: Optional[str] = None
    current_country: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    total_yoe: float = 0.0
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    currency: str = "USD"
    availability_status: str = "ACTIVE"
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)

class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CandidateStatusUpdate(BaseModel):
    new_status: str
    recruiter_name: str
    reason: Optional[str] = None

class TimelineEventResponse(BaseModel):
    id: str
    candidate_id: str
    event_type: str
    title: str
    description: Optional[str] = None
    event_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
