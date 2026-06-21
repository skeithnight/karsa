"""Evolution evidence value object -- Sprint-11. ADR-120."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class EvolutionEvidence:
    """Provenance chain linking an evolution record to its source data.

    Every evolution must trace its origin to at least one review finding
    or attribution contribution. An evolution without provenance is rejected.
    """

    source_type: str  # REVIEW, ATTRIBUTION, EXECUTION, GOVERNANCE
    source_id: str  # URN of the source record
    finding_ids: List[str] = field(default_factory=list)
    attribution_contribution_ids: List[str] = field(default_factory=list)
    data_points: Dict = field(default_factory=dict)
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.source_type:
            raise ValueError("source_type is required")
        if not self.source_id:
            raise ValueError("source_id is required")
        if not self.finding_ids and not self.attribution_contribution_ids:
            raise ValueError(
                "At least one of finding_ids or attribution_contribution_ids "
                "is required for provenance"
            )
