"""JSONB roundtrip tests — Sprint-07 Wave-2C."""
import pytest
import json
from datetime import datetime

from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot, StructuredAssumption
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot, AssumptionValidation
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis
from karsa.review.domain.value_objects.review_verdict import ReviewType
from karsa.review.infrastructure.jsonb_serializers import (
    serialize_decision_snapshot, deserialize_decision_snapshot,
    serialize_schedule_policy, deserialize_schedule_policy,
    serialize_review_template, deserialize_review_template,
    serialize_actual_outcome, deserialize_actual_outcome,
    serialize_variance, deserialize_variance,
    to_jsonb, from_jsonb,
)


def _make_decision_snapshot():
    return DecisionSnapshot(
        decision_id="dec-1", proposal_id="p1", journal_ref="j1",
        action_type="APPROVE", target_node_type="WORKER", target_node_id="main",
        allocated_weights={"w1": 0.6, "w2": 0.4}, policy_snapshot={"id": "p1"},
        expected_return_bps=50.0, expected_drawdown_pct=5.0,
        expected_sharpe_ratio=1.5, expected_horizon_days=30,
        confidence_level=0.7, benchmark_urn=None, regime_at_decision=None,
        key_assumptions=[
            StructuredAssumption(assumption_id="a1", statement="Market up",
                                 validation_criteria="positive return", source_urn="urn:1"),
        ],
        attribution_expectations={"w1": 0.6},
        decision_rationale="Test", decision_confidence=0.7,
        decision_timestamp="2026-06-20T00:00:00Z",
        cryptographic_signature="sig", snapshot_hash="hash",
    )


class TestDecisionSnapshotRoundtrip:
    def test_roundtrip(self):
        original = _make_decision_snapshot()
        serialized = serialize_decision_snapshot(original)
        json_str = to_jsonb(serialized)
        deserialized = from_jsonb(json_str)
        result = deserialize_decision_snapshot(deserialized)

        assert result.decision_id == original.decision_id
        assert result.proposal_id == original.proposal_id
        assert result.confidence_level == original.confidence_level
        assert len(result.key_assumptions) == 1
        assert result.key_assumptions[0].assumption_id == "a1"
        assert result.allocated_weights == original.allocated_weights

    def test_empty_assumptions(self):
        ds = _make_decision_snapshot()
        object.__setattr__(ds, 'key_assumptions', [])
        serialized = serialize_decision_snapshot(ds)
        result = deserialize_decision_snapshot(serialized)
        assert result.key_assumptions == []


class TestSchedulePolicyRoundtrip:
    def test_roundtrip(self):
        original = SchedulePolicy.create(30, 7, datetime(2026, 6, 20))
        serialized = serialize_schedule_policy(original)
        json_str = to_jsonb(serialized)
        deserialized = from_jsonb(json_str)
        result = deserialize_schedule_policy(deserialized)

        assert result.observation_window_days == 30
        assert result.overdue_threshold_days == 7
        assert result.auto_expire is False


class TestReviewTemplateRoundtrip:
    def test_roundtrip(self):
        original = ReviewTemplate.default_allocation_review()
        serialized = serialize_review_template(original)
        json_str = to_jsonb(serialized)
        deserialized = from_jsonb(json_str)
        result = deserialize_review_template(deserialized)

        assert result.template_id == original.template_id
        assert result.review_type == ReviewType.ALLOCATION_REVIEW
        assert result.required_metrics == original.required_metrics


class TestActualOutcomeRoundtrip:
    def test_roundtrip(self):
        original = ActualOutcomeSnapshot(
            evaluation_id="e1", target_urn="w1", observation_window_days=30,
            realized_return_bps=60.0, realized_drawdown_pct=3.0,
            realized_sharpe_ratio=1.8, benchmark_return_bps=40.0,
            regime_during_period="BULL",
            assumption_validations=[
                AssumptionValidation("a1", "market up", "yes", "yes", True, 10.0),
            ],
            actual_attribution={"w1": 0.6},
        )
        serialized = serialize_actual_outcome(original)
        json_str = to_jsonb(serialized)
        deserialized = from_jsonb(json_str)
        result = deserialize_actual_outcome(deserialized)

        assert result.evaluation_id == "e1"
        assert result.realized_return_bps == 60.0
        assert len(result.assumption_validations) == 1
        assert result.assumption_validations[0].validated is True


class TestVarianceRoundtrip:
    def test_roundtrip(self):
        original = VarianceAnalysis.compute(
            50.0, 5.0, 1.5, 60.0, 3.0, 1.8, 0.7, [],
        )
        serialized = serialize_variance(original)
        json_str = to_jsonb(serialized)
        deserialized = from_jsonb(json_str)
        result = deserialize_variance(deserialized)

        assert result.return_variance_bps == original.return_variance_bps
        assert result.overall_accuracy == original.overall_accuracy


class TestJsonbHelpers:
    def test_to_jsonb_dict(self):
        data = {"key": "value", "num": 42}
        result = to_jsonb(data)
        assert isinstance(result, str)
        assert json.loads(result) == data

    def test_from_jsonb_string(self):
        data = '{"key": "value"}'
        result = from_jsonb(data)
        assert result == {"key": "value"}

    def test_from_jsonb_dict(self):
        data = {"key": "value"}
        result = from_jsonb(data)
        assert result == {"key": "value"}
