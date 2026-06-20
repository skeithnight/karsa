"""Value object tests — Sprint-07 Wave-1."""
import pytest
from datetime import datetime

from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot, StructuredAssumption
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot, AssumptionValidation
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis
from karsa.review.domain.value_objects.review_verdict import ReviewType


class TestDecisionSnapshot:
    def _make(self, **overrides):
        defaults = dict(
            decision_id="dec-1", proposal_id="p1", journal_ref="j1",
            action_type="APPROVE", target_node_type="WORKER", target_node_id="main",
            allocated_weights={"w1": 0.6}, policy_snapshot={"id": "p1"},
            expected_return_bps=50.0, expected_drawdown_pct=5.0,
            expected_sharpe_ratio=1.5, expected_horizon_days=30,
            confidence_level=0.7, benchmark_urn=None, regime_at_decision=None,
            key_assumptions=[], attribution_expectations={},
            decision_rationale="Test", decision_confidence=0.7,
            decision_timestamp="2026-06-20T00:00:00Z",
            cryptographic_signature="sig", snapshot_hash="hash",
        )
        defaults.update(overrides)
        return DecisionSnapshot(**defaults)

    def test_valid(self):
        ds = self._make()
        assert ds.decision_id == "dec-1"

    def test_empty_decision_id_raises(self):
        with pytest.raises(ValueError, match="decision_id"):
            self._make(decision_id="")

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="confidence_level"):
            self._make(confidence_level=1.5)

    def test_zero_horizon_raises(self):
        with pytest.raises(ValueError, match="expected_horizon_days"):
            self._make(expected_horizon_days=0)

    def test_frozen(self):
        ds = self._make()
        with pytest.raises(AttributeError):
            ds.decision_id = "changed"

    def test_expected_outcome_dict(self):
        ds = self._make()
        d = ds.expected_outcome_dict
        assert d["expected_return_bps"] == 50.0
        assert d["confidence_level"] == 0.7


class TestSchedulePolicy:
    def test_create(self):
        sp = SchedulePolicy.create(30, 7, datetime(2026, 6, 20))
        assert sp.observation_window_days == 30
        assert sp.overdue_threshold_days == 7
        assert sp.due_date.month == 7

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="observation_window_days"):
            SchedulePolicy.create(0, 7, datetime(2026, 6, 20))

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError, match="overdue_threshold_days"):
            SchedulePolicy.create(30, -1, datetime(2026, 6, 20))

    def test_frozen(self):
        sp = SchedulePolicy.create(30, 7, datetime(2026, 6, 20))
        with pytest.raises(AttributeError):
            sp.observation_window_days = 60


class TestReviewTemplate:
    def test_default_allocation_review(self):
        t = ReviewTemplate.default_allocation_review()
        assert t.review_type == ReviewType.ALLOCATION_REVIEW
        assert "return_bps" in t.required_metrics

    def test_empty_template_id_raises(self):
        with pytest.raises(ValueError, match="template_id"):
            ReviewTemplate(
                template_id="", review_type=ReviewType.ALLOCATION_REVIEW,
                required_metrics=["m"], required_assumptions=[],
                evaluation_criteria={}, scoring_rules={},
            )

    def test_empty_metrics_raises(self):
        with pytest.raises(ValueError, match="required_metrics"):
            ReviewTemplate(
                template_id="t1", review_type=ReviewType.ALLOCATION_REVIEW,
                required_metrics=[], required_assumptions=[],
                evaluation_criteria={}, scoring_rules={},
            )


class TestActualOutcomeSnapshot:
    def test_valid(self):
        ao = ActualOutcomeSnapshot(
            evaluation_id="e1", target_urn="w1", observation_window_days=30,
            realized_return_bps=60.0, realized_drawdown_pct=3.0,
            realized_sharpe_ratio=1.8, benchmark_return_bps=40.0,
            regime_during_period="BULL",
        )
        assert ao.evaluation_id == "e1"

    def test_empty_evaluation_id_raises(self):
        with pytest.raises(ValueError, match="evaluation_id"):
            ActualOutcomeSnapshot(
                evaluation_id="", target_urn="w1", observation_window_days=30,
                realized_return_bps=0, realized_drawdown_pct=0,
                realized_sharpe_ratio=0, benchmark_return_bps=0,
                regime_during_period=None,
            )

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="observation_window_days"):
            ActualOutcomeSnapshot(
                evaluation_id="e1", target_urn="w1", observation_window_days=0,
                realized_return_bps=0, realized_drawdown_pct=0,
                realized_sharpe_ratio=0, benchmark_return_bps=0,
                regime_during_period=None,
            )


class TestVarianceAnalysis:
    def test_compute(self):
        v = VarianceAnalysis.compute(
            expected_return_bps=50.0, expected_drawdown_pct=5.0,
            expected_sharpe_ratio=1.5, realized_return_bps=60.0,
            realized_drawdown_pct=3.0, realized_sharpe_ratio=1.8,
            confidence_level=0.7, assumption_validations=[],
        )
        assert v.return_variance_bps == 10.0
        assert v.drawdown_variance_pct == -2.0
        assert 0.0 <= v.overall_accuracy <= 1.0

    def test_with_assumptions(self):
        assumptions = [
            AssumptionValidation("a1", "market up", "yes", "yes", True, 10.0),
            AssumptionValidation("a2", "worker active", "yes", "no", False, -5.0),
        ]
        v = VarianceAnalysis.compute(
            50.0, 5.0, 1.5, 60.0, 3.0, 1.8, 0.7, assumptions,
        )
        assert v.assumption_accuracy == 0.5

    def test_accuracy_out_of_range_raises(self):
        with pytest.raises(ValueError, match="confidence_accuracy"):
            VarianceAnalysis(10.0, -2.0, 0.3, 1.5, 0.5, 0.5)

    def test_frozen(self):
        v = VarianceAnalysis(10.0, -2.0, 0.3, 0.7, 0.9, 0.8)
        with pytest.raises(AttributeError):
            v.return_variance_bps = 999
