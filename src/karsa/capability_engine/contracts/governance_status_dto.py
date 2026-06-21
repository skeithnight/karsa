"""GovernanceStatusDTO -- Sprint-11. Wave-8.

Public contract for capability governance lifecycle state.
ADR-138: Suspension/unsuspension status.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class GovernanceStatusDTO:
    """Public contract for capability governance status.

    Reflects suspension state from ADR-138 governance counters.
    """

    capability_family_id: str
    capability_urn: str
    lifecycle_state: str  # ACTIVE, SUSPENDED
    consecutive_low_scores: int
    consecutive_high_scores: int
    suspension_threshold: int = 3  # ADR-138
    unsuspension_threshold: int = 2  # ADR-138
    is_suspended: bool = False
    suspension_reason: Optional[str] = None
    last_evaluated_at: Optional[datetime] = None
