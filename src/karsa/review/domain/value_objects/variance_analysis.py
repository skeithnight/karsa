"""VarianceAnalysis value object — Sprint-07 Wave-1."""
from dataclasses import dataclass


@dataclass(frozen=True)
class VarianceAnalysis:
    """Computed variance between expected and actual outcomes.

    All values are immutable once computed.
    """
    return_variance_bps: float
    drawdown_variance_pct: float
    sharpe_variance: float
    confidence_accuracy: float  # 0.0–1.0
    assumption_accuracy: float  # 0.0–1.0
    overall_accuracy: float  # 0.0–1.0

    def __post_init__(self):
        for field_name in ("confidence_accuracy", "assumption_accuracy", "overall_accuracy"):
            value = getattr(self, field_name)
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")

    @classmethod
    def compute(
        cls,
        expected_return_bps: float,
        expected_drawdown_pct: float,
        expected_sharpe_ratio: float,
        realized_return_bps: float,
        realized_drawdown_pct: float,
        realized_sharpe_ratio: float,
        confidence_level: float,
        assumption_validations: list,
    ) -> "VarianceAnalysis":
        """Computes variance from expected and actual outcomes."""
        return_var = realized_return_bps - expected_return_bps
        dd_var = realized_drawdown_pct - expected_drawdown_pct
        sharpe_var = realized_sharpe_ratio - expected_sharpe_ratio

        # Confidence accuracy: how close was the confidence prediction
        # If return met/exceeded expectation, confidence was accurate
        return_met = realized_return_bps >= expected_return_bps
        confidence_acc = confidence_level if return_met else (1.0 - confidence_level)

        # Assumption accuracy: fraction of assumptions validated
        if assumption_validations:
            validated_count = sum(1 for a in assumption_validations if a.validated)
            assumption_acc = validated_count / len(assumption_validations)
        else:
            assumption_acc = 1.0  # No assumptions = no failures

        # Overall accuracy: weighted combination
        overall = 0.4 * confidence_acc + 0.3 * assumption_acc + 0.3 * max(0, 1.0 - abs(return_var) / max(abs(expected_return_bps), 1.0))

        return cls(
            return_variance_bps=round(return_var, 4),
            drawdown_variance_pct=round(dd_var, 4),
            sharpe_variance=round(sharpe_var, 4),
            confidence_accuracy=round(confidence_acc, 4),
            assumption_accuracy=round(assumption_acc, 4),
            overall_accuracy=round(min(1.0, max(0.0, overall)), 4),
        )
