"""Sprint-59: CIO Dashboard domain models.

PortfolioSnapshot, SectorExposure, PortfolioState, ExposureBreakdown,
PnLSnapshot, StaleDataState. Extends the existing cio/ bounded context.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional


class StaleDataState(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    HALTED = "HALTED"


@dataclass
class Position:
    """A single position in the portfolio."""
    symbol: str = ""
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    sector: str = "Unknown"

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.current_price - self.avg_entry_price)

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_entry_price <= 0:
            return 0.0
        return (self.current_price - self.avg_entry_price) / self.avg_entry_price


@dataclass
class PnLSnapshot:
    """Point-in-time PnL breakdown."""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExposureBreakdown:
    """Portfolio exposure breakdown."""
    gross_exposure: float = 0.0  # Sum of abs(position values)
    net_exposure: float = 0.0    # Sum of position values (long - short)
    by_sector: Dict[str, float] = field(default_factory=dict)
    long_exposure: float = 0.0
    short_exposure: float = 0.0


@dataclass
class PortfolioState:
    """In-memory portfolio state cache.

    Maintained by CIOProducer. Updated on fills and mark-to-market.
    """
    cash_balance: float = 1_000_000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    daily_pnl: float = 0.0
    peak_equity: float = 1_000_000.0
    last_fill_timestamp: Optional[datetime] = None
    last_bar_timestamp: Optional[datetime] = None
    last_thesis_timestamp: Optional[datetime] = None

    @property
    def total_equity(self) -> float:
        """Cash + sum of position market values."""
        position_value = sum(p.market_value for p in self.positions.values())
        return self.cash_balance + position_value

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def max_drawdown_pct(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        drawdown = (self.peak_equity - self.total_equity) / self.peak_equity
        return max(0.0, drawdown)

    def get_exposure(self) -> ExposureBreakdown:
        """Calculate current exposure breakdown."""
        gross = 0.0
        net = 0.0
        long_exp = 0.0
        short_exp = 0.0
        by_sector: Dict[str, float] = {}

        for pos in self.positions.values():
            mv = pos.market_value
            gross += abs(mv)
            net += mv
            if mv >= 0:
                long_exp += mv
            else:
                short_exp += abs(mv)
            by_sector[pos.sector] = by_sector.get(pos.sector, 0.0) + mv

        return ExposureBreakdown(
            gross_exposure=gross,
            net_exposure=net,
            by_sector=by_sector,
            long_exposure=long_exp,
            short_exposure=short_exp,
        )


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Time-series portfolio snapshot for persistence."""
    snapshot_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_equity: float = 0.0
    cash_balance: float = 0.0
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown_pct: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    position_count: int = 0


@dataclass(frozen=True)
class SectorExposure:
    """Time-series sector exposure for persistence."""
    snapshot_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sector_name: str = ""
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
