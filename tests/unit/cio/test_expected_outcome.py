"""Tests for ExpectedOutcome value object — Sprint-06 Wave-2."""
import pytest
from datetime import datetime

from karsa.allocation.domain.model.value_objects import (
    ExpectedOutcome, StructuredAssumption
)


def _make_outcome(**overrides):
    defaults = dict(
        expected_return_bps=50.0,
        expected_drawdown_pct=5.0,
        expected_sharpe_ratio=1.5,
        expected_horizon_days=30,
        confidence_level=0.7,
        benchmark_urn="urn:karsa:benchmark:composite",
        regime_at_decision="BULL",
        key_assumptions=[
            StructuredAssumption(
                assumption_id="a1",
                statement="Market remains in uptrend",
                validation_criteria="Composite benchmark positive",
                source_urn="urn:karsa:thesis:th-1",
            )
        ],
        attribution_expectations={"alpha": 0.7, "beta": 0.3},
    )
    defaults.update(overrides)
    return ExpectedOutcome(**defaults)


class TestExpectedOutcome:
    def test_valid_outcome(self):
        eo = _make_outcome()
        assert eo.expected_return_bps == 50.0
        assert eo.confidence_level == 0.7
        assert eo.expected_horizon_days == 30
        assert len(eo.key_assumptions) == 1

    def test_confidence_at_zero_succeeds(self):
        eo = _make_outcome(confidence_level=0.0)
        assert eo.confidence_level == 0.0

    def test_confidence_at_one_succeeds(self):
        eo = _make_outcome(confidence_level=1.0)
        assert eo.confidence_level == 1.0

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence_level must be between"):
            _make_outcome(confidence_level=-0.01)

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence_level must be between"):
            _make_outcome(confidence_level=1.01)

    def test_horizon_zero_raises(self):
        with pytest.raises(ValueError, match="expected_horizon_days must be positive"):
            _make_outcome(expected_horizon_days=0)

    def test_horizon_negative_raises(self):
        with pytest.raises(ValueError, match="expected_horizon_days must be positive"):
            _make_outcome(expected_horizon_days=-1)

    def test_horizon_one_succeeds(self):
        eo = _make_outcome(expected_horizon_days=1)
        assert eo.expected_horizon_days == 1

    def test_optional_benchmark_urn(self):
        eo = _make_outcome(benchmark_urn=None)
        assert eo.benchmark_urn is None

    def test_optional_regime(self):
        eo = _make_outcome(regime_at_decision=None)
        assert eo.regime_at_decision is None

    def test_empty_assumptions_list(self):
        eo = _make_outcome(key_assumptions=[])
        assert len(eo.key_assumptions) == 0

    def test_frozen_immutability(self):
        eo = _make_outcome()
        with pytest.raises(AttributeError):
            eo.confidence_level = 0.9


class TestStructuredAssumption:
    def test_valid_assumption(self):
        sa = StructuredAssumption(
            assumption_id="a1",
            statement="Market remains bullish",
            validation_criteria="Composite benchmark positive",
            source_urn="urn:karsa:thesis:th-1",
        )
        assert sa.assumption_id == "a1"
        assert sa.source_urn == "urn:karsa:thesis:th-1"

    def test_optional_source_urn(self):
        sa = StructuredAssumption(
            assumption_id="a1",
            statement="Test",
            validation_criteria="Test",
        )
        assert sa.source_urn is None

    def test_empty_assumption_id_raises(self):
        with pytest.raises(ValueError, match="assumption_id cannot be empty"):
            StructuredAssumption(assumption_id="", statement="x", validation_criteria="y")

    def test_empty_statement_raises(self):
        with pytest.raises(ValueError, match="statement cannot be empty"):
            StructuredAssumption(assumption_id="a1", statement="", validation_criteria="y")
