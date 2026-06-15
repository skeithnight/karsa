import pytest
from decimal import Decimal
from datetime import datetime
from karsa.performance.domain.exceptions import InvalidScoreError, InvalidRegimeDistributionError
from karsa.performance.domain.value_objects import BrierScore, RegimeDistribution, OutcomeStatus, ForecastError, EvaluationHorizon
from karsa.performance.domain.models import OutcomeRecord, PerformanceEvaluation, CalibrationLedgerEntry

def test_brier_score_valid():
    score = BrierScore(Decimal("1.5"))
    assert score.value == Decimal("1.5")

def test_brier_score_invalid_high():
    with pytest.raises(InvalidScoreError):
        BrierScore(Decimal("2.1"))

def test_brier_score_invalid_low():
    with pytest.raises(InvalidScoreError):
        BrierScore(Decimal("-0.1"))

def test_regime_distribution_valid():
    regime = RegimeDistribution({"Bull": Decimal("0.6"), "Bear": Decimal("0.4")})
    assert regime.distribution["Bull"] == Decimal("0.6")

def test_regime_distribution_empty():
    with pytest.raises(InvalidRegimeDistributionError):
        RegimeDistribution({})

def test_regime_distribution_sum_invalid():
    with pytest.raises(InvalidRegimeDistributionError):
        RegimeDistribution({"Bull": Decimal("0.6"), "Bear": Decimal("0.5")})

def test_outcome_record():
    dt = datetime(2026, 1, 1)
    record = OutcomeRecord("urn1", "price", Decimal("100"), dt)
    assert record.status == OutcomeStatus.PENDING
    
    record.resolve(Decimal("110"))
    assert record.final_value == Decimal("110")
    assert record.status == OutcomeStatus.RESOLVED
    
    record.fail()
    assert record.status == OutcomeStatus.FAILED

def test_performance_evaluation():
    dt = datetime(2026, 1, 1)
    regime = RegimeDistribution({"Bull": Decimal("1.0")})
    eval_record = PerformanceEvaluation(
        "e_urn", "o_urn", "t_urn", "d_urn", "w_urn",
        ForecastError(Decimal("0.5")), regime, EvaluationHorizon.NINETY_DAY, dt
    )
    assert eval_record.eval_urn == "e_urn"

def test_calibration_ledger_entry():
    dt = datetime(2026, 1, 1)
    score = BrierScore(Decimal("0.2"))
    entry = CalibrationLedgerEntry("l_urn", "prev_l_urn", "w_urn", score, dt)
    assert entry.ledger_urn == "l_urn"
    assert entry.previous_ledger_urn == "prev_l_urn"


def test_events():
    from karsa.performance.domain.events import OutcomeRecorded, PerformanceEvaluated, CalibrationAppended
    dt = datetime(2026, 1, 1)
    
    e1 = OutcomeRecorded("urn1", "metric", Decimal("100"), dt)
    assert e1.outcome_urn == "urn1"
    
    e2 = PerformanceEvaluated("eval", "out", "thes", "dec", "work", Decimal("0.5"), {"Bull": Decimal("1.0")}, dt)
    assert e2.eval_urn == "eval"
    
    e3 = CalibrationAppended("l_urn", "w_urn", Decimal("0.2"), dt)
    assert e3.ledger_urn == "l_urn"

def test_lineage():
    from karsa.performance.domain.lineage import validate_calibration_ledger_lineage
    from karsa.performance.domain.exceptions import TemporalLedgerError
    
    dt = datetime(2026, 1, 1)
    score = BrierScore(Decimal("0.2"))
    entry1 = CalibrationLedgerEntry("l1", None, "w1", score, dt)
    entry2 = CalibrationLedgerEntry("l2", "l1", "w1", score, dt)
    
    # Valid
    validate_calibration_ledger_lineage([entry1, entry2])
    
    # Cycle
    entry3 = CalibrationLedgerEntry("l1", "l2", "w1", score, dt)
    with pytest.raises(TemporalLedgerError):
        validate_calibration_ledger_lineage([entry1, entry2, entry3])
