"""AttributionService -- Sprint-18.

Application service for performance attribution decomposition
and win rate analysis.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from karsa.investment_attribution.domain.events.attribution_events import (
    AttributionComputedEvent,
    PerformanceSnapshotRecordedEvent,
    WinRateComputedEvent,
)
from karsa.investment_attribution.domain.value_objects.attribution_breakdown import (
    AttributionBreakdown,
)
from karsa.investment_attribution.domain.value_objects.enums import (
    PerformancePeriod,
    WinRateCategory,
)
from karsa.investment_attribution.domain.value_objects.performance_snapshot import (
    PerformanceSnapshot,
)
from karsa.investment_attribution.domain.value_objects.win_rate import WinRate
from karsa.investment_attribution.infrastructure.repositories.performance_snapshot_repository import (
    PerformanceSnapshotRepository,
)


@dataclass
class RecordSnapshotCommand:
    """Input DTO for recording a daily snapshot."""

    snapshot_date: date
    nav: float
    benchmark_close: float
    portfolio_beta: float
    sharpe_ytd: float
    max_drawdown_ytd: float
    previous_nav: Optional[float] = None
    previous_benchmark: Optional[float] = None


@dataclass
class ComputeAttributionCommand:
    """Input DTO for computing attribution."""

    period: str  # PerformancePeriod value
    portfolio_return_pct: float
    benchmark_return_pct: float
    portfolio_beta: float
    holdings: List[Dict[str, Any]]  # [{ticker, weight, return, benchmark_weight}]


@dataclass
class AttributionResult:
    """Output DTO from attribution operations."""

    success: bool
    message: str
    attribution: Optional[AttributionBreakdown] = None
    events: Optional[List] = None


class AttributionService:
    """Application service for performance attribution."""

    def __init__(
        self,
        snapshot_repo: PerformanceSnapshotRepository,
    ) -> None:
        self._snapshot_repo = snapshot_repo

    def record_snapshot(
        self, command: RecordSnapshotCommand
    ) -> AttributionResult:
        """Record a daily performance snapshot."""
        snapshot = PerformanceSnapshot.compute(
            snapshot_date=command.snapshot_date,
            nav=command.nav,
            benchmark_close=command.benchmark_close,
            portfolio_beta=command.portfolio_beta,
            sharpe_ytd=command.sharpe_ytd,
            max_drawdown_ytd=command.max_drawdown_ytd,
            previous_nav=command.previous_nav,
            previous_benchmark=command.previous_benchmark,
        )

        saved = self._snapshot_repo.save(snapshot)
        if not saved:
            return AttributionResult(
                success=False,
                message=f"Snapshot for {command.snapshot_date} already exists",
            )

        event = PerformanceSnapshotRecordedEvent(
            event_id=str(uuid.uuid4()),
            snapshot_date=str(command.snapshot_date),
            nav=snapshot.nav,
            nav_pct_change=snapshot.nav_pct_change,
            alpha=snapshot.alpha,
            recorded_at=datetime.utcnow().isoformat(),
        )

        return AttributionResult(
            success=True,
            message="Snapshot recorded",
            events=[event],
        )

    def compute_attribution(
        self, command: ComputeAttributionCommand
    ) -> AttributionResult:
        """Compute performance attribution decomposition.

        Brinson-Fachler model:
        - Selection: Σ(wp - wb) * (rb - R)
        - Allocation: Σ(wp - wb) * (Rb - rb)
        - Beta: portfolio_beta * benchmark_return
        - Residual: total - selection - allocation - beta

        Where:
        - wp = portfolio weight
        - wb = benchmark weight
        - rb = holding return
        - R = benchmark return
        - Rb = benchmark sector return (simplified: benchmark return)
        """
        portfolio_return = command.portfolio_return_pct / 100
        benchmark_return = command.benchmark_return_pct / 100

        selection = 0.0
        allocation = 0.0

        for h in command.holdings:
            wp = h.get("weight", 0) / 100  # portfolio weight
            wb = h.get("benchmark_weight", 0) / 100  # benchmark weight
            rb = h.get("return", 0) / 100  # holding return

            # Selection: overweight winners, underweight losers
            selection += (wp - wb) * (rb - benchmark_return)

            # Allocation: overweight sectors that outperform
            allocation += (wp - wb) * (benchmark_return - benchmark_return)
            # Simplified: allocation ≈ 0 without sector-level benchmarks

        # Beta component
        beta = command.portfolio_beta * benchmark_return

        # Residual
        residual = portfolio_return - selection - allocation - beta

        breakdown = AttributionBreakdown.compute(
            selection_pct=round(selection * 100, 4),
            allocation_pct=round(allocation * 100, 4),
            beta_pct=round(beta * 100, 4),
            residual_pct=round(residual * 100, 4),
        )

        event = AttributionComputedEvent(
            event_id=str(uuid.uuid4()),
            period=command.period,
            total_return_pct=breakdown.total_return_pct,
            selection_pct=breakdown.selection_pct,
            allocation_pct=breakdown.allocation_pct,
            beta_pct=breakdown.beta_pct,
            residual_pct=breakdown.residual_pct,
            computed_at=datetime.utcnow().isoformat(),
        )

        return AttributionResult(
            success=True,
            message="Attribution computed",
            attribution=breakdown,
            events=[event],
        )

    def compute_win_rate(
        self,
        category: str,
        realized_returns: List[float],
    ) -> WinRate:
        """Compute win rate for a category of decisions."""
        return WinRate.compute(category, realized_returns)

    def get_snapshots(self, limit: int = 30) -> List[PerformanceSnapshot]:
        """Get recent performance snapshots."""
        return self._snapshot_repo.list_snapshots(limit)

    def get_latest_snapshot(self) -> Optional[PerformanceSnapshot]:
        """Get the most recent snapshot."""
        return self._snapshot_repo.get_latest()
