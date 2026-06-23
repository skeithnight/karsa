"""Sprint-58: Live Risk — Volatility Targeting events.

RiskScalingAppliedEvent follows existing risk/events.py frozen dataclass pattern.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class RiskScalingAppliedEvent:
    """Emitted when risk calibration overrides a thesis position size.

    Follows existing risk/events.py pattern with event_id, correlation_id,
    causation_id, timestamp, and event_version.
    """
    event_id: str
    correlation_id: str  # thesis_id
    causation_id: str  # ThesisApprovedEvent event_id
    timestamp: datetime
    thesis_id: str
    ticker: str
    original_qty: float
    calibrated_qty: float
    risk_scaling_applied: bool
    reason: str
    annualized_vol: float
    daily_vol_pct: float
    target_risk_usd: float
    event_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "timestamp": self.timestamp.isoformat(),
            "thesis_id": self.thesis_id,
            "ticker": self.ticker,
            "original_qty": self.original_qty,
            "calibrated_qty": self.calibrated_qty,
            "risk_scaling_applied": self.risk_scaling_applied,
            "reason": self.reason,
            "annualized_vol": self.annualized_vol,
            "daily_vol_pct": self.daily_vol_pct,
            "target_risk_usd": self.target_risk_usd,
            "event_version": self.event_version,
        }
