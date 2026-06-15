import pytest
from datetime import datetime
from karsa.portfolio.domain.model.portfolio import (
    Portfolio, Position, ExposureMetrics, PortfolioState,
    PortfolioTargetSnapshot, TargetPosition
)
from karsa.portfolio.infrastructure.storage.portfolio_mapper import PortfolioMapper, PortfolioTargetSnapshotMapper

def test_portfolio_mapper_roundtrip():
    p = Portfolio("P-1")
    p.activate()
    p.current_target_snapshot_id = "SNAP-1"
    p.add_position(Position("POS-1", "P-1", "AAPL", 100, 150.0, 16000.0))
    p.update_exposure_metrics(ExposureMetrics(1.5, 0.8, 0.2, 0.1, 1.5))
    
    record = PortfolioMapper.to_record(p)
    assert record.portfolio_id == "P-1"
    assert record.state == "ACTIVE"
    assert record.current_target_snapshot_id == "SNAP-1"
    assert len(record.positions) == 1
    assert record.exposure_metrics.gross_exposure == 1.5
    
    restored = PortfolioMapper.to_domain(record)
    assert restored.portfolio_id == "P-1"
    assert restored.state == PortfolioState.ACTIVE
    assert restored.current_target_snapshot_id == "SNAP-1"
    assert len(restored.positions) == 1
    assert restored.positions[0].symbol == "AAPL"
    assert restored.exposure_metrics.gross_exposure == 1.5

def test_snapshot_mapper_roundtrip():
    targets = frozenset([TargetPosition("AAPL", 0.8), TargetPosition("MSFT", 0.2)])
    s = PortfolioTargetSnapshot("SNAP-1", "P-1", 1, targets)
    
    record = PortfolioTargetSnapshotMapper.to_record(s)
    assert record.snapshot_id == "SNAP-1"
    assert record.portfolio_id == "P-1"
    assert record.version == 1
    assert len(record.target_positions) == 2
    
    restored = PortfolioTargetSnapshotMapper.to_domain(record)
    assert restored.snapshot_id == "SNAP-1"
    assert restored.portfolio_id == "P-1"
    assert restored.version == 1
    assert len(restored.target_positions) == 2
    assert type(restored.target_positions) is frozenset
