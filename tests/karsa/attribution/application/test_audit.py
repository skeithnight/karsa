import pytest
from datetime import datetime
from decimal import Decimal
from karsa.attribution.infrastructure.repositories import (
    InMemoryAttributionSessionRepository,
    InMemoryPerformanceAttributionRepository
)
from karsa.attribution.application.service import (
    AttributionCalculationService,
    AttributionRecomputationService
)
from karsa.attribution.domain.model.models import PerformanceAttributionRecord

def test_failure_recovery():
    session_repo = InMemoryAttributionSessionRepository()
    record_repo = InMemoryPerformanceAttributionRepository()
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    calc_service.stage_session("session-fail", datetime(2026, 1, 1), datetime(2026, 1, 5))
    
    # 1. Attempt calculation with bad strategy to trigger failure
    bad_inputs = {
        "decision_id": "urn:decision:fail",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005}]
        }
    }
    
    # Temporarily set compounding strategy to something invalid
    session = session_repo.get_by_id("session-fail")
    session.compounding_strategy = "INVALID_STRATEGY"
    session.aggregate_version += 1
    session_repo.save(session)
    
    with pytest.raises(ValueError, match="Unknown strategy"):
        calc_service.calculate_attribution("session-fail", bad_inputs)
        
    # Verify no records were saved for the session
    records = record_repo.find_by_session("session-fail")
    assert len(records) == 0
    
    # 2. Recover: Reset strategy and run calculation with valid inputs
    session = session_repo.get_by_id("session-fail")
    session.compounding_strategy = "FRONGELLO"
    session.state = "STAGED"  # Reset state
    session.aggregate_version += 1
    session_repo.save(session)
    
    good_inputs = {
        "decision_id": "urn:decision:fail",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    
    records = calc_service.calculate_attribution("session-fail", good_inputs)
    assert len(records) == 1
    assert records[0].is_active is True
    
    # Verify session is now calibrated
    session = session_repo.get_by_id("session-fail")
    assert session.state == "CALIBRATED"


def test_queue_replay():
    session_repo = InMemoryAttributionSessionRepository()
    record_repo = InMemoryPerformanceAttributionRepository()
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    recalc_service = AttributionRecomputationService(session_repo, record_repo, {}, events)
    
    # Simulate a recomputation request queue
    queue = [
        {"session_id": "session-q", "inputs": {
            "decision_id": "urn:decision:q",
            "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
            "daily_effects": {
                "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
            }
        }, "request_id": "req-init"},
        {"session_id": "session-q", "inputs": {
            "decision_id": "urn:decision:q",
            "daily_returns": [{"portfolio_return": 0.02, "benchmark_return": 0.005}],
            "daily_effects": {
                "urn:asset:1": [{"selection": 0.010, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
            }
        }, "request_id": "req-v2"},
        {"session_id": "session-q", "inputs": {
            "decision_id": "urn:decision:q",
            "daily_returns": [{"portfolio_return": 0.03, "benchmark_return": 0.005}],
            "daily_effects": {
                "urn:asset:1": [{"selection": 0.015, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
            }
        }, "request_id": "req-v3"}
    ]
    
    # Replay/process the queue
    for item in queue:
        session_id = item["session_id"]
        inputs = item["inputs"]
        req_id = item["request_id"]
        
        session = session_repo.get_by_id(session_id)
        if not session:
            calc_service.stage_session(session_id, datetime(2026, 1, 1), datetime(2026, 1, 5))
            calc_service.calculate_attribution(session_id, inputs)
            calc_service.seal_session(session_id)
        else:
            recalc_service.recompute_horizon(session_id, inputs, req_id)
            
    # Assert final version is 3 and only version 3 is active
    all_records = record_repo.find_by_session("session-q")
    assert len(all_records) == 3
    
    active_records = [r for r in all_records if r.is_active]
    assert len(active_records) == 1
    assert active_records[0].attribution_version == 3
    assert active_records[0].selection_return == Decimal("0.015")


def test_multi_version_reconstruction():
    # Construct a historical record set manually
    records = [
        PerformanceAttributionRecord(
            record_id="rec-1",
            session_id="session-1",
            decision_id="urn:decision:1",
            thesis_urn="urn:thesis:1",
            worker_urn="urn:worker:1",
            capability_urn="urn:capability:1",
            regime_urn="urn:regime:1",
            asset_urn="urn:asset:1",
            selection_return=Decimal("0.01"),
            allocation_return=Decimal("0.005"),
            execution_return=Decimal("0.0"),
            beta_return=Decimal("0.0"),
            attribution_version=1,
            is_active=False
        ),
        PerformanceAttributionRecord(
            record_id="rec-2",
            session_id="session-1",
            decision_id="urn:decision:1",
            thesis_urn="urn:thesis:1",
            worker_urn="urn:worker:1",
            capability_urn="urn:capability:1",
            regime_urn="urn:regime:1",
            asset_urn="urn:asset:1",
            selection_return=Decimal("0.02"),
            allocation_return=Decimal("0.005"),
            execution_return=Decimal("0.0"),
            beta_return=Decimal("0.0"),
            attribution_version=2,
            is_active=False
        ),
        PerformanceAttributionRecord(
            record_id="rec-3",
            session_id="session-1",
            decision_id="urn:decision:1",
            thesis_urn="urn:thesis:1",
            worker_urn="urn:worker:1",
            capability_urn="urn:capability:1",
            regime_urn="urn:regime:1",
            asset_urn="urn:asset:1",
            selection_return=Decimal("0.03"),
            allocation_return=Decimal("0.005"),
            execution_return=Decimal("0.0"),
            beta_return=Decimal("0.0"),
            attribution_version=3,
            is_active=True
        ),
    ]
    
    # Reconstruct version 1 state
    # We filter by version <= 1, and for each asset keep the highest version <= 1
    v1_state = {}
    for r in records:
        if r.attribution_version <= 1:
            existing = v1_state.get(r.asset_urn)
            if not existing or r.attribution_version > existing.attribution_version:
                v1_state[r.asset_urn] = r
                
    assert len(v1_state) == 1
    assert v1_state["urn:asset:1"].selection_return == Decimal("0.01")
    
    # Reconstruct version 2 state
    v2_state = {}
    for r in records:
        if r.attribution_version <= 2:
            existing = v2_state.get(r.asset_urn)
            if not existing or r.attribution_version > existing.attribution_version:
                v2_state[r.asset_urn] = r
                
    assert len(v2_state) == 1
    assert v2_state["urn:asset:1"].selection_return == Decimal("0.02")
