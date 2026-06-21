"""CapabilityHealthResponse -- Sprint-12. Wave-3.

Transport response DTO for capability health data.
No projection leakage. No domain types.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CapabilityHealthResponse(BaseModel):
    """Response for GET /capabilities/{family_id}/health."""

    capability_family_id: str
    current_score: float = Field(ge=0.0, le=1.0)
    algorithm_version: str
    execution_quality_score: float = 0.0
    attribution_alignment_score: float = 0.0
    review_sentiment_score: float = 0.0
    regime_fitness_score: float = 0.0
    evaluation_count: int = 0
    data_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    score_trend: str = "UNKNOWN"
    lifecycle_state: str = "ACTIVE"
    consecutive_low_scores: int = 0
    consecutive_high_scores: int = 0
    last_evaluated_at: Optional[datetime] = None
