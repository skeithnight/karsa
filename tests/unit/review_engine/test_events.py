"""Event and outbox tests — Sprint-10 Wave-5."""
import pytest
import json
from datetime import datetime

from karsa.review_engine.domain.events.review_events import (
    ReviewCompletedEvent,
    ReviewDeferredEvent,
    ReviewCanonicalVersionChangedEvent,
    ReviewSizeExceededEvent,
)


# --- ReviewCompletedEvent Tests ---

class TestReviewCompletedEvent:
    def test_creation(self):
        e = ReviewCompletedEvent(
            event_id="e1", review_id="r1", evaluation_id="ev1",
            review_type="WORKER", review_version="v1.0", target_urn="w1",
            review_summary={"total_findings": 5}, review_quality={"quality_score": 0.7},
            finding_count=5, recommendation_count=3, reviewed_at="2026-06-21",
        )
        assert e.event_type == "ReviewCompletedEvent"
        assert e.event_version == 1
        assert e.schema_version == 1

    def test_metadata_present(self):
        e = ReviewCompletedEvent(
            event_id="e1", review_id="r1", evaluation_id="ev1",
            review_type="WORKER", review_version="v1.0", target_urn="w1",
            review_summary={}, review_quality={},
            finding_count=0, recommendation_count=0, reviewed_at="2026-06-21",
        )
        assert e.event_type == "ReviewCompletedEvent"
        assert e.event_version == 1
        assert e.schema_version == 1

    def test_frozen(self):
        e = ReviewCompletedEvent(
            event_id="e1", review_id="r1", evaluation_id="ev1",
            review_type="WORKER", review_version="v1.0", target_urn="w1",
            review_summary={}, review_quality={},
            finding_count=0, recommendation_count=0, reviewed_at="2026-06-21",
        )
        with pytest.raises(AttributeError):
            e.event_id = "changed"


# --- ReviewDeferredEvent Tests ---

class TestReviewDeferredEvent:
    def test_creation(self):
        e = ReviewDeferredEvent(
            event_id="e1", evaluation_id="ev1", review_type="WORKER",
            reason="Quality below threshold", quality_score=0.2,
            missing_data=["regime_data"], deferred_at="2026-06-21",
        )
        assert e.event_type == "ReviewDeferredEvent"
        assert e.quality_score == 0.2

    def test_metadata_present(self):
        e = ReviewDeferredEvent(
            event_id="e1", evaluation_id="ev1", review_type="WORKER",
            reason="r", quality_score=0.2, missing_data=[], deferred_at="2026-06-21",
        )
        assert e.event_version == 1
        assert e.schema_version == 1


# --- ReviewCanonicalVersionChangedEvent Tests ---

class TestReviewCanonicalVersionChangedEvent:
    def test_creation(self):
        e = ReviewCanonicalVersionChangedEvent(
            event_id="e1", evaluation_id="ev1", review_type="WORKER",
            previous_review_id="r1", new_review_id="r2",
            changed_at="2026-06-21", changed_by="system",
        )
        assert e.event_type == "ReviewCanonicalVersionChangedEvent"
        assert e.previous_review_id == "r1"
        assert e.new_review_id == "r2"

    def test_no_previous_review(self):
        e = ReviewCanonicalVersionChangedEvent(
            event_id="e1", evaluation_id="ev1", review_type="WORKER",
            previous_review_id=None, new_review_id="r1",
            changed_at="2026-06-21", changed_by="system",
        )
        assert e.previous_review_id is None


# --- ReviewSizeExceededEvent Tests ---

class TestReviewSizeExceededEvent:
    def test_creation(self):
        e = ReviewSizeExceededEvent(
            event_id="e1", review_id="r1",
            finding_count=150, recommendation_count=60,
            limit_findings=100, limit_recommendations=50,
            exceeded_at="2026-06-21",
        )
        assert e.event_type == "ReviewSizeExceededEvent"
        assert e.finding_count == 150
        assert e.limit_findings == 100

    def test_metadata_present(self):
        e = ReviewSizeExceededEvent(
            event_id="e1", review_id="r1",
            finding_count=150, recommendation_count=60,
            limit_findings=100, limit_recommendations=50,
            exceeded_at="2026-06-21",
        )
        assert e.event_version == 1
        assert e.schema_version == 1


# --- Event Metadata Tests ---

class TestEventMetadata:
    def test_all_events_have_version_fields(self):
        events = [
            ReviewCompletedEvent(event_id="e1", review_id="r1", evaluation_id="ev1",
                review_type="WORKER", review_version="v1.0", target_urn="w1",
                review_summary={}, review_quality={}, finding_count=0,
                recommendation_count=0, reviewed_at="2026-06-21"),
            ReviewDeferredEvent(event_id="e1", evaluation_id="ev1", review_type="WORKER",
                reason="r", quality_score=0.2, missing_data=[], deferred_at="2026-06-21"),
            ReviewCanonicalVersionChangedEvent(event_id="e1", evaluation_id="ev1",
                review_type="WORKER", previous_review_id=None, new_review_id="r1",
                changed_at="2026-06-21", changed_by="sys"),
            ReviewSizeExceededEvent(event_id="e1", review_id="r1", finding_count=100,
                recommendation_count=50, limit_findings=100, limit_recommendations=50,
                exceeded_at="2026-06-21"),
        ]
        for e in events:
            assert e.event_version == 1
            assert e.schema_version == 1
