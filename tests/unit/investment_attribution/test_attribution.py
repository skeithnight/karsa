"""Tests for Investment Attribution -- Sprint-18.

Covers:
- AttributionBreakdown validation and computation
- WinRate computation
- PerformanceSnapshot computation
- AttributionService operations
"""

import pytest
from datetime import date

from karsa.investment_attribution.application.attribution_service import (
    AttributionService,
    ComputeAttributionCommand,
    RecordSnapshotCommand,
)
from karsa.investment_attribution.domain.exceptions import (
    InvalidAttributionError,
    InvalidPerformanceError,
)
from karsa.investment_attribution.domain.value_objects.attribution_breakdown import (
    AttributionBreakdown,
)
from karsa.investment_attribution.domain.value_objects.enums import (
    AttributionDimension,
    PerformancePeriod,
    WinRateCategory,
)
from karsa.investment_attribution.domain.value_objects.performance_snapshot import (
    PerformanceSnapshot,
)
from karsa.investment_attribution.domain.value_objects.win_rate import WinRate
from karsa.investment_attribution.infrastructure.persistence.in_memory_performance_snapshot_repository import (
    InMemoryPerformanceSnapshotRepository,
)


class TestAttributionBreakdown:
    """AttributionBreakdown value object."""

    def test_compute(self):
        ab = AttributionBreakdown.compute(
            selection_pct=8.2,
            allocation_pct=3.1,
            beta_pct=2.4,
            residual_pct=-0.2,
        )
        assert ab.total_return_pct == pytest.approx(13.5)
        assert ab.selection_pct == 8.2

    def test_components_must_sum_to_total(self):
        with pytest.raises(InvalidAttributionError, match="sum"):
            AttributionBreakdown(
                selection_pct=8.0,
                allocation_pct=3.0,
                beta_pct=2.0,
                residual_pct=-0.5,
                total_return_pct=20.0,  # doesn't match
            )

    def test_frozen(self):
        ab = AttributionBreakdown.compute(1.0, 2.0, 3.0, 0.0)
        with pytest.raises(AttributeError):
            ab.selection_pct = 10.0

    def test_positive_selection(self):
        ab = AttributionBreakdown.compute(5.0, 0.0, 0.0, 0.0)
        assert ab.is_positive_selection

    def test_negative_selection(self):
        ab = AttributionBreakdown.compute(-5.0, 0.0, 0.0, 0.0)
        assert not ab.is_positive_selection

    def test_dominant_dimension(self):
        ab = AttributionBreakdown.compute(8.0, 3.0, 2.0, -0.2)
        assert ab.dominant_dimension == "SELECTION"

    def test_all_zero(self):
        ab = AttributionBreakdown.compute(0.0, 0.0, 0.0, 0.0)
        assert ab.total_return_pct == 0.0


class TestWinRate:
    """WinRate value object."""

    def test_compute_with_returns(self):
        returns = [5.0, -2.0, 8.0, -1.0, 3.0]
        wr = WinRate.compute("OVERALL", returns)
        assert wr.total_decisions == 5
        assert wr.winning_decisions == 3
        assert wr.win_rate_pct == pytest.approx(60.0)

    def test_compute_empty(self):
        wr = WinRate.compute("OVERALL", [])
        assert wr.total_decisions == 0
        assert wr.win_rate_pct == 0.0

    def test_all_winners(self):
        wr = WinRate.compute("FUNDAMENTAL", [1.0, 2.0, 3.0])
        assert wr.win_rate_pct == 100.0

    def test_all_losers(self):
        wr = WinRate.compute("TECHNICAL", [-1.0, -2.0, -3.0])
        assert wr.win_rate_pct == 0.0

    def test_frozen(self):
        wr = WinRate.compute("OVERALL", [1.0, -1.0])
        with pytest.raises(AttributeError):
            wr.category = "FUNDAMENTAL"

    def test_avg_returns(self):
        returns = [10.0, -5.0]
        wr = WinRate.compute("OVERALL", returns)
        assert wr.avg_return_pct == pytest.approx(2.5)
        assert wr.avg_winner_return_pct == pytest.approx(10.0)
        assert wr.avg_loser_return_pct == pytest.approx(-5.0)


class TestPerformanceSnapshot:
    """PerformanceSnapshot value object."""

    def test_compute(self):
        ps = PerformanceSnapshot.compute(
            snapshot_date=date(2026, 6, 15),
            nav=10_200_000_000,
            benchmark_close=7500.0,
            portfolio_beta=1.05,
            sharpe_ytd=1.8,
            max_drawdown_ytd=0.082,
            previous_nav=10_000_000_000,
            previous_benchmark=7400.0,
        )
        assert ps.nav == 10_200_000_000
        assert ps.nav_pct_change == pytest.approx(2.0)
        assert ps.benchmark_pct_change > 0

    def test_frozen(self):
        ps = PerformanceSnapshot.compute(
            snapshot_date=date(2026, 6, 15),
            nav=10_000_000_000,
            benchmark_close=7500.0,
            portfolio_beta=1.0,
            sharpe_ytd=1.5,
            max_drawdown_ytd=0.1,
        )
        with pytest.raises(AttributeError):
            ps.nav = 0

    def test_invalid_nav(self):
        with pytest.raises(InvalidPerformanceError):
            PerformanceSnapshot.compute(
                snapshot_date=date(2026, 6, 15),
                nav=0,
                benchmark_close=7500.0,
                portfolio_beta=1.0,
                sharpe_ytd=1.5,
                max_drawdown_ytd=0.1,
            )

    def test_invalid_drawdown(self):
        with pytest.raises(InvalidPerformanceError):
            PerformanceSnapshot.compute(
                snapshot_date=date(2026, 6, 15),
                nav=10_000_000_000,
                benchmark_close=7500.0,
                portfolio_beta=1.0,
                sharpe_ytd=1.5,
                max_drawdown_ytd=1.5,  # > 1.0
            )


class TestAttributionService:
    """AttributionService application service."""

    def _make_service(self):
        repo = InMemoryPerformanceSnapshotRepository()
        return AttributionService(snapshot_repo=repo), repo

    def test_record_snapshot(self):
        service, repo = self._make_service()
        cmd = RecordSnapshotCommand(
            snapshot_date=date(2026, 6, 15),
            nav=10_200_000_000,
            benchmark_close=7500.0,
            portfolio_beta=1.05,
            sharpe_ytd=1.8,
            max_drawdown_ytd=0.082,
            previous_nav=10_000_000_000,
            previous_benchmark=7400.0,
        )
        result = service.record_snapshot(cmd)
        assert result.success is True
        assert len(result.events) == 1

    def test_duplicate_snapshot_rejected(self):
        service, _ = self._make_service()
        cmd = RecordSnapshotCommand(
            snapshot_date=date(2026, 6, 15),
            nav=10_000_000_000,
            benchmark_close=7500.0,
            portfolio_beta=1.0,
            sharpe_ytd=1.5,
            max_drawdown_ytd=0.1,
        )
        service.record_snapshot(cmd)
        result = service.record_snapshot(cmd)
        assert result.success is False

    def test_compute_attribution(self):
        service, _ = self._make_service()
        cmd = ComputeAttributionCommand(
            period="YTD",
            portfolio_return_pct=13.5,
            benchmark_return_pct=10.0,
            portfolio_beta=1.05,
            holdings=[
                {"ticker": "BBCA", "weight": 12.5, "return": 15.0, "benchmark_weight": 10.0},
                {"ticker": "ASII", "weight": 10.2, "return": 8.0, "benchmark_weight": 8.0},
            ],
        )
        result = service.compute_attribution(cmd)
        assert result.success is True
        assert result.attribution is not None
        assert result.attribution.total_return_pct == pytest.approx(13.5)

    def test_compute_win_rate(self):
        service, _ = self._make_service()
        returns = [5.0, -2.0, 8.0, -1.0, 3.0]
        wr = service.compute_win_rate("FUNDAMENTAL", returns)
        assert wr.win_rate_pct == pytest.approx(60.0)
        assert wr.total_decisions == 5

    def test_get_snapshots(self):
        service, repo = self._make_service()
        for i in range(5):
            cmd = RecordSnapshotCommand(
                snapshot_date=date(2026, 6, 10 + i),
                nav=10_000_000_000 + i * 100_000_000,
                benchmark_close=7500.0,
                portfolio_beta=1.0,
                sharpe_ytd=1.5,
                max_drawdown_ytd=0.1,
            )
            service.record_snapshot(cmd)

        snapshots = service.get_snapshots(limit=3)
        assert len(snapshots) == 3

    def test_get_latest_snapshot(self):
        service, _ = self._make_service()
        cmd = RecordSnapshotCommand(
            snapshot_date=date(2026, 6, 15),
            nav=10_200_000_000,
            benchmark_close=7500.0,
            portfolio_beta=1.05,
            sharpe_ytd=1.8,
            max_drawdown_ytd=0.082,
        )
        service.record_snapshot(cmd)

        latest = service.get_latest_snapshot()
        assert latest is not None
        assert latest.nav == 10_200_000_000


class TestEnums:
    """Enum completeness."""

    def test_attribution_dimensions(self):
        assert len(AttributionDimension) == 4
        assert AttributionDimension.SELECTION.value == "SELECTION"

    def test_performance_periods(self):
        assert len(PerformancePeriod) == 7

    def test_win_rate_categories(self):
        assert len(WinRateCategory) == 5
