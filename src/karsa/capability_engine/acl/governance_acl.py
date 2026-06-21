"""GovernanceACL -- Sprint-11. Wave-8.

Anti-corruption layer for Governance events.
Translates governance state into capability engine DTOs.

Prevents Governance Engine types from leaking into
the Capability Engine domain.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from karsa.capability_engine.contracts.governance_status_dto import (
    GovernanceStatusDTO,
)

# ADR-138 thresholds
SUSPENSION_THRESHOLD = 3
UNSUSPENSION_THRESHOLD = 2


class GovernanceACL:
    """Translates governance state into Capability Engine DTOs.

    Maps health score governance counters (ADR-138) into the
    public GovernanceStatusDTO without exposing the aggregate.
    """

    def translate_health_score_to_governance_status(
        self,
        capability_family_id: str,
        capability_urn: str,
        consecutive_low_scores: int,
        consecutive_high_scores: int,
        last_evaluated_at: Optional[datetime] = None,
    ) -> GovernanceStatusDTO:
        """Map health score governance counters to governance status DTO.

        ADR-138: Suspension after 3 consecutive low scores.
        Unsuspension after 2 consecutive high scores.
        """
        is_suspended = consecutive_low_scores >= SUSPENSION_THRESHOLD
        lifecycle_state = "SUSPENDED" if is_suspended else "ACTIVE"

        suspension_reason = None
        if is_suspended:
            suspension_reason = (
                f"Consecutive low scores ({consecutive_low_scores}) "
                f">= threshold ({SUSPENSION_THRESHOLD})"
            )

        return GovernanceStatusDTO(
            capability_family_id=capability_family_id,
            capability_urn=capability_urn,
            lifecycle_state=lifecycle_state,
            consecutive_low_scores=consecutive_low_scores,
            consecutive_high_scores=consecutive_high_scores,
            suspension_threshold=SUSPENSION_THRESHOLD,
            unsuspension_threshold=UNSUSPENSION_THRESHOLD,
            is_suspended=is_suspended,
            suspension_reason=suspension_reason,
            last_evaluated_at=last_evaluated_at,
        )

    def translate_from_projection(
        self, projection: Dict[str, Any]
    ) -> GovernanceStatusDTO:
        """Translate a health projection dict into governance status DTO."""
        return self.translate_health_score_to_governance_status(
            capability_family_id=projection.get(
                "capability_family_id", ""
            ),
            capability_urn=projection.get("capability_urn", ""),
            consecutive_low_scores=projection.get(
                "consecutive_low_scores", 0
            ),
            consecutive_high_scores=projection.get(
                "consecutive_high_scores", 0
            ),
            last_evaluated_at=projection.get("last_evaluated_at"),
        )
