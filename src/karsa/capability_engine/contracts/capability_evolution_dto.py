"""CapabilityEvolutionDTO -- Sprint-11. Wave-8.

Read-only contract for capability evolution data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class CapabilityEvolutionDTO:
    """Public contract for capability evolution summary.

    Maps from CapabilityEvolutionProjection.
    Only canonical records are exposed (ADR-133).
    """

    capability_family_id: str
    evaluation_id: str
    capability_urn: str
    total_evolutions: int = 0
    trigger_type_breakdown: Dict[str, int] = field(default_factory=dict)
    positive_evolutions: int = 0
    negative_evolutions: int = 0
    avg_score_change_bps: float = 0.0
    last_score_change_bps: float = 0.0
    last_evolution_type: str = ""
    last_evaluated_at: Optional[datetime] = None
