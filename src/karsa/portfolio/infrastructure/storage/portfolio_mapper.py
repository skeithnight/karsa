from datetime import datetime
from karsa.portfolio.domain.model.portfolio import (
    Portfolio, Position, ExposureMetrics, PortfolioState, 
    PortfolioTargetSnapshot, TargetPosition, PortfolioDecision
)
from karsa.portfolio.infrastructure.storage.portfolio_records import (
    PortfolioRecord, PositionRecord, ExposureMetricsRecord, 
    PortfolioTargetSnapshotRecord, TargetPositionRecord, PortfolioDecisionRecord
)

class PortfolioMapper:
    @staticmethod
    def to_record(portfolio: Portfolio) -> PortfolioRecord:
        positions_rec = [
            PositionRecord(
                position_id=p.position_id,
                symbol=p.symbol,
                quantity=p.quantity,
                average_cost=p.average_cost,
                market_value=p.market_value
            ) for p in portfolio.positions
        ]
        
        exposure_rec = ExposureMetricsRecord(
            gross_exposure=portfolio.exposure_metrics.gross_exposure,
            net_exposure=portfolio.exposure_metrics.net_exposure,
            concentration_exposure=portfolio.exposure_metrics.concentration_exposure,
            cash_ratio=portfolio.exposure_metrics.cash_ratio,
            leverage_ratio=portfolio.exposure_metrics.leverage_ratio
        )
        
        return PortfolioRecord(
            portfolio_id=portfolio.portfolio_id,
            state=portfolio.state.value,
            current_target_snapshot_id=portfolio.current_target_snapshot_id or "",
            positions=positions_rec,
            exposure_metrics=exposure_rec
        )

    @staticmethod
    def to_domain(record: PortfolioRecord) -> Portfolio:
        portfolio = Portfolio(record.portfolio_id)
        portfolio.state = PortfolioState(record.state)
        portfolio.current_target_snapshot_id = record.current_target_snapshot_id if record.current_target_snapshot_id else None
        
        portfolio.positions = [
            Position(
                position_id=p.position_id,
                portfolio_id=record.portfolio_id,
                symbol=p.symbol,
                quantity=p.quantity,
                average_cost=p.average_cost,
                market_value=p.market_value
            ) for p in record.positions
        ]
        
        portfolio.exposure_metrics = ExposureMetrics(
            gross_exposure=record.exposure_metrics.gross_exposure,
            net_exposure=record.exposure_metrics.net_exposure,
            concentration_exposure=record.exposure_metrics.concentration_exposure,
            cash_ratio=record.exposure_metrics.cash_ratio,
            leverage_ratio=record.exposure_metrics.leverage_ratio
        )
        
        return portfolio

class PortfolioTargetSnapshotMapper:
    @staticmethod
    def to_record(snapshot: PortfolioTargetSnapshot) -> PortfolioTargetSnapshotRecord:
        targets = [
            TargetPositionRecord(
                symbol=t.symbol,
                target_weight=t.target_weight
            ) for t in snapshot.target_positions
        ]
        
        return PortfolioTargetSnapshotRecord(
            snapshot_id=snapshot.snapshot_id,
            portfolio_id=snapshot.portfolio_id,
            version=snapshot.version,
            target_positions=targets,
            created_at=snapshot.created_at.isoformat()
        )

    @staticmethod
    def to_domain(record: PortfolioTargetSnapshotRecord) -> PortfolioTargetSnapshot:
        targets = frozenset([
            TargetPosition(
                symbol=t.symbol,
                target_weight=t.target_weight
            ) for t in record.target_positions
        ])
        
        return PortfolioTargetSnapshot(
            snapshot_id=record.snapshot_id,
            portfolio_id=record.portfolio_id,
            version=record.version,
            target_positions=targets,
            created_at=datetime.fromisoformat(record.created_at)
        )
