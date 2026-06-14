import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from karsa.attribution.infrastructure.repositories import (
    InMemoryAttributionSessionRepository,
    InMemoryPerformanceAttributionRepository
)
from karsa.attribution.application.service import (
    AttributionCalculationService,
    AttributionRecomputationService,
    AttributionInvalidationService,
    AttributionReplayService
)

@pytest.fixture
def repos():
    return InMemoryAttributionSessionRepository(), InMemoryPerformanceAttributionRepository()

def test_calculation_service_workflow(repos):
    session_repo, record_repo = repos
    events = []
    service = AttributionCalculationService(session_repo, record_repo, events)
    
    # 1. Stage session
    session = service.stage_session(
        session_id="session-1",
        horizon_start=datetime(2026, 1, 1),
        horizon_end=datetime(2026, 1, 5),
        compounding_strategy="FRONGELLO"
    )
    assert session.state == "STAGED"
    
    # 2. Calculate returns
    inputs = {
        "decision_id": "urn:decision:1",
        "thesis_urn": "urn:thesis:1",
        "worker_urn": "urn:worker:1",
        "capability_urn": "urn:capability:1",
        "regime_urn": "urn:regime:1",
        "daily_returns": [
            {"portfolio_return": 0.01, "benchmark_return": 0.005},
            {"portfolio_return": 0.02, "benchmark_return": 0.01}
        ],
        "daily_effects": {
            "urn:asset:1": [
                {"selection": 0.005, "allocation": 0.002, "execution": 0.001, "beta": 0.002},
                {"selection": 0.01, "allocation": 0.004, "execution": 0.002, "beta": 0.004}
            ]
        }
    }
    
    records = service.calculate_attribution("session-1", inputs)
    assert len(records) == 1
    record = records[0]
    assert record.is_active is True
    assert record.attribution_version == 1
    
    # 3. Seal session
    event = service.seal_session("session-1")
    assert event.session_id == "session-1"
    assert len(events) == 1
    assert event.records[0]["record_id"] == record.record_id

def test_recomputation_service(repos):
    session_repo, record_repo = repos
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    recalc_service = AttributionRecomputationService(session_repo, record_repo, {}, events)
    
    session = calc_service.stage_session("session-2", datetime(2026, 1, 1), datetime(2026, 1, 5))
    
    inputs_v1 = {
        "decision_id": "urn:decision:2",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    
    calc_service.calculate_attribution("session-2", inputs_v1)
    calc_service.seal_session("session-2")
    
    # Now run recomputation with updated returns (V2)
    inputs_v2 = {
        "decision_id": "urn:decision:2",
        "daily_returns": [{"portfolio_return": 0.02, "benchmark_return": 0.005}],  # changed portfolio return
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.01, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    
    new_records = recalc_service.recompute_horizon("session-2", inputs_v2, "req-1")
    assert len(new_records) == 1
    assert new_records[0].attribution_version == 2
    assert new_records[0].is_active is True
    
    # Check old records are deactivated
    old_records = record_repo.find_by_session("session-2")
    for r in old_records:
        if r.attribution_version == 1:
            assert r.is_active is False
            
    # Verify events emitted
    superseded_events = [e for e in events if e.event_type == "AttributionSupersededEvent"]
    recomputed_events = [e for e in events if e.event_type == "AttributionRecomputedEvent"]
    assert len(superseded_events) == 1
    assert len(recomputed_events) == 1
    assert recomputed_events[0].session_id == "session-2"

def test_invalidation_service(repos):
    session_repo, record_repo = repos
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    inval_service = AttributionInvalidationService(session_repo, record_repo, events)
    
    calc_service.stage_session("session-3", datetime(2026, 1, 1), datetime(2026, 1, 5))
    inputs = {
        "decision_id": "urn:decision:3",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    calc_service.calculate_attribution("session-3", inputs)
    
    # Invalidate session
    inval_service.invalidate_session("session-3")
    
    records = record_repo.find_by_session("session-3")
    for r in records:
        assert r.is_active is False
        
    invalidated_events = [e for e in events if e.event_type == "AttributionInvalidatedEvent"]
    assert len(invalidated_events) == 1
    assert invalidated_events[0].session_id == "session-3"

def test_replay_service(repos):
    session_repo, record_repo = repos
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    replay_service = AttributionReplayService(session_repo, record_repo)
    
    calc_service.stage_session("session-4", datetime(2026, 1, 1), datetime(2026, 1, 5))
    inputs = {
        "decision_id": "urn:decision:4",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    calc_service.calculate_attribution("session-4", inputs)
    calc_service.seal_session("session-4")
    
    # Replay session with identical inputs
    result = replay_service.replay_session("session-4", inputs)
    assert result["session_id"] == "session-4"
    assert result["compounding_strategy"] == "FRONGELLO"
    
    # Replay session with mismatched inputs -> must raise error
    inputs_bad = {
        "decision_id": "urn:decision:4",
        "daily_returns": [{"portfolio_return": 0.02, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    with pytest.raises(ValueError):
        replay_service.replay_session("session-4", inputs_bad)
