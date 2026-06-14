import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord
from karsa.attribution.domain.model.value_objects import (
    FrongelloCompounding,
    CarinoCompounding,
    MencheroCompounding,
    CanonicalManifestSerializer,
    BenchmarkSnapshot
)

def test_attribution_session_state_transitions():
    session = AttributionSession(
        session_id="session-1",
        horizon_start=datetime(2026, 1, 1),
        horizon_end=datetime(2026, 1, 10),
        state="STAGED",
        compounding_strategy="FRONGELLO"
    )
    
    # staged -> computing
    session.transition_to("COMPUTING")
    assert session.state == "COMPUTING"
    assert session.aggregate_version == 2
    
    # computing -> calibrated
    session.transition_to("CALIBRATED")
    assert session.state == "CALIBRATED"
    
    # calibrated -> sealed
    session.transition_to("SEALED")
    assert session.state == "SEALED"
    
    # sealed is final state
    with pytest.raises(ValueError):
        session.transition_to("STAGED")

def test_attribution_session_invalid_transitions():
    session = AttributionSession(
        session_id="session-2",
        horizon_start=datetime(2026, 1, 1),
        horizon_end=datetime(2026, 1, 10),
        state="STAGED"
    )
    # cannot go staged -> sealed
    with pytest.raises(ValueError):
        session.transition_to("SEALED")

def test_performance_record_immutability():
    rec = PerformanceAttributionRecord(
        record_id="rec-1",
        session_id="session-1",
        decision_id="urn:decision:1",
        thesis_urn="urn:thesis:1",
        worker_urn="urn:worker:1",
        capability_urn="urn:capability:1",
        regime_urn="urn:regime:1",
        asset_urn="urn:asset:1",
        selection_return=Decimal("0.05"),
        allocation_return=Decimal("0.02"),
        execution_return=Decimal("0.01"),
        beta_return=Decimal("0.03"),
        attribution_version=1,
        is_active=True
    )
    
    # We can set is_active from True to False (superseding)
    rec.is_active = False
    assert rec.is_active is False
    assert rec.aggregate_version == 2
    
    # Cannot toggle it back to True
    with pytest.raises(TypeError):
        rec.is_active = True
        
    # Cannot modify other fields
    with pytest.raises(TypeError):
        rec.selection_return = Decimal("0.10")

def test_frongello_compounding_math():
    strategy = FrongelloCompounding()
    
    daily_returns = [
        {"portfolio_return": 0.02, "benchmark_return": 0.01},
        {"portfolio_return": -0.01, "benchmark_return": 0.03}
    ]
    
    effects = [
        {"selection": Decimal("0.01"), "allocation": Decimal("0.005"), "execution": Decimal("0.0"), "beta": Decimal("0.005")},
        {"selection": Decimal("-0.02"), "allocation": Decimal("-0.01"), "execution": Decimal("-0.005"), "beta": Decimal("-0.005")}
    ]
    
    res = strategy.compound_returns(daily_returns, effects)
    
    # T=1: cum_p = 1.0, cum_b = 1.0 + 0.03 = 1.03. beta_1 = 1.03
    # T=2: cum_p = 1.02, cum_b = 1.0. beta_2 = 1.02
    # selection_1_compounded = 0.01 * 1.03 = 0.0103
    # selection_2_compounded = -0.02 * 1.02 = -0.0204
    # selection_total = -0.0101
    assert abs(res["selection"] - Decimal("-0.0101")) < Decimal("1e-6")
    assert abs(res["allocation"] - (Decimal("0.005") * Decimal("1.03") - Decimal("0.01") * Decimal("1.02"))) < Decimal("1e-6")

def test_frongello_floor_protection():
    strategy = FrongelloCompounding()
    
    daily_returns = [
        {"portfolio_return": -1.0, "benchmark_return": -1.0}
    ]
    
    effects = [
        {"selection": Decimal("0.0"), "allocation": Decimal("0.0"), "execution": Decimal("0.0"), "beta": Decimal("0.0")}
    ]
    
    res = strategy.compound_returns(daily_returns, effects)
    # Floor caps portfolio/benchmark returns at -0.999999
    # Residual of actual vs cap is: (-1.0 - -0.999999) - (-1.0 - -0.999999) = 0.0
    assert res["residual"] == Decimal("0.0")

def test_menchero_compounding():
    strategy = MencheroCompounding()
    daily_returns = [
        {"portfolio_return": 0.02, "benchmark_return": 0.01},
        {"portfolio_return": 0.03, "benchmark_return": 0.02}
    ]
    effects = [
        {"selection": Decimal("0.01")},
        {"selection": Decimal("0.02")}
    ]
    res = strategy.compound_returns(daily_returns, effects)
    # Excess sum = (0.02 - 0.01) + (0.03 - 0.02) = 0.02
    # R_p = 1.02 * 1.03 - 1 = 0.0506
    # R_b = 1.01 * 1.02 - 1 = 0.0302
    # theta = (0.0506 - 0.0302) / 0.02 = 0.0204 / 0.02 = 1.02
    # selection_total = (0.01 + 0.02) * 1.02 = 0.0306
    assert abs(res["selection"] - Decimal("0.0306")) < Decimal("1e-6")

def test_canonical_serializer():
    data1 = {
        "decision_id": "urn:decision:1",
        "horizon_start": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "asset_weight": Decimal("0.45"),
        "null_val": None,
        "assets_list": [
            {"asset_urn": "urn:asset:B", "weight": 0.2},
            {"asset_urn": "urn:asset:A", "weight": 0.3}
        ]
    }
    
    data2 = {
        "asset_weight": 0.45,
        "assets_list": [
            {"weight": 0.3, "asset_urn": "urn:asset:A"},
            {"asset_urn": "urn:asset:B", "weight": 0.2}
        ],
        "decision_id": "urn:decision:1",
        "horizon_start": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "null_val": None
    }
    
    hash1 = CanonicalManifestSerializer.generate_hash(data1)
    hash2 = CanonicalManifestSerializer.generate_hash(data2)
    assert hash1 == hash2


from karsa.attribution.domain.model.lineage import reconstruct_lineage_chain

def test_lineage_reconstruction_helper():
    records = [
        PerformanceAttributionRecord(
            record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
            capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
            allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0"),
            attribution_version=1, is_active=False, superseded_by_version=2
        ),
        PerformanceAttributionRecord(
            record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
            capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
            allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0"),
            attribution_version=2, is_active=False, invalidated_by_version=3
        ),
        PerformanceAttributionRecord(
            record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
            capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
            allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0"),
            attribution_version=3, is_active=True
        )
    ]
    
    chain = reconstruct_lineage_chain(records)
    expected = "Version 1\n\u2192 superseded by Version 2\n\u2192 invalidated by Version 3"
    assert chain == expected

def test_carino_compounding():
    strategy = CarinoCompounding()
    daily_returns = [
        {"portfolio_return": 0.02, "benchmark_return": 0.01},
        {"portfolio_return": 0.03, "benchmark_return": 0.02}
    ]
    effects = [
        {"selection": Decimal("0.01")},
        {"selection": Decimal("0.02")}
    ]
    res = strategy.compound_returns(daily_returns, effects)
    assert res["selection"] > Decimal("0.0")

def test_benchmark_snapshot_validation():
    with pytest.raises(ValueError):
        BenchmarkSnapshot("", "urn:benchmark:sp500", datetime(2026, 1, 1), datetime(2026, 1, 5), {}, "")
    with pytest.raises(ValueError):
        BenchmarkSnapshot("urn:snap:1", "", datetime(2026, 1, 1), datetime(2026, 1, 5), {}, "")

def test_attribution_session_validation():
    with pytest.raises(ValueError):
        AttributionSession("", datetime(2026, 1, 1), datetime(2026, 1, 5))
    with pytest.raises(ValueError):
        AttributionSession("s1", None, datetime(2026, 1, 5))
    with pytest.raises(ValueError):
        AttributionSession("s1", datetime(2026, 1, 1), None)
    with pytest.raises(ValueError):
        AttributionSession("s1", datetime(2026, 1, 5), datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5), state="INVALID")
    with pytest.raises(ValueError):
        AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5), compounding_strategy="INVALID")

def test_performance_record_validation():
    with pytest.raises(ValueError):
        PerformanceAttributionRecord(
            record_id="", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
            capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
            allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0")
        )
    with pytest.raises(ValueError):
        PerformanceAttributionRecord(
            record_id="r1", session_id="", decision_id="d1", thesis_urn="t1", worker_urn="w1",
            capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
            allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0")
        )
    with pytest.raises(ValueError):
        PerformanceAttributionRecord(
            record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
            capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
            allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0"),
            attribution_version=0
        )

def test_performance_record_delattr():
    rec = PerformanceAttributionRecord(
        record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
        capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
        allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0")
    )
    with pytest.raises(TypeError):
        del rec.record_id



def test_abstract_repositories():
    from karsa.attribution.domain.model.repositories import AttributionSessionRepository, PerformanceAttributionRepository
    
    class DummySessionRepo(AttributionSessionRepository):
        def save(self, session): super().save(session)
        def get_by_id(self, session_id): return super().get_by_id(session_id)
        def list_all(self): return super().list_all()
        def clear(self): super().clear()

    class DummyPerfRepo(PerformanceAttributionRepository):
        def save(self, record): super().save(record)
        def find_by_id(self, record_id, version): return super().find_by_id(record_id, version)
        def find_active_by_decision(self, decision_id): return super().find_active_by_decision(decision_id)
        def find_by_session(self, session_id): return super().find_by_session(session_id)
        def list_all(self): return super().list_all()
        def deactivate_old_versions(self, decision_id, exclude_version): super().deactivate_old_versions(decision_id, exclude_version)
        def deactivate_by_session(self, session_id): super().deactivate_by_session(session_id)
        def clear(self): super().clear()

    sr = DummySessionRepo()
    sr.save(None)
    sr.get_by_id("")
    sr.list_all()
    sr.clear()

    pr = DummyPerfRepo()
    pr.save(None)
    pr.find_by_id("", 1)
    pr.find_active_by_decision("")
    pr.find_by_session("")
    pr.list_all()
    pr.deactivate_old_versions("", 1)
    pr.deactivate_by_session("")
    pr.clear()

def test_performance_record_mutation_details():
    rec = PerformanceAttributionRecord(
        record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
        capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
        allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0")
    )
    # superseded_by_version
    rec.superseded_by_version = 2
    assert rec.superseded_by_version == 2
    assert rec.aggregate_version == 2
    
    # invalidated_by_version
    rec.invalidated_by_version = 3
    assert rec.invalidated_by_version == 3
    assert rec.aggregate_version == 3
    
    # other field setting
    with pytest.raises(TypeError):
        rec.selection_return = Decimal("0.1")
        
    with pytest.raises(TypeError):
        rec.non_existent = "val"
        
    # invalid toggle is_active
    rec.is_active = False
    assert rec.is_active is False
    with pytest.raises(TypeError):
        rec.is_active = True

def test_performance_record_serialization_details():
    rec = PerformanceAttributionRecord(
        record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1", worker_urn="w1",
        capability_urn="c1", regime_urn="rg1", asset_urn="a1", selection_return=Decimal("0.0"),
        allocation_return=Decimal("0.0"), execution_return=Decimal("0.0"), beta_return=Decimal("0.0")
    )
    d = rec.to_dict()
    assert d["liquidation_tracking_residual"] == "0.0"
    assert d["superseded_by_version"] is None
    
    rec2 = PerformanceAttributionRecord.from_dict(d)
    assert rec2.record_id == "r1"
    assert rec2.liquidation_tracking_residual == Decimal("0.0")

def test_attribution_session_state_transition_details():
    session = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    
    # Invalid target states
    with pytest.raises(ValueError):
        session.transition_to("INVALID")
        
    # Invalid transition staged -> sealed
    with pytest.raises(ValueError):
        session.transition_to("SEALED")
        
    session.transition_to("COMPUTING")
    
    # Allowed fallback computing -> staged
    session.transition_to("STAGED")
    assert session.state == "STAGED"
    
    session.transition_to("COMPUTING")
    session.transition_to("CALIBRATED")
    
    # Allowed fallback calibrated -> staged
    session.transition_to("STAGED")
    assert session.state == "STAGED"
    
    session.transition_to("COMPUTING")
    session.transition_to("CALIBRATED")
    session.transition_to("SEALED")
    
    # Sealed is terminal
    with pytest.raises(ValueError):
        session.transition_to("STAGED")

def test_value_objects_math_details():
    # Frongello empty returns
    fe = FrongelloCompounding().compound_returns([], [])
    assert fe["selection"] == Decimal("0.0")
    
    # Carino empty returns
    ce = CarinoCompounding().compound_returns([], [])
    assert ce["selection"] == Decimal("0.0")
    
    # Carino same portfolio and benchmark returns
    c_same = CarinoCompounding().compound_returns(
        [{"portfolio_return": 0.05, "benchmark_return": 0.05}],
        [{"selection": Decimal("0.02")}]
    )
    assert c_same["selection"] == Decimal("0.02")
    
    # Carino negative total return value error
    with pytest.raises(ValueError, match="Logarithm of non-positive return value"):
        CarinoCompounding().compound_returns(
            [{"portfolio_return": -1.0, "benchmark_return": -0.5}],
            [{"selection": Decimal("0.0")}]
        )
        
    # Carino negative daily return value error
    with pytest.raises(ValueError, match="Logarithm of non-positive daily return"):
        CarinoCompounding().compound_returns(
            [
                {"portfolio_return": -2.0, "benchmark_return": 0.0},
                {"portfolio_return": -2.0, "benchmark_return": 0.0}
            ],
            [{"selection": Decimal("0.0")}, {"selection": Decimal("0.0")}]
        )
        
    # Menchero empty returns
    me = MencheroCompounding().compound_returns([], [])
    assert me["selection"] == Decimal("0.0")
    
    # Menchero excess_sum == 0
    m_zero = MencheroCompounding().compound_returns(
        [{"portfolio_return": 0.02, "benchmark_return": 0.02}],
        [{"selection": Decimal("0.02")}]
    )
    assert m_zero["selection"] == Decimal("0.02")

def test_canonical_manifest_serializer_details():
    from karsa.attribution.domain.model.value_objects import CanonicalManifestSerializer
    # date serialization
    d_date = date(2026, 6, 1)
    assert CanonicalManifestSerializer._normalize_val(d_date) == "2026-06-01"
    
    # datetime serialization with timezone
    from datetime import timezone
    dt_tz = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert CanonicalManifestSerializer._normalize_val(dt_tz) == "2026-06-01T10:00:00.000000Z"
    
    # lists sorting logic for items without matching keys
    lst = [
        {"decision_id": "dec-1"},
        {"session_id": "ses-1"},
        {"other_key": "val"}
    ]
    norm = CanonicalManifestSerializer._normalize_val(lst)
    assert len(norm) == 3

def test_performance_record_all_field_validations():
    """Cover all individual field validation branches in PerformanceAttributionRecord.validate()."""
    base = dict(
        record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1",
        worker_urn="w1", capability_urn="c1", regime_urn="rg1", asset_urn="a1",
        selection_return=Decimal("0.0"), allocation_return=Decimal("0.0"),
        execution_return=Decimal("0.0"), beta_return=Decimal("0.0")
    )
    # Each required field missing
    for field in ["decision_id", "thesis_urn", "worker_urn", "capability_urn", "regime_urn", "asset_urn"]:
        kwargs = {**base, field: ""}
        with pytest.raises(ValueError):
            PerformanceAttributionRecord(**kwargs)

def test_session_transition_computing_invalid():
    """Cover transition_to from COMPUTING to invalid states (CALIBRATED is valid, SEALED is not)."""
    session = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    session.transition_to("COMPUTING")
    
    # COMPUTING -> SEALED should fail (line 53)
    with pytest.raises(ValueError, match="Cannot transition from COMPUTING"):
        session.transition_to("SEALED")
    
    # COMPUTING -> CALIBRATED should succeed
    session.transition_to("CALIBRATED")
    
    # CALIBRATED -> COMPUTING should fail (line 55)
    with pytest.raises(ValueError, match="Cannot transition from CALIBRATED"):
        session.transition_to("COMPUTING")

def test_events_to_dict():
    """Cover the to_dict() methods on all four event types (lines 18, 43, 67, 89)."""
    from karsa.attribution.events.events import (
        AttributionCalculatedEvent,
        AttributionSupersededEvent,
        AttributionInvalidatedEvent,
        AttributionRecomputedEvent
    )
    
    calc_event = AttributionCalculatedEvent(
        event_id="e1", correlation_id="c1", causation_id="caus1",
        session_id="s1", records=[{"record_id": "r1"}]
    )
    d = calc_event.to_dict()
    assert d["event_type"] == "AttributionCalculatedEvent"
    assert d["event_id"] == "e1"
    assert d["records"] == [{"record_id": "r1"}]
    
    sup_event = AttributionSupersededEvent(
        event_id="e2", correlation_id="c1", causation_id="caus1",
        record_id="r1", old_version=1, new_version=2
    )
    d2 = sup_event.to_dict()
    assert d2["event_type"] == "AttributionSupersededEvent"
    assert d2["old_version"] == 1
    
    inv_event = AttributionInvalidatedEvent(
        event_id="e3", correlation_id="c1", causation_id="caus1", session_id="s1"
    )
    d3 = inv_event.to_dict()
    assert d3["event_type"] == "AttributionInvalidatedEvent"
    
    rec_event = AttributionRecomputedEvent(
        event_id="e4", correlation_id="c1", causation_id="caus1", session_id="s1"
    )
    d4 = rec_event.to_dict()
    assert d4["event_type"] == "AttributionRecomputedEvent"

def test_session_serialization_roundtrip():
    """Cover AttributionSession.to_dict and from_dict including compounding_strategy and raw_input_manifest_hash."""
    session = AttributionSession(
        "s1", datetime(2026, 1, 1), datetime(2026, 1, 5),
        compounding_strategy="CARINO", raw_input_manifest_hash="abc123"
    )
    d = session.to_dict()
    assert d["compounding_strategy"] == "CARINO"
    assert d["raw_input_manifest_hash"] == "abc123"
    
    restored = AttributionSession.from_dict(d)
    assert restored.session_id == "s1"
    assert restored.compounding_strategy == "CARINO"
    assert restored.raw_input_manifest_hash == "abc123"

def test_benchmark_snapshot_get_returns():
    """Cover BenchmarkSnapshot.get_returns_dict (line 274)."""
    snap = BenchmarkSnapshot(
        snapshot_urn="urn:snap:1", benchmark_urn="urn:bench:1",
        start_date="2026-01-01", end_date="2026-01-05",
        daily_returns={"2026-01-01": "0.01", "2026-01-02": "-0.005"},
        manifest_hash="hash1"
    )
    returns = snap.get_returns_dict()
    assert returns["2026-01-01"] == Decimal("0.01")
    assert returns["2026-01-02"] == Decimal("-0.005")


