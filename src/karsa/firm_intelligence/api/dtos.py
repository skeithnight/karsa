from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class AllocationRankingExplanation(BaseModel):
    reward_factor: float
    risk_penalty: float
    final_score: float

class AllocationReadinessDTO(BaseModel):
    worker_urn: str
    eligibility_status: str
    cumulative_alpha: float
    max_drawdown: float
    observation_count: int
    ranking_explanation: AllocationRankingExplanation

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
