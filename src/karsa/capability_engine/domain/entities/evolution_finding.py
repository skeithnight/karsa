"""Evolution finding child entity -- Sprint-11. ADR-120."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionFinding:
    """Child entity of CapabilityEvolution.

    Stored as JSONB within the parent aggregate.
    Not a separate aggregate -- no independent lifecycle.
    Links to the specific review finding that triggered this evolution.
    """

    finding_id: str
    finding_type: str  # CONCERN, RISK, OPPORTUNITY
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    dimension: str  # THESIS, EXECUTION, ALLOCATION, REGIME, PORTFOLIO
    description: str

    def _validate(self) -> None:
        if not self.finding_id:
            raise ValueError("finding_id is required")
        if not self.finding_type:
            raise ValueError("finding_type is required")
        if not self.severity:
            raise ValueError("severity is required")
        if not self.dimension:
            raise ValueError("dimension is required")
        if not self.description:
            raise ValueError("description is required")
