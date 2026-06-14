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
