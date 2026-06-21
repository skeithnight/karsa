"""PerformanceSnapshot value object -- Sprint-18."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from karsa.investment_attribution.domain.exceptions import InvalidPerformanceError


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Daily performance snapshot for attribution tracking."""

    snapshot_date: date
    nav: float  # Net Asset Value
    nav_pct_change: float  # daily return
    benchmark_close: float  # IHSG close
    benchmark_pct_change: float  # benchmark daily return
    alpha: float  # nav_pct_change - benchmark_pct_change
    portfolio_beta: float  # rolling beta vs benchmark
    sharpe_ytd: float
    max_drawdown_ytd: float

    def __post_init__(self) -> None:
        if self.nav <= 0:
            raise InvalidPerformanceError("nav must be > 0")
        if not 0.0 <= self.max_drawdown_ytd <= 1.0:
            raise InvalidPerformanceError(
                f"max_drawdown_ytd must be 0.0-1.0, got {self.max_drawdown_ytd}"
            )

    @classmethod
    def compute(
        cls,
        snapshot_date: date,
        nav: float,
        benchmark_close: float,
        portfolio_beta: float,
        sharpe_ytd: float,
        max_drawdown_ytd: float,
        previous_nav: Optional[float] = None,
        previous_benchmark: Optional[float] = None,
    ) -> "PerformanceSnapshot":
        """Compute snapshot from raw data."""
        nav_change = (
            (nav - previous_nav) / previous_nav * 100
            if previous_nav and previous_nav > 0
            else 0.0
        )
        bench_change = (
            (benchmark_close - previous_benchmark) / previous_benchmark * 100
            if previous_benchmark and previous_benchmark > 0
            else 0.0
        )
        alpha = nav_change - bench_change

        return cls(
            snapshot_date=snapshot_date,
            nav=nav,
            nav_pct_change=round(nav_change, 4),
            benchmark_close=benchmark_close,
            benchmark_pct_change=round(bench_change, 4),
            alpha=round(alpha, 4),
            portfolio_beta=portfolio_beta,
            sharpe_ytd=sharpe_ytd,
            max_drawdown_ytd=max_drawdown_ytd,
        )
