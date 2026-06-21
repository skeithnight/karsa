"""CapabilityEvolutionProjection DTO -- Sprint-11. ADR-120, ADR-133."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class CapabilityEvolutionProjection:
    """Read model for capability evolution summaries.

    Rebuilt from capability_evolutions JOIN capability_evolution_version_registry.
    Only canonical records contribute to this projection (ADR-133).
    """

    capability_family_id: str  # UUID
    evaluation_id: str  # UUID
    capability_urn: str  # URN of capability at evolution time
    total_evolutions: int = 0
    trigger_type_breakdown: Dict[str, int] = field(default_factory=dict)
    positive_evolutions: int = 0
    negative_evolutions: int = 0
    avg_score_change_bps: float = 0.0
    last_score_change_bps: float = 0.0
    last_evolution_type: str = ""
    last_evaluated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.capability_family_id:
            raise ValueError("capability_family_id is required")
        if not self.evaluation_id:
            raise ValueError("evaluation_id is required")
        if not self.capability_urn:
            raise ValueError("capability_urn is required")
        if self.total_evolutions < 0:
            raise ValueError(
                f"total_evolutions must be >= 0, got {self.total_evolutions}"
            )
        if self.positive_evolutions < 0:
            raise ValueError(
                f"positive_evolutions must be >= 0, got {self.positive_evolutions}"
            )
        if self.negative_evolutions < 0:
            raise ValueError(
                f"negative_evolutions must be >= 0, got {self.negative_evolutions}"
            )
