from unittest.mock import MagicMock
import pytest
from karsa.performance.infrastructure.storage.profile_repository import PostgresProfileRepository
from karsa.performance.domain.model.profile import PerformanceProfileWindow
from karsa.performance.domain.model.value_objects import TargetIdentity, WindowIdentity, PredictionMetrics, InvestmentMetrics
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
import json

def test_postgres_profile_occ_failure():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.rowcount = 0
    
    repo = PostgresProfileRepository(conn)
    profile = PerformanceProfileWindow(
        TargetIdentity("t1", "ORIGINATOR"),
        WindowIdentity("MONTH", "2026-06"),
        PredictionMetrics(0,0,0), InvestmentMetrics(0,0), version=2
    )
    
    with pytest.raises(ConcurrencyConflictError):
        repo.save(profile)

def test_profile_persistence_roundtrip():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    
    # Mocking get
    metrics = {
        "prediction_metrics": {"hit_rate": 0.5, "brier_score": 0.1, "evaluation_count": 2},
        "investment_metrics": {"average_roi": 0.0, "capital_efficiency_score": 0.0}
    }
    cur.fetchone.return_value = (1, json.dumps(metrics))
    
    repo = PostgresProfileRepository(conn)
    profile = repo.get_by_identity(TargetIdentity("t1", "ORIGINATOR"), WindowIdentity("MONTH", "2026-06"))
    
    assert profile is not None
    assert profile.aggregate_version == 1
    assert profile.prediction_metrics.evaluation_count == 2
