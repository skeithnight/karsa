"""Evolution delta value object -- Sprint-11. ADR-120."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvolutionDelta:
    """Measured change in capability metrics between before and after.

    Stores before/after snapshots for score, lifecycle state, and contract
    fingerprint. The score_change_bps is derived and validated.
    """

    before_score: float  # 0.0-1.0
    after_score: float  # 0.0-1.0
    score_change_bps: float  # derived: (after - before) * 10000
    before_lifecycle_state: str  # CapabilityLifecycleState enum value
    after_lifecycle_state: str  # CapabilityLifecycleState enum value
    before_contract_fingerprint: Optional[str]  # SHA-256 or None
    after_contract_fingerprint: Optional[str]  # SHA-256 or None

    def __post_init__(self) -> None:
        if not 0.0 <= self.before_score <= 1.0:
            raise ValueError(
                f"before_score must be 0.0-1.0, got {self.before_score}"
            )
        if not 0.0 <= self.after_score <= 1.0:
            raise ValueError(
                f"after_score must be 0.0-1.0, got {self.after_score}"
            )
        expected_bps = (self.after_score - self.before_score) * 10000
        if abs(self.score_change_bps - expected_bps) > 0.01:
            raise ValueError(
                f"score_change_bps must equal (after_score - before_score) * 10000. "
                f"Expected {expected_bps}, got {self.score_change_bps}"
            )
        if not self.before_lifecycle_state:
            raise ValueError("before_lifecycle_state is required")
        if not self.after_lifecycle_state:
            raise ValueError("after_lifecycle_state is required")
