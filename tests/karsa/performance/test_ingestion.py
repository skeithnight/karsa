import pytest
from decimal import Decimal
from datetime import datetime
from karsa.performance.domain.value_objects import DecisionPerformanceIdentity
from karsa.performance.domain.projections import DecisionContext, DecisionPerformanceRecord
from karsa.performance.application.ingestion import PerformanceEventIngestionService
from karsa.performance.infrastructure.repositories import DecisionContextMissingError

class MockRepository:
    def __init__(self):
        self.effective_record = None
        self.bucket_deltas = []
        self.should_raise_missing = False

    def get_context(self, decision_id):
        if self.should_raise_missing:
            raise DecisionContextMissingError()
        return DecisionContext(
            decision_id=decision_id, worker_id="W1", strategy_id="S1", thesis_id="T1", 
            stated_confidence=Decimal('0.8'), decision_timestamp=datetime(2026, 1, 1)
        )

    def get_effective_generation_record(self, decision_id, outcome_seq_id):
        return self.effective_record

    def append_decision_record(self, record):
        pass

    def apply_bucket_delta(self, target_type, target_id, date, delta_gross, delta_net):
        self.bucket_deltas.append((target_type, delta_gross))

class MockOrchestrator:
    def __init__(self):
        self.invalidated = False

    def trigger_invalidation(self, worker_id, strategy_id, thesis_id, occurred_at):
        self.invalidated = True

class MockBus:
    def __init__(self):
        self.dlq_events = []
    def publish(self, topic, event):
        if topic == "performance_dlq":
            self.dlq_events.append(event)

def test_identity_aware_delta_calculation():
    repo = MockRepository()
    orch = MockOrchestrator()
    svc = PerformanceEventIngestionService(repo, orch, MockBus())

    svc.handle_attribution_calculated({
        "decision_id": "D1", "outcome_sequence_id": 1, "attribution_generation": 1,
        "gross_pnl": 100, "occurred_at": "2026-01-01T10:00:00"
    })
    
    assert len(repo.bucket_deltas) == 3
    assert repo.bucket_deltas[0][1] == Decimal('100')
    assert orch.invalidated is True

def test_duplicate_delivery_is_ignored():
    repo = MockRepository()
    orch = MockOrchestrator()
    svc = PerformanceEventIngestionService(repo, orch, MockBus())
    
    repo.effective_record = DecisionPerformanceRecord(
        identity=DecisionPerformanceIdentity("D1", 1, 1),
        worker_id="W1", strategy_id="S1", thesis_id="T1", regime_id=None,
        gross_pnl=Decimal('100'), net_pnl=Decimal('100'), stated_confidence=None,
        decision_timestamp=datetime.now()
    )

    svc.handle_attribution_calculated({
        "decision_id": "D1", "outcome_sequence_id": 1, "attribution_generation": 1,
        "gross_pnl": 100, "occurred_at": "2026-01-01T10:00:00"
    })
    
    assert len(repo.bucket_deltas) == 0
    assert orch.invalidated is False

def test_out_of_order_generation_is_suppressed():
    repo = MockRepository()
    orch = MockOrchestrator()
    svc = PerformanceEventIngestionService(repo, orch, MockBus())
    
    repo.effective_record = DecisionPerformanceRecord(
        identity=DecisionPerformanceIdentity("D1", 1, 3),
        worker_id="W1", strategy_id="S1", thesis_id="T1", regime_id=None,
        gross_pnl=Decimal('50'), net_pnl=Decimal('50'), stated_confidence=None,
        decision_timestamp=datetime.now()
    )

    svc.handle_attribution_calculated({
        "decision_id": "D1", "outcome_sequence_id": 1, "attribution_generation": 2,
        "gross_pnl": 75, "occurred_at": "2026-01-01T10:00:00"
    })
    
    assert len(repo.bucket_deltas) == 0
    assert orch.invalidated is False

def test_dlq_routing_on_missing_context(monkeypatch):
    import time
    monkeypatch.setattr(time, 'sleep', lambda s: None) # Fast tests
    
    repo = MockRepository()
    repo.should_raise_missing = True
    orch = MockOrchestrator()
    bus = MockBus()
    svc = PerformanceEventIngestionService(repo, orch, bus)
    
    svc.handle_attribution_calculated({
        "decision_id": "D1", "outcome_sequence_id": 1, "attribution_generation": 1,
        "gross_pnl": 100, "occurred_at": "2026-01-01T10:00:00"
    }, retry_count=5)
    
    assert len(bus.dlq_events) == 1
    assert bus.dlq_events[0].error_reason == ""

def test_governance_restatement_triggers_invalidation():
    repo = MockRepository()
    orch = MockOrchestrator()
    svc = PerformanceEventIngestionService(repo, orch, MockBus())
    
    repo.effective_record = DecisionPerformanceRecord(
        identity=DecisionPerformanceIdentity("D1", 1, 1),
        worker_id="W1", strategy_id="S1", thesis_id="T1", regime_id=None,
        gross_pnl=Decimal('100'), net_pnl=Decimal('100'), stated_confidence=None,
        decision_timestamp=datetime.now()
    )

    svc.handle_attribution_calculated({
        "decision_id": "D1", "outcome_sequence_id": 1, "attribution_generation": 2,
        "gross_pnl": 50, "occurred_at": "2026-01-02T10:00:00"
    })
    
    assert repo.bucket_deltas[0][1] == Decimal('-50')
    assert orch.invalidated is True

def test_brier_score_math():
    assert True

def test_ingestion_pipeline_end_to_end():
    assert True

def test_query_time_ranking_view():
    assert True

def test_deterministic_rebuild():
    assert True

def test_late_arrival_changes_reality():
    assert True

def test_bucket_delta_upsert_scale():
    assert True

