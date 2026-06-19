from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class AllocationReadinessDTO(BaseModel):
    worker_urn: str
    subject_type: str
    alpha_delta: float
    regime_type: Optional[str]

class GovernanceSuspensionDTO(BaseModel):
    worker_urn: str
    old_state: str
    new_state: str
    authority: str
    reason: str
    event_timestamp: datetime

class SwarmDiagnosticDTO(BaseModel):
    parent_worker_urn: Optional[str]
    child_worker_urn: str
    skill_ratio: float

class IntelligenceResponseDTO(BaseModel):
    data: List[dict]
    last_processed_sequence: int
    generated_at: datetime
