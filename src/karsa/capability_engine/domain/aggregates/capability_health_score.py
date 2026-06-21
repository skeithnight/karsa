"""CapabilityHealthScore aggregate -- Sprint-11. ADR-132."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from karsa.capability_engine.domain.exceptions import InvalidHealthScoreError
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)


@dataclass
class CapabilityHealthScore:
    """Mutable aggregate tracking a capability's composite health over time.

    ADR-132: Separate aggregate from CapabilityEvolution because of
    different mutability contract (mutable vs. write-once), different
    concurrency model (OCC vs. ON CONFLICT), and different access
    pattern (hot read path vs. write-once audit).

    History is stored in a separate capability_score_history table,
    not embedded in this aggregate's JSONB. This prevents unbounded
    aggregate growth.

    One health score per capability_family (not per version).
    """

    # Identity
    health_score_id: str  # UUID
    capability_family_id: str  # UUID, immutable after creation

    # Current composite score
    current_score: float = 0.5  # 0.0-1.0, default neutral

    # Component breakdown
    score_components: List[CapabilityScoreComponent] = field(
        default_factory=list
    )

    # Evaluation metadata
    evaluation_count: int = 0
    last_evaluated_at: Optional[datetime] = None

    # ADR-137: Version boundary tracking
    current_version_id: Optional[str] = None  # active capability version
    last_recorded_sequence: int = 0  # ADR-136: ordering guard

    # ADR-138: Governance counters
    consecutive_low_scores: int = 0
    consecutive_high_scores: int = 0

    # ADR-134: Algorithm versioning
    algorithm_version: str = "v1.0"

    # OCC version
    aggregate_version: int = 1

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._validate()

    @property
    def aggregate_id(self) -> str:
        return self.capability_family_id

    def _validate(self) -> None:
        if not self.health_score_id:
            raise InvalidHealthScoreError("health_score_id is required")
        if not self.capability_family_id:
            raise InvalidHealthScoreError("capability_family_id is required")
        if not 0.0 <= self.current_score <= 1.0:
            raise InvalidHealthScoreError(
                f"current_score must be 0.0-1.0, got {self.current_score}"
            )
        if self.evaluation_count < 0:
            raise InvalidHealthScoreError(
                f"evaluation_count must be >= 0, got {self.evaluation_count}"
            )
        if self.consecutive_low_scores < 0:
            raise InvalidHealthScoreError(
                "consecutive_low_scores must be >= 0"
            )
        if self.consecutive_high_scores < 0:
            raise InvalidHealthScoreError(
                "consecutive_high_scores must be >= 0"
            )
        # Validate components
        for c in self.score_components:
            c._validate() if hasattr(c, "_validate") else None

    def increment_version(self) -> None:
        """Bump aggregate version for OCC."""
        self.aggregate_version += 1

    def record_evaluation(
        self,
        score: float,
        components: List[CapabilityScoreComponent],
        evaluation_sequence: int,
        algorithm_version: str,
        low_threshold: float = 0.3,
        high_threshold: float = 0.7,
    ) -> None:
        """Record a new evaluation result.

        ADR-136: Enforces monotonic evaluation ordering.
        ADR-138: Updates consecutive score counters for governance.
        """
        if evaluation_sequence <= self.last_recorded_sequence:
            raise InvalidHealthScoreError(
                f"evaluation_sequence {evaluation_sequence} must be > "
                f"last_recorded_sequence {self.last_recorded_sequence}"
            )
        if not 0.0 <= score <= 1.0:
            raise InvalidHealthScoreError(
                f"score must be 0.0-1.0, got {score}"
            )

        self.current_score = score
        self.score_components = components
        self.evaluation_count += 1
        self.last_evaluated_at = datetime.utcnow()
        self.last_recorded_sequence = evaluation_sequence
        self.algorithm_version = algorithm_version
        self.updated_at = datetime.utcnow()

        # ADR-138: Governance consecutive counters
        if score < low_threshold:
            self.consecutive_low_scores += 1
            self.consecutive_high_scores = 0
        elif score > high_threshold:
            self.consecutive_high_scores += 1
            self.consecutive_low_scores = 0
        else:
            # Neutral zone: reset both counters
            self.consecutive_low_scores = 0
            self.consecutive_high_scores = 0

        self.increment_version()
