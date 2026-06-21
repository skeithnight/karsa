"""Investment Attribution domain events -- Sprint-18.

All events are frozen dataclasses.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AttributionComputedEvent:
    """Published when attribution decomposition is computed."""

    event_id: str
    period: str  # PerformancePeriod value
    total_return_pct: float
    selection_pct: float
    allocation_pct: float
    beta_pct: float
    residual_pct: float
    computed_at: str = ""

    event_sequence: int = 0
    event_type: str = "AttributionComputedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "period": self.period,
            "total_return_pct": self.total_return_pct,
            "selection_pct": self.selection_pct,
            "allocation_pct": self.allocation_pct,
            "beta_pct": self.beta_pct,
            "residual_pct": self.residual_pct,
            "computed_at": self.computed_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class PerformanceSnapshotRecordedEvent:
    """Published when a daily performance snapshot is recorded."""

    event_id: str
    snapshot_date: str
    nav: float
    nav_pct_change: float
    alpha: float
    recorded_at: str = ""

    event_sequence: int = 0
    event_type: str = "PerformanceSnapshotRecordedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "snapshot_date": self.snapshot_date,
            "nav": self.nav,
            "nav_pct_change": self.nav_pct_change,
            "alpha": self.alpha,
            "recorded_at": self.recorded_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class WinRateComputedEvent:
    """Published when win rate analysis is computed."""

    event_id: str
    category: str
    win_rate_pct: float
    total_decisions: int
    winning_decisions: int
    computed_at: str = ""

    event_sequence: int = 0
    event_type: str = "WinRateComputedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "category": self.category,
            "win_rate_pct": self.win_rate_pct,
            "total_decisions": self.total_decisions,
            "winning_decisions": self.winning_decisions,
            "computed_at": self.computed_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }
