"""Sprint-59: CIO Dashboard repository.

TimescaleDB-optimized persistence for portfolio_snapshots and sector_exposures.
Falls back to standard PostgreSQL if TimescaleDB is unavailable.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Numeric, Integer, DateTime
from sqlalchemy.sql import func

from karsa.shared.persistence.base import Base
from karsa.cio.dashboard_models import PortfolioSnapshot, SectorExposure

logger = logging.getLogger(__name__)


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"

    snapshot_time = Column(DateTime(timezone=True), primary_key=True)
    total_equity = Column(Numeric(18, 4), nullable=False)
    cash_balance = Column(Numeric(18, 4), nullable=False)
    gross_exposure = Column(Numeric(18, 4), nullable=False)
    net_exposure = Column(Numeric(18, 4), nullable=False)
    daily_pnl = Column(Numeric(18, 4), nullable=False)
    max_drawdown_pct = Column(Numeric(10, 4), nullable=False)
    realized_pnl = Column(Numeric(18, 4), server_default="0")
    unrealized_pnl = Column(Numeric(18, 4), server_default="0")
    position_count = Column(Integer, server_default="0")


class SectorExposureModel(Base):
    __tablename__ = "sector_exposures"

    snapshot_time = Column(DateTime(timezone=True), primary_key=True)
    sector_name = Column(String(50), primary_key=True)
    gross_exposure = Column(Numeric(18, 4), nullable=False)
    net_exposure = Column(Numeric(18, 4), nullable=False)


class TimescalePortfolioRepository:
    """Read/write portfolio snapshots and sector exposures."""

    def __init__(self, session: Session):
        self.session = session

    def write_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Write a portfolio snapshot."""
        model = PortfolioSnapshotModel(
            snapshot_time=snapshot.snapshot_time,
            total_equity=snapshot.total_equity,
            cash_balance=snapshot.cash_balance,
            gross_exposure=snapshot.gross_exposure,
            net_exposure=snapshot.net_exposure,
            daily_pnl=snapshot.daily_pnl,
            max_drawdown_pct=snapshot.max_drawdown_pct,
            realized_pnl=snapshot.realized_pnl,
            unrealized_pnl=snapshot.unrealized_pnl,
            position_count=snapshot.position_count,
        )
        self.session.add(model)

    def write_sector_exposures(self, exposures: List[SectorExposure]) -> None:
        """Write sector exposure records."""
        for exp in exposures:
            model = SectorExposureModel(
                snapshot_time=exp.snapshot_time,
                sector_name=exp.sector_name,
                gross_exposure=exp.gross_exposure,
                net_exposure=exp.net_exposure,
            )
            self.session.add(model)

    def get_latest_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot."""
        m = self.session.query(PortfolioSnapshotModel).order_by(
            PortfolioSnapshotModel.snapshot_time.desc()
        ).first()

        if not m:
            return None

        return PortfolioSnapshot(
            snapshot_time=m.snapshot_time,
            total_equity=float(m.total_equity),
            cash_balance=float(m.cash_balance),
            gross_exposure=float(m.gross_exposure),
            net_exposure=float(m.net_exposure),
            daily_pnl=float(m.daily_pnl),
            max_drawdown_pct=float(m.max_drawdown_pct),
            realized_pnl=float(m.realized_pnl or 0),
            unrealized_pnl=float(m.unrealized_pnl or 0),
            position_count=int(m.position_count or 0),
        )

    def get_equity_curve(
        self,
        timeframe: str = "1D",
    ) -> List[PortfolioSnapshot]:
        """Get equity curve data for charting."""
        now = datetime.now(timezone.utc)
        delta_map = {
            "1D": timedelta(days=1),
            "1W": timedelta(weeks=1),
            "1M": timedelta(days=30),
            "YTD": datetime(now.year, 1, 1, tzinfo=timezone.utc) - now,
        }
        delta = delta_map.get(timeframe, timedelta(days=1))
        cutoff = now + delta  # delta is negative for YTD

        models = (
            self.session.query(PortfolioSnapshotModel)
            .filter(PortfolioSnapshotModel.snapshot_time >= cutoff)
            .order_by(PortfolioSnapshotModel.snapshot_time.asc())
            .all()
        )

        return [
            PortfolioSnapshot(
                snapshot_time=m.snapshot_time,
                total_equity=float(m.total_equity),
                cash_balance=float(m.cash_balance),
                gross_exposure=float(m.gross_exposure),
                net_exposure=float(m.net_exposure),
                daily_pnl=float(m.daily_pnl),
                max_drawdown_pct=float(m.max_drawdown_pct),
                realized_pnl=float(m.realized_pnl or 0),
                unrealized_pnl=float(m.unrealized_pnl or 0),
                position_count=int(m.position_count or 0),
            )
            for m in models
        ]

    def get_latest_sector_exposures(self) -> List[SectorExposure]:
        """Get the most recent sector exposures."""
        # Get latest snapshot time
        latest = self.session.query(
            func.max(SectorExposureModel.snapshot_time)
        ).scalar()

        if not latest:
            return []

        models = (
            self.session.query(SectorExposureModel)
            .filter(SectorExposureModel.snapshot_time == latest)
            .all()
        )

        return [
            SectorExposure(
                snapshot_time=m.snapshot_time,
                sector_name=m.sector_name,
                gross_exposure=float(m.gross_exposure),
                net_exposure=float(m.net_exposure),
            )
            for m in models
        ]
