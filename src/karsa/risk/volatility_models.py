"""Sprint-58: Live Risk — Volatility Targeting domain models.

AssetRiskMetrics, VolatilityEstimate, RiskCalibrationResult, EWMAParameters, RiskTarget.
Extends the existing risk/ bounded context.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class EWMAParameters:
    """Parameters for EWMA volatility estimation."""
    span_days: int = 20
    annualization_factor: int = 252  # Trading days per year

    @property
    def decay_factor(self) -> float:
        """Lambda = 1 - 2/(span+1) — standard EWMA decay."""
        return 1.0 - (2.0 / (self.span_days + 1.0))


@dataclass(frozen=True)
class RiskTarget:
    """Target risk per trade in USD."""
    target_risk_per_trade_usd: float = 10_000.0


@dataclass
class AssetRiskMetrics:
    """Point-in-time risk metrics for a single asset.

    Updated by VolatilityCalculator on each new bar.
    Read by RiskCalibrationEngine for position sizing.
    """
    symbol: str = ""
    timeframe: str = "1d"
    realized_volatility: float = 0.0  # Annualized (e.g., 0.245 = 24.5%)
    beta_to_spy: Optional[float] = None
    var_95: Optional[float] = None
    daily_vol_pct: float = 0.0  # Daily volatility as percentage
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class VolatilityEstimate:
    """Value object: a volatility estimate for a symbol."""
    symbol: str = ""
    annualized_vol: float = 0.0
    daily_vol_pct: float = 0.0
    calculation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        """Check if the estimate is valid (not NaN, not zero, not stale)."""
        import math
        return (
            self.annualized_vol > 0.0
            and not math.isnan(self.annualized_vol)
            and not math.isinf(self.annualized_vol)
        )


@dataclass(frozen=True)
class RiskCalibrationResult:
    """Value object: result of risk calibration for a thesis."""
    thesis_id: str = ""
    ticker: str = ""
    original_quantity: float = 0.0
    calibrated_quantity: float = 0.0
    risk_scaling_applied: bool = False
    target_risk_usd: float = 10_000.0
    daily_vol_pct: float = 0.0
    daily_price_vol_usd: float = 0.0
    reason: str = ""
    volatility_estimate: Optional[VolatilityEstimate] = None

    @property
    def scaling_factor(self) -> float:
        """Ratio of calibrated to original quantity."""
        if self.original_quantity <= 0:
            return 1.0
        return self.calibrated_quantity / self.original_quantity
