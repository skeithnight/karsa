from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class TimelineEventDto(BaseModel):
    event_id: UUID
    stream_version: int
    causation_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    actor_urn: Optional[str] = None
    rationale: Optional[str] = None
    event_type: str
    timestamp: datetime

class ConfidencePointDto(BaseModel):
    id: UUID
    stream_version: int
    previous_confidence: float
    new_confidence: float
    delta: float
    rationale: Optional[str] = None
    event_type: str
    causation_id: Optional[UUID] = None
    timestamp: datetime

class AssumptionTimelineDto(BaseModel):
    event_id: UUID
    event_type: str
    actor_urn: Optional[str] = None
    rationale: Optional[str] = None
    timestamp: datetime

class AssumptionIntelligenceDto(BaseModel):
    assumption_urn: str
    statement: str
    is_valid: bool
    challenge_count: int
    timeline: List[AssumptionTimelineDto] = Field(default_factory=list)

class ThesisHealthDto(BaseModel):
    thesis_urn: str
    lifecycle_state: str
    confidence: float
    total_assumptions: int
    valid_assumptions: int
    challenged_assumptions: int
    invalid_assumptions: int
    health_score: float
    health_status: str
    snapshot_version: int
