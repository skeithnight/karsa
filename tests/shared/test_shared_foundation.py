import pytest
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.shared.domain.identity import DecisionIdentity, OriginatorIdentity
from karsa.shared.domain.snapshot import DecisionContextSnapshot
from karsa.shared.events.envelope import PlatformEventEnvelope
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.shared.contracts.execution import ExecutionOutcomeContract

def test_versioned_aggregate_increments():
    agg = VersionedAggregate()
    assert agg.aggregate_version == 0
    agg.increment_version()
    assert agg.aggregate_version == 1

def test_platform_event_envelope_serialization():
    env = PlatformEventEnvelope(
        event_id="evt-1",
        event_type="TestEvent",
        correlation_id="corr-1",
        causation_id="cause-1",
        aggregate_type="Portfolio",
        aggregate_id="port-1",
        aggregate_version=1,
        occurred_at="2026-06-13T00:00:00Z",
        schema_version="1.0",
        payload={"foo": "bar"}
    )
    serialized = env.serialize()
    deserialized = PlatformEventEnvelope.deserialize(serialized)
    assert deserialized.event_id == "evt-1"
    assert deserialized.payload["foo"] == "bar"

def test_decision_context_snapshot_fingerprint():
    snap = DecisionContextSnapshot(
        decision_context_id="ctx-1",
        trigger_event_id="trig-1",
        trigger_event_type="RebalanceRequested",
        constraint_fingerprint="abc",
        optimizer_version="v1",
        engine_version="v2",
        git_hash="123456",
        created_at="2026-06-13T00:00:00Z",
        dependency_snapshot_ids={"regime": "r-1"}
    )
    fp = snap.generate_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 64  # sha256

def test_originator_identity():
    ident = OriginatorIdentity(
        originator_id="AI-1",
        originator_type="LLM",
        originator_version="v4"
    )
    assert ident.originator_id == "AI-1"

def test_execution_outcome_contract():
    contract = ExecutionOutcomeContract(
        decision_id="dec-1",
        intent_id="int-1",
        execution_status="FILLED",
        requested_quantity=10.0,
        filled_quantity=10.0,
        requested_price=100.0,
        average_fill_price=100.5,
        fees=0.1,
        slippage=0.5,
        executed_at="2026-06-13T00:00:00Z",
        broker_reference="brk-1"
    )
    assert contract.execution_status == "FILLED"
