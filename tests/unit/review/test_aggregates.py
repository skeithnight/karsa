"""Aggregate tests — Sprint-07 Wave-1."""
import pytest
from datetime import datetime

from karsa.review.domain.aggregates.review_cycle import ReviewCycle, ImmutableLedgerEntry
from karsa.review.domain.aggregates.review_record import ReviewRecord
from karsa.review.domain.aggregates.attribution_entry import AttributionEntry
from karsa.review.domain.aggregates.capability_score_adjustment import CapabilityScoreAdjustment
from karsa.review.domain.aggregates.outbox_event import OutboxEvent, OutboxStatus
from karsa.review.domain.value_objects.review_verdict import (
    ReviewType, ReviewVerdict, AttributionDimension, AttributionType,
)
from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot, StructuredAssumption
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot, AssumptionValidation
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis


def _make_snapshot():
    return DecisionSnapshot(
        decision_id="dec-1",
        proposal_id="prop-1",
        journal_ref="urn:karsa:journal:j1",
        action_type="APPROVE_ALLOCATION",
        target_node_type="WORKER",
        target_node_id="portfolio-main",
        allocated_weights={"w1": 0.6, "w2": 0.4},
        policy_snapshot={"policy_id": "p1"},
        expected_return_bps=50.0,
        expected_drawdown_pct=5.0,
        expected_sharpe_ratio=1.5,
        expected_horizon_days=30,
        confidence_level=0.7,
        benchmark_urn=None,
        regime_at_decision=None,
        key_assumptions=[],
        attribution_expectations={},
        decision_rationale="Test",
        decision_confidence=0.7,
        decision_timestamp="2026-06-20T00:00:00Z",
        cryptographic_signature="sig",
        snapshot_hash="hash123",
    )


def _make_schedule():
    return SchedulePolicy.create(
        observation_window_days=30,
        overdue_threshold_days=7,
        created_at=datetime(2026, 6, 20),
    )


def _make_template():
    return ReviewTemplate.default_allocation_review()


def _make_actual_outcome():
    return ActualOutcomeSnapshot(
        evaluation_id="eval-1",
        target_urn="urn:karsa:worker:analyst-1",
        observation_window_days=30,
        realized_return_bps=60.0,
        realized_drawdown_pct=3.0,
        realized_sharpe_ratio=1.8,
        benchmark_return_bps=40.0,
        regime_during_period="BULL",
        assumption_validations=[],
        actual_attribution={"w1": 0.6},
    )


def _make_variance():
    return VarianceAnalysis.compute(
        expected_return_bps=50.0,
        expected_drawdown_pct=5.0,
        expected_sharpe_ratio=1.5,
        realized_return_bps=60.0,
        realized_drawdown_pct=3.0,
        realized_sharpe_ratio=1.8,
        confidence_level=0.7,
        assumption_validations=[],
    )


class TestReviewCycle:
    def test_valid_creation(self):
        cycle = ReviewCycle(
            cycle_id="cycle-1",
            decision_id="dec-1",
            proposal_id="prop-1",
            journal_ref="urn:karsa:journal:j1",
            review_type=ReviewType.ALLOCATION_REVIEW,
            decision_snapshot=_make_snapshot(),
            schedule_policy=_make_schedule(),
            review_template=_make_template(),
            eligibility_event_ref="elig-1",
            created_at=datetime.utcnow(),
            created_by="system",
        )
        assert cycle.cycle_id == "cycle-1"
        assert cycle.review_type == ReviewType.ALLOCATION_REVIEW

    def test_empty_cycle_id_raises(self):
        with pytest.raises(ValueError, match="cycle_id cannot be empty"):
            ReviewCycle(
                cycle_id="", decision_id="dec-1", proposal_id=None,
                journal_ref="j1", review_type=ReviewType.ALLOCATION_REVIEW,
                decision_snapshot=_make_snapshot(), schedule_policy=_make_schedule(),
                review_template=_make_template(), eligibility_event_ref="e1",
                created_at=datetime.utcnow(), created_by="system",
            )

    def test_empty_decision_id_raises(self):
        with pytest.raises(ValueError, match="decision_id cannot be empty"):
            ReviewCycle(
                cycle_id="c1", decision_id="", proposal_id=None,
                journal_ref="j1", review_type=ReviewType.ALLOCATION_REVIEW,
                decision_snapshot=_make_snapshot(), schedule_policy=_make_schedule(),
                review_template=_make_template(), eligibility_event_ref="e1",
                created_at=datetime.utcnow(), created_by="system",
            )

    def test_immutability(self):
        cycle = ReviewCycle(
            cycle_id="c1", decision_id="dec-1", proposal_id=None,
            journal_ref="j1", review_type=ReviewType.ALLOCATION_REVIEW,
            decision_snapshot=_make_snapshot(), schedule_policy=_make_schedule(),
            review_template=_make_template(), eligibility_event_ref="e1",
            created_at=datetime.utcnow(), created_by="system",
        )
        with pytest.raises(AttributeError):
            cycle.cycle_id = "changed"

    def test_schedule_due_date_property(self):
        cycle = ReviewCycle(
            cycle_id="c1", decision_id="dec-1", proposal_id=None,
            journal_ref="j1", review_type=ReviewType.ALLOCATION_REVIEW,
            decision_snapshot=_make_snapshot(), schedule_policy=_make_schedule(),
            review_template=_make_template(), eligibility_event_ref="e1",
            created_at=datetime.utcnow(), created_by="system",
        )
        assert cycle.schedule_due_date.year == 2026
        assert cycle.schedule_due_date.month == 7


class TestReviewRecord:
    def test_valid_creation(self):
        record = ReviewRecord(
            review_id="rev-1", cycle_id="c1",
            review_type=ReviewType.ALLOCATION_REVIEW,
            decision_snapshot=_make_snapshot(),
            actual_outcome=_make_actual_outcome(),
            variance=_make_variance(),
            verdict=ReviewVerdict.OUTPERFORMED,
            rationale="Exceeded expectations.",
            executed_at=datetime.utcnow(),
            executed_by="cio-1",
        )
        assert record.review_id == "rev-1"
        assert record.verdict == ReviewVerdict.OUTPERFORMED

    def test_determine_verdict_outperformed(self):
        variance = VarianceAnalysis(
            return_variance_bps=10.0, drawdown_variance_pct=-2.0,
            sharpe_variance=0.3, confidence_accuracy=0.8,
            assumption_accuracy=0.9, overall_accuracy=0.85,
        )
        verdict = ReviewRecord.determine_verdict(variance, return_threshold=0.0)
        assert verdict == ReviewVerdict.OUTPERFORMED

    def test_determine_verdict_failed(self):
        variance = VarianceAnalysis(
            return_variance_bps=-100.0, drawdown_variance_pct=10.0,
            sharpe_variance=-1.0, confidence_accuracy=0.1,
            assumption_accuracy=0.1, overall_accuracy=0.2,
        )
        verdict = ReviewRecord.determine_verdict(variance)
        assert verdict == ReviewVerdict.FAILED

    def test_immutability(self):
        record = ReviewRecord(
            review_id="rev-1", cycle_id="c1",
            review_type=ReviewType.ALLOCATION_REVIEW,
            decision_snapshot=_make_snapshot(),
            actual_outcome=_make_actual_outcome(),
            variance=_make_variance(),
            verdict=ReviewVerdict.MET_EXPECTATIONS,
            rationale="Met.", executed_at=datetime.utcnow(), executed_by="cio",
        )
        with pytest.raises(AttributeError):
            record.verdict = ReviewVerdict.FAILED


class TestAttributionEntry:
    def test_from_contribution_positive(self):
        entry = AttributionEntry.from_contribution(
            attribution_id="a1", review_id="rev-1",
            dimension=AttributionDimension.WORKER,
            target_urn="urn:karsa:worker:analyst-1",
            contribution_bps=30.0, total_bps=60.0,
            evidence={"source": "test"}, created_at=datetime.utcnow(),
        )
        assert entry.attribution_type == AttributionType.POSITIVE
        assert entry.contribution_pct == 0.5

    def test_from_contribution_negative(self):
        entry = AttributionEntry.from_contribution(
            attribution_id="a2", review_id="rev-1",
            dimension=AttributionDimension.WORKER,
            target_urn="urn:karsa:worker:analyst-2",
            contribution_bps=-20.0, total_bps=60.0,
            evidence={}, created_at=datetime.utcnow(),
        )
        assert entry.attribution_type == AttributionType.NEGATIVE
        assert entry.contribution_pct < 0

    def test_immutability(self):
        entry = AttributionEntry.from_contribution(
            attribution_id="a1", review_id="rev-1",
            dimension=AttributionDimension.WORKER,
            target_urn="w1", contribution_bps=10.0, total_bps=10.0,
            evidence={}, created_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            entry.contribution_bps = 999


class TestCapabilityScoreAdjustment:
    def test_from_attribution_positive(self):
        adj = CapabilityScoreAdjustment.from_attribution(
            adjustment_id="adj-1", target_urn="w1", target_type="WORKER",
            contribution_bps=50.0, review_id="rev-1", created_at=datetime.utcnow(),
        )
        assert adj.score_delta > 0
        assert adj.confidence_delta == 0.01

    def test_from_attribution_negative(self):
        adj = CapabilityScoreAdjustment.from_attribution(
            adjustment_id="adj-2", target_urn="w1", target_type="WORKER",
            contribution_bps=-30.0, review_id="rev-1", created_at=datetime.utcnow(),
        )
        assert adj.score_delta < 0
        assert adj.confidence_delta == -0.01

    def test_immutability(self):
        adj = CapabilityScoreAdjustment.from_attribution(
            adjustment_id="adj-1", target_urn="w1", target_type="WORKER",
            contribution_bps=10.0, review_id="rev-1", created_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            adj.score_delta = 999


class TestOutboxEvent:
    def test_valid_creation(self):
        event = OutboxEvent(
            outbox_id="out-1", event_type="ReviewExecutedEvent",
            payload={"review_id": "r1"}, aggregate_id="r1",
        )
        assert event.status == OutboxStatus.PENDING
        assert event.is_pending

    def test_mark_sent(self):
        event = OutboxEvent(
            outbox_id="out-1", event_type="TestEvent",
            payload={}, aggregate_id="a1",
        )
        now = datetime.utcnow()
        event.mark_sent(now)
        assert event.status == OutboxStatus.SENT
        assert event.is_sent
        assert event.sent_at == now

    def test_mark_sent_twice_raises(self):
        event = OutboxEvent(
            outbox_id="out-1", event_type="TestEvent",
            payload={}, aggregate_id="a1",
        )
        event.mark_sent(datetime.utcnow())
        with pytest.raises(ValueError, match="already sent"):
            event.mark_sent(datetime.utcnow())

    def test_mark_failed(self):
        event = OutboxEvent(
            outbox_id="out-1", event_type="TestEvent",
            payload={}, aggregate_id="a1",
        )
        event.mark_failed()
        assert event.is_failed

    def test_increment_retry(self):
        event = OutboxEvent(
            outbox_id="out-1", event_type="TestEvent",
            payload={}, aggregate_id="a1",
        )
        assert event.retry_count == 0
        event.increment_retry()
        assert event.retry_count == 1
