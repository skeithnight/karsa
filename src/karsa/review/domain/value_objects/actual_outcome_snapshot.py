"""ActualOutcomeSnapshot value object — Sprint-07 Wave-1."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AssumptionValidation:
    """Validation result for a single assumption."""
    assumption_id: str
    statement: str
    expected: str
    actual: str
    validated: bool
    impact_bps: float = 0.0


@dataclass(frozen=True)
class ActualOutcomeSnapshot:
    """Immutable snapshot of realized outcomes.

    Populated from PerformanceEvaluationCompletedEvent payload.
    """
    evaluation_id: str
    target_urn: str
    observation_window_days: int
    realized_return_bps: float
    realized_drawdown_pct: float
    realized_sharpe_ratio: float
    benchmark_return_bps: float
    regime_during_period: Optional[str]
    assumption_validations: List[AssumptionValidation] = field(default_factory=list)
    actual_attribution: Dict[str, float] = field(default_factory=dict)
    generated_at: Optional[str] = None  # ISO datetime

    def __post_init__(self):
        if not self.evaluation_id or not self.evaluation_id.strip():
            raise ValueError("evaluation_id cannot be empty.")
        if not self.target_urn or not self.target_urn.strip():
            raise ValueError("target_urn cannot be empty.")
        if self.observation_window_days <= 0:
            raise ValueError("observation_window_days must be positive.")
