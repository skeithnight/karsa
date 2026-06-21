"""Evolution attribution reference child entity -- Sprint-11. ADR-120."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionAttributionRef:
    """Child entity of CapabilityEvolution.

    Stored as JSONB within the parent aggregate.
    Not a separate aggregate -- no independent lifecycle.
    Links to the specific attribution contribution that triggered
    this evolution.
    """

    contribution_id: str
    dimension: str  # THESIS, EXECUTION, ALLOCATION, REGIME, RESIDUAL
    contribution_bps: float
    quality_score: float  # 0.0-1.0

    def _validate(self) -> None:
        if not self.contribution_id:
            raise ValueError("contribution_id is required")
        if not self.dimension:
            raise ValueError("dimension is required")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError(
                f"quality_score must be 0.0-1.0, got {self.quality_score}"
            )
