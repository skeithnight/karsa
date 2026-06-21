"""GovernanceStatusResponse -- Sprint-12. Wave-3.

Transport response DTO for capability governance status.
"""

from pydantic import BaseModel


class GovernanceStatusResponse(BaseModel):
    """Response for GET /capabilities/{family_id}/governance."""

    capability_family_id: str
    status: str  # ACTIVE, SUSPENDED
    consecutive_low_scores: int = 0
    consecutive_high_scores: int = 0
    suspension_threshold: int = 3
    unsuspension_threshold: int = 2
