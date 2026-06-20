"""Event tests — Sprint-07 Wave-1."""
import pytest
from datetime import datetime

from karsa.review.domain.events.review_events import (
    ReviewEligibilityEvaluatedEvent,
    ReviewCycleCreatedEvent,
    ReviewDueEvent,
    ReviewOverdueEvent,
    ReviewExecutedEvent,
    AttributionGeneratedEvent,
    CapabilityScoreAdjustmentCreatedEvent,
)


class TestReviewEligibilityEvaluatedEvent:
    def test_valid(self):
        e = ReviewEligibilityEvaluatedEvent(
            event_id="e1", evaluation_id="ev1", decision_id="d1",
            eligible=True, review_type="ALLOCATION_REVIEW",
            strategy_name="default", strategy_version="1.0",
            evaluation_reason="Approved decision", evaluated_at=datetime.utcnow(),
        )
        assert e.event_type == "ReviewEligibilityEvaluatedEvent"
        assert e.event_version == 1
        assert e.eligible is True

    def test_ineligible(self):
        e = ReviewEligibilityEvaluatedEvent(
            event_id="e2", evaluation_id="ev2", decision_id="d2",
            eligible=False, review_type=None,
            strategy_name="default", strategy_version="1.0",
            evaluation_reason="Below threshold", evaluated_at=datetime.utcnow(),
        )
        assert e.eligible is False
        assert e.review_type is None

    def test_empty_evaluation_id_raises(self):
        with pytest.raises(ValueError, match="evaluation_id"):
            ReviewEligibilityEvaluatedEvent(
                event_id="e1", evaluation_id="", decision_id="d1",
                eligible=True, review_type=None,
                strategy_name="s", strategy_version="1",
                evaluation_reason="r", evaluated_at=datetime.utcnow(),
            )

    def test_frozen(self):
        e = ReviewEligibilityEvaluatedEvent(
            event_id="e1", evaluation_id="ev1", decision_id="d1",
            eligible=True, review_type=None,
            strategy_name="s", strategy_version="1",
            evaluation_reason="r", evaluated_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            e.eligible = False

    def test_to_dict(self):
        e = ReviewEligibilityEvaluatedEvent(
            event_id="e1", evaluation_id="ev1", decision_id="d1",
            eligible=True, review_type="ALLOCATION_REVIEW",
            strategy_name="default", strategy_version="1.0",
            evaluation_reason="Approved", evaluated_at=datetime(2026, 6, 20),
        )
        d = e.to_dict()
        assert d["eligible"] is True
        assert d["strategy_name"] == "default"


class TestReviewCycleCreatedEvent:
    def test_valid(self):
        e = ReviewCycleCreatedEvent(
            event_id="e1", cycle_id="c1", decision_id="d1",
            proposal_id="p1", journal_ref="j1",
            review_type="ALLOCATION_REVIEW",
            decision_snapshot={}, schedule_policy={}, review_template={},
            eligibility_event_ref="ev1", created_by="system",
            created_at=datetime.utcnow(),
        )
        assert e.event_type == "ReviewCycleCreatedEvent"

    def test_empty_cycle_id_raises(self):
        with pytest.raises(ValueError, match="cycle_id"):
            ReviewCycleCreatedEvent(
                event_id="e1", cycle_id="", decision_id="d1",
                proposal_id=None, journal_ref="j1",
                review_type="ALLOCATION_REVIEW",
                decision_snapshot={}, schedule_policy={}, review_template={},
                eligibility_event_ref="ev1", created_by="system",
                created_at=datetime.utcnow(),
            )


class TestReviewDueEvent:
    def test_valid(self):
        e = ReviewDueEvent(
            event_id="e1", cycle_id="c1",
            review_due_date=datetime(2026, 7, 20),
            days_until_due=30, created_at=datetime.utcnow(),
        )
        assert e.event_type == "ReviewDueEvent"

    def test_empty_cycle_id_raises(self):
        with pytest.raises(ValueError, match="cycle_id"):
            ReviewDueEvent(
                event_id="e1", cycle_id="",
                review_due_date=datetime(2026, 7, 20),
                days_until_due=30, created_at=datetime.utcnow(),
            )


class TestReviewOverdueEvent:
    def test_valid(self):
        e = ReviewOverdueEvent(
            event_id="e1", cycle_id="c1",
            days_overdue=5, original_due_date=datetime(2026, 7, 20),
            detected_at=datetime.utcnow(),
        )
        assert e.event_type == "ReviewOverdueEvent"
        assert e.days_overdue == 5


class TestReviewExecutedEvent:
    def test_valid(self):
        e = ReviewExecutedEvent(
            event_id="e1", review_id="r1", cycle_id="c1",
            review_type="ALLOCATION_REVIEW",
            actual_outcome={}, variance={},
            verdict="OUTPERFORMED", rationale="Exceeded",
            executed_by="cio-1", executed_at=datetime.utcnow(),
        )
        assert e.event_type == "ReviewExecutedEvent"

    def test_empty_review_id_raises(self):
        with pytest.raises(ValueError, match="review_id"):
            ReviewExecutedEvent(
                event_id="e1", review_id="", cycle_id="c1",
                review_type="ALLOCATION_REVIEW",
                actual_outcome={}, variance={},
                verdict="OUTPERFORMED", rationale="r",
                executed_by="cio", executed_at=datetime.utcnow(),
            )


class TestAttributionGeneratedEvent:
    def test_valid(self):
        e = AttributionGeneratedEvent(
            event_id="e1", attribution_id="a1", review_id="r1",
            dimension="WORKER", target_urn="w1",
            contribution_bps=30.0, contribution_pct=0.5,
            attribution_type="POSITIVE", evidence={},
            created_at=datetime.utcnow(),
        )
        assert e.event_type == "AttributionGeneratedEvent"

    def test_to_dict(self):
        e = AttributionGeneratedEvent(
            event_id="e1", attribution_id="a1", review_id="r1",
            dimension="WORKER", target_urn="w1",
            contribution_bps=30.0, contribution_pct=0.5,
            attribution_type="POSITIVE", evidence={"key": "val"},
            created_at=datetime(2026, 6, 20),
        )
        d = e.to_dict()
        assert d["dimension"] == "WORKER"
        assert d["contribution_bps"] == 30.0


class TestCapabilityScoreAdjustmentCreatedEvent:
    def test_valid(self):
        e = CapabilityScoreAdjustmentCreatedEvent(
            event_id="e1", adjustment_id="adj-1",
            target_urn="w1", target_type="WORKER",
            score_delta=0.005, confidence_delta=0.01,
            review_id="r1", rationale="Positive contribution",
            created_at=datetime.utcnow(),
        )
        assert e.event_type == "CapabilityScoreAdjustmentCreatedEvent"

    def test_empty_adjustment_id_raises(self):
        with pytest.raises(ValueError, match="adjustment_id"):
            CapabilityScoreAdjustmentCreatedEvent(
                event_id="e1", adjustment_id="",
                target_urn="w1", target_type="WORKER",
                score_delta=0.0, confidence_delta=0.0,
                review_id="r1", rationale="r",
                created_at=datetime.utcnow(),
            )
