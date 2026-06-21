"""CapabilityEvolutionResponse -- Sprint-12. Wave-3.

Transport response DTO for capability evolution data.
No internal registry identifiers. No version registry metadata.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class CapabilityEvolutionResponse(BaseModel):
    """Response for GET /capabilities/{family_id}/evolution."""

    capability_family_id: str
    evaluation_id: str
    capability_urn: str
    total_evolutions: int = 0
    trigger_type_breakdown: Dict[str, int] = {}
    positive_evolutions: int = 0
    negative_evolutions: int = 0
    avg_score_change_bps: float = 0.0
    last_score_change_bps: float = 0.0
    last_evolution_type: str = ""
    last_evaluated_at: Optional[datetime] = None
