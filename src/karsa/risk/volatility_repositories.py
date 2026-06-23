"""Sprint-58: Live Risk — Repository for asset_risk_metrics.

Upsert volatility estimates. Query latest vol for a symbol.
Uses SQLAlchemy ORM.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy.sql import func

from karsa.shared.persistence.base import Base
from karsa.risk.volatility_models import AssetRiskMetrics

logger = logging.getLogger(__name__)


class AssetRiskMetricsModel(Base):
    __tablename__ = "asset_risk_metrics"

    symbol = Column(String(20), primary_key=True)
    timeframe = Column(String(10), primary_key=True)
    realized_volatility = Column(Numeric(10, 6), nullable=False)
    beta_to_spy = Column(Numeric(10, 4), nullable=True)
    var_95 = Column(Numeric(18, 4), nullable=True)
    daily_vol_pct = Column(Numeric(10, 6), server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PostgresAssetRiskMetricsRepository:
    """CRUD for asset_risk_metrics table."""

    def __init__(self, session: Session):
        self.session = session

    def upsert_metrics(self, metrics: AssetRiskMetrics) -> None:
        """Insert or update risk metrics for a symbol/timeframe."""
        existing = self.session.query(AssetRiskMetricsModel).filter_by(
            symbol=metrics.symbol,
            timeframe=metrics.timeframe,
        ).first()

        if existing:
            existing.realized_volatility = metrics.realized_volatility
            existing.daily_vol_pct = metrics.daily_vol_pct
            existing.beta_to_spy = metrics.beta_to_spy
            existing.var_95 = metrics.var_95
            existing.updated_at = datetime.now(timezone.utc)
        else:
            model = AssetRiskMetricsModel(
                symbol=metrics.symbol,
                timeframe=metrics.timeframe,
                realized_volatility=metrics.realized_volatility,
                daily_vol_pct=metrics.daily_vol_pct,
                beta_to_spy=metrics.beta_to_spy,
                var_95=metrics.var_95,
            )
            self.session.add(model)

    def get_latest(self, symbol: str, timeframe: str = "1d") -> Optional[AssetRiskMetrics]:
        """Get the latest risk metrics for a symbol."""
        model = self.session.query(AssetRiskMetricsModel).filter_by(
            symbol=symbol,
            timeframe=timeframe,
        ).first()

        if not model:
            return None

        return AssetRiskMetrics(
            symbol=model.symbol,
            timeframe=model.timeframe,
            realized_volatility=float(model.realized_volatility),
            daily_vol_pct=float(model.daily_vol_pct or 0),
            beta_to_spy=float(model.beta_to_spy) if model.beta_to_spy else None,
            var_95=float(model.var_95) if model.var_95 else None,
            updated_at=model.updated_at,
        )

    def get_all(self, timeframe: str = "1d") -> list:
        """Get all risk metrics for a timeframe."""
        models = self.session.query(AssetRiskMetricsModel).filter_by(
            timeframe=timeframe,
        ).all()

        return [
            AssetRiskMetrics(
                symbol=m.symbol,
                timeframe=m.timeframe,
                realized_volatility=float(m.realized_volatility),
                daily_vol_pct=float(m.daily_vol_pct or 0),
                beta_to_spy=float(m.beta_to_spy) if m.beta_to_spy else None,
                var_95=float(m.var_95) if m.var_95 else None,
                updated_at=m.updated_at,
            )
            for m in models
        ]
