"""Score history entry value object -- Sprint-11. ADR-132, ADR-134, ADR-136."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class ScoreHistoryEntry:
    """Timestamped snapshot of a capability's score at a specific evaluation.

    Stored in the capability_score_history table (not embedded in the
    aggregate JSONB). Append-only -- no deletion or modification of
    historical entries.
    """

    capability_family_id: str  # FK to capability definition family
    evaluation_id: str
    evaluation_sequence: int  # ADR-136: monotonic ordering
    capability_version_id: str  # ADR-137: version boundary tracking
    score: float  # 0.0-1.0
    algorithm_version: str  # ADR-134: scoring algorithm versioning
    components: List = field(default_factory=list)  # List[CapabilityScoreComponent]
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.capability_family_id:
            raise ValueError("capability_family_id is required")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"score must be 0.0-1.0, got {self.score}"
            )
        if not self.evaluation_id:
            raise ValueError("evaluation_id is required")
        if self.evaluation_sequence < 0:
            raise ValueError(
                f"evaluation_sequence must be >= 0, got "
                f"{self.evaluation_sequence}"
            )
        if not self.capability_version_id:
            raise ValueError("capability_version_id is required")
        if not self.algorithm_version:
            raise ValueError("algorithm_version is required")
