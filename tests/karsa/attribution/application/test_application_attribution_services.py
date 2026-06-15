import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord
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


import os
import shutil
from karsa.attribution.infrastructure.repositories import (
    FileAttributionSessionRepository,
    FilePerformanceAttributionRepository
)

def test_service_error_paths(repos):
    session_repo, record_repo = repos
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    recalc_service = AttributionRecomputationService(session_repo, record_repo, {}, events)
    inval_service = AttributionInvalidationService(session_repo, record_repo, events)
    replay_service = AttributionReplayService(session_repo, record_repo)
    
    # 1. Non-existent session exceptions
    with pytest.raises(ValueError, match="Session not found"):
        calc_service.calculate_attribution("non-existent", {})
    with pytest.raises(ValueError, match="Session not found"):
        calc_service.seal_session("non-existent")
    with pytest.raises(ValueError, match="Session not found"):
        recalc_service.recompute_horizon("non-existent", {}, "req-x")
    with pytest.raises(ValueError, match="Session not found"):
        inval_service.invalidate_session("non-existent")
    with pytest.raises(ValueError, match="Session not found"):
        replay_service.replay_session("non-existent", {})
        
    # 2. Manifest hash identical short-circuit
    calc_service.stage_session("session-sc", datetime(2026, 1, 1), datetime(2026, 1, 5))
    inputs = {
        "decision_id": "urn:decision:sc",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    calc_service.calculate_attribution("session-sc", inputs)
    # Recomputes with SAME inputs -> should short-circuit and return existing records
    recalculated = recalc_service.recompute_horizon("session-sc", inputs, "req-sc")
    assert len(recalculated) == 1
    assert recalculated[0].attribution_version == 1
    
    # 3. Recomputation depth ceiling check
    # Manually insert 99 versions to trigger ceiling validation
    for ver in range(2, 100):
        rec = PerformanceAttributionRecord(
            record_id="rec-ceil", session_id="session-sc", decision_id="urn:decision:sc",
            thesis_urn="t", worker_urn="w", capability_urn="c", regime_urn="r", asset_urn="urn:asset:1",
            selection_return=Decimal("0.0"), allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"),
            beta_return=Decimal("0.0"), attribution_version=ver, is_active=(ver == 99)
        )
        record_repo.save(rec)
        
    inputs_new = {
        "decision_id": "urn:decision:sc",
        "daily_returns": [{"portfolio_return": 0.02, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.01, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    with pytest.raises(ValueError, match="Recomputation depth ceiling of 99 exceeded"):
        recalc_service.recompute_horizon("session-sc", inputs_new, "req-ceil-fail")


def test_file_repos_cleanup_and_list():
    sess_dir = ".karsa/test_file_repos_list/sessions/"
    rec_dir = ".karsa/test_file_repos_list/records/"
    
    if os.path.exists(".karsa/test_file_repos_list/"):
        shutil.rmtree(".karsa/test_file_repos_list/")
        
    sess_repo = FileAttributionSessionRepository(storage_dir=sess_dir)
    rec_repo = FilePerformanceAttributionRepository(storage_dir=rec_dir)
    
    # Check lists and clears on empty repos
    assert len(sess_repo.list_all()) == 0
    assert len(rec_repo.list_all()) == 0
    
    # Save session and record
    s1 = AttributionSession("session-f1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    sess_repo.save(s1)
    
    r1 = PerformanceAttributionRecord(
        record_id="rec-f1", session_id="session-f1", decision_id="urn:decision:f1",
        thesis_urn="t", worker_urn="w", capability_urn="c", regime_urn="r", asset_urn="urn:asset:1",
        selection_return=Decimal("0.0"), allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"),
        beta_return=Decimal("0.0"), attribution_version=1
    )
    rec_repo.save(r1)
    
    assert len(sess_repo.list_all()) == 1
    assert len(rec_repo.list_all()) == 1
    
    # Clear repositories
    sess_repo.clear()
    rec_repo.clear()
    
    assert len(sess_repo.list_all()) == 0
    assert len(rec_repo.list_all()) == 0
    
    if os.path.exists(".karsa/test_file_repos_list/"):
        shutil.rmtree(".karsa/test_file_repos_list/")

def test_service_strategy_resolution(repos):
    session_repo, record_repo = repos
    events = []
    
    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    recalc_service = AttributionRecomputationService(session_repo, record_repo, {}, events)
    replay_service = AttributionReplayService(session_repo, record_repo)
    
    # Check invalid strategy raising ValueError
    with pytest.raises(ValueError, match="Unknown strategy"):
        calc_service._get_strategy("INVALID")
        
    with pytest.raises(ValueError, match="Unknown strategy"):
        recalc_service._get_strategy("INVALID")
        
    # Check resolved strategies
    assert calc_service._get_strategy("CARINO").__class__.__name__ == "CarinoCompounding"
    assert calc_service._get_strategy("MENCHERO").__class__.__name__ == "MencheroCompounding"
    assert recalc_service._get_strategy("CARINO").__class__.__name__ == "CarinoCompounding"
    assert recalc_service._get_strategy("MENCHERO").__class__.__name__ == "MencheroCompounding"

def test_recomputation_idempotency_cache(repos):
    session_repo, record_repo = repos
    recalc_service = AttributionRecomputationService(session_repo, record_repo, {"req-cached": True}, [])
    
    # Should return empty list immediately on idempotency hit
    res = recalc_service.recompute_horizon("session-1", {}, "req-cached")
    assert res == []

def test_replay_service_mismatch_branches(repos):
    session_repo, record_repo = repos
    calc_service = AttributionCalculationService(session_repo, record_repo, [])
    replay_service = AttributionReplayService(session_repo, record_repo)
    
    # 1. Setup session and record
    calc_service.stage_session("session-rep", datetime(2026, 1, 1), datetime(2026, 1, 5), compounding_strategy="FRONGELLO")
    inputs = {
        "decision_id": "urn:decision:rep",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.0, "beta": 0.0}]
        }
    }
    calc_service.calculate_attribution("session-rep", inputs)
    
    # 2. Replay with input manifest hash mismatch
    with pytest.raises(ValueError, match="Input data mismatch"):
        replay_service.replay_session("session-rep", {"daily_returns": []})
        
    # 3. Replay with unknown strategy on session
    session = session_repo.get_by_id("session-rep")
    session.compounding_strategy = "INVALID"
    session.increment_version()
    session_repo.save(session)
    with pytest.raises(ValueError, match="Unknown strategy"):
        replay_service.replay_session("session-rep", inputs)
        
    # Restore strategy and test Carino & Menchero resolving in replay
    session = session_repo.get_by_id("session-rep")
    session.compounding_strategy = "CARINO"
    session.increment_version()
    session_repo.save(session)
    res_carino = replay_service.replay_session("session-rep", inputs)
    assert res_carino["compounding_strategy"] == "CARINO"
    
    session = session_repo.get_by_id("session-rep")
    session.compounding_strategy = "MENCHERO"
    session.increment_version()
    session_repo.save(session)
    res_menchero = replay_service.replay_session("session-rep", inputs)
    assert res_menchero["compounding_strategy"] == "MENCHERO"
    
    # Restore to FRONGELLO to test record discrepancies
    session = session_repo.get_by_id("session-rep")
    session.compounding_strategy = "FRONGELLO"
    session.increment_version()
    session_repo.save(session)
    
    # 4. Replay with missing asset result in replayed output
    # Directly modify internal repo state to change asset_urn on stored record
    records = record_repo.find_by_session("session-rep")
    rec = records[0]
    key = f"{rec.record_id}:{rec.attribution_version}"
    # Directly mutate the internal record (bypassing immutability for test setup)
    internal_rec = record_repo._records[key]
    object.__setattr__(internal_rec, 'asset_urn', "urn:asset:missing")
    with pytest.raises(ValueError, match="Missing replayed results for asset"):
        replay_service.replay_session("session-rep", inputs)
        
    # 5. Restore asset_urn but change selection_return to trigger mismatch
    object.__setattr__(internal_rec, 'asset_urn', "urn:asset:1")
    object.__setattr__(internal_rec, 'selection_return', Decimal("9.99"))
    with pytest.raises(ValueError, match="Replay output mismatch on selection effect"):
        replay_service.replay_session("session-rep", inputs)
        
    # 6. Restore selection but change allocation to trigger mismatch on allocation
    object.__setattr__(internal_rec, 'selection_return', Decimal("0.005"))
    object.__setattr__(internal_rec, 'allocation_return', Decimal("9.99"))
    with pytest.raises(ValueError, match="Replay output mismatch on allocation effect"):
        replay_service.replay_session("session-rep", inputs)


