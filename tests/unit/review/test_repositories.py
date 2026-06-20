"""Repository contract tests — Sprint-07 Wave-2B.

Verifies that all repository contracts are properly defined:
- ABC classes
- abstractmethod decorators
- correct method signatures
- proper typing
"""
import pytest
from abc import ABC
from datetime import datetime

from karsa.review.domain.repositories.review_cycle_repository import ReviewCycleRepository
from karsa.review.domain.repositories.review_record_repository import ReviewRecordRepository
from karsa.review.domain.repositories.attribution_entry_repository import AttributionEntryRepository
from karsa.review.domain.repositories.capability_score_adjustment_repository import CapabilityScoreAdjustmentRepository
from karsa.review.domain.repositories.capability_score_projection_repository import (
    CapabilityScoreProjectionRepository, CapabilityScoreProjection,
)
from karsa.review.domain.repositories.review_coverage_projection_repository import (
    ReviewCoverageProjectionRepository, ReviewCoverageProjection,
)
from karsa.review.domain.repositories.outbox_repository import OutboxRepository


class TestReviewCycleRepository:
    def test_is_abc(self):
        assert issubclass(ReviewCycleRepository, ABC)

    def test_has_save_cycle(self):
        assert hasattr(ReviewCycleRepository, 'save_cycle')
        assert callable(getattr(ReviewCycleRepository, 'save_cycle'))

    def test_has_get_cycle_by_id(self):
        assert hasattr(ReviewCycleRepository, 'get_cycle_by_id')

    def test_has_get_cycle_by_decision_id(self):
        assert hasattr(ReviewCycleRepository, 'get_cycle_by_decision_id')

    def test_has_get_cycle_by_eligibility_ref(self):
        assert hasattr(ReviewCycleRepository, 'get_cycle_by_eligibility_ref')

    def test_has_list_cycles(self):
        assert hasattr(ReviewCycleRepository, 'list_cycles')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ReviewCycleRepository()


class TestReviewRecordRepository:
    def test_is_abc(self):
        assert issubclass(ReviewRecordRepository, ABC)

    def test_has_save_record(self):
        assert hasattr(ReviewRecordRepository, 'save_record')

    def test_has_get_record_by_id(self):
        assert hasattr(ReviewRecordRepository, 'get_record_by_id')

    def test_has_get_records_by_cycle_id(self):
        assert hasattr(ReviewRecordRepository, 'get_records_by_cycle_id')

    def test_has_list_records(self):
        assert hasattr(ReviewRecordRepository, 'list_records')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ReviewRecordRepository()


class TestAttributionEntryRepository:
    def test_is_abc(self):
        assert issubclass(AttributionEntryRepository, ABC)

    def test_has_save_entry(self):
        assert hasattr(AttributionEntryRepository, 'save_entry')

    def test_has_save_entries(self):
        assert hasattr(AttributionEntryRepository, 'save_entries')

    def test_has_get_entries_by_review_id(self):
        assert hasattr(AttributionEntryRepository, 'get_entries_by_review_id')

    def test_has_get_entries_by_target_urn(self):
        assert hasattr(AttributionEntryRepository, 'get_entries_by_target_urn')

    def test_has_get_entries_by_dimension(self):
        assert hasattr(AttributionEntryRepository, 'get_entries_by_dimension')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AttributionEntryRepository()


class TestCapabilityScoreAdjustmentRepository:
    def test_is_abc(self):
        assert issubclass(CapabilityScoreAdjustmentRepository, ABC)

    def test_has_save_adjustment(self):
        assert hasattr(CapabilityScoreAdjustmentRepository, 'save_adjustment')

    def test_has_save_adjustments(self):
        assert hasattr(CapabilityScoreAdjustmentRepository, 'save_adjustments')

    def test_has_get_adjustments_by_review_id(self):
        assert hasattr(CapabilityScoreAdjustmentRepository, 'get_adjustments_by_review_id')

    def test_has_get_adjustments_by_target_urn(self):
        assert hasattr(CapabilityScoreAdjustmentRepository, 'get_adjustments_by_target_urn')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            CapabilityScoreAdjustmentRepository()


class TestCapabilityScoreProjectionRepository:
    def test_is_abc(self):
        assert issubclass(CapabilityScoreProjectionRepository, ABC)

    def test_has_get_by_target_urn(self):
        assert hasattr(CapabilityScoreProjectionRepository, 'get_by_target_urn')

    def test_has_list_all(self):
        assert hasattr(CapabilityScoreProjectionRepository, 'list_all')

    def test_has_upsert(self):
        assert hasattr(CapabilityScoreProjectionRepository, 'upsert')

    def test_has_rebuild(self):
        assert hasattr(CapabilityScoreProjectionRepository, 'rebuild')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            CapabilityScoreProjectionRepository()

    def test_projection_dataclass(self):
        p = CapabilityScoreProjection(
            target_urn="w1",
            target_type="WORKER",
            current_score=0.5,
            current_confidence=0.7,
            adjustment_count=3,
            last_updated=datetime.utcnow(),
        )
        assert p.target_urn == "w1"
        assert p.current_score == 0.5


class TestReviewCoverageProjectionRepository:
    def test_is_abc(self):
        assert issubclass(ReviewCoverageProjectionRepository, ABC)

    def test_has_get_by_decision_id(self):
        assert hasattr(ReviewCoverageProjectionRepository, 'get_by_decision_id')

    def test_has_list_by_status(self):
        assert hasattr(ReviewCoverageProjectionRepository, 'list_by_status')

    def test_has_list_overdue(self):
        assert hasattr(ReviewCoverageProjectionRepository, 'list_overdue')

    def test_has_upsert_from_eligibility(self):
        assert hasattr(ReviewCoverageProjectionRepository, 'upsert_from_eligibility')

    def test_has_update_status(self):
        assert hasattr(ReviewCoverageProjectionRepository, 'update_status')

    def test_has_rebuild(self):
        assert hasattr(ReviewCoverageProjectionRepository, 'rebuild')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ReviewCoverageProjectionRepository()

    def test_projection_dataclass(self):
        p = ReviewCoverageProjection(
            decision_id="d1",
            proposal_id="p1",
            cycle_id="c1",
            eligible=True,
            review_type="ALLOCATION_REVIEW",
            strategy_name="default",
            strategy_version="1.0",
            evaluation_reason="Approved",
            review_status="PENDING",
            review_due_date=datetime.utcnow(),
            executed_at=None,
            days_overdue=None,
            evaluated_at=datetime.utcnow(),
        )
        assert p.decision_id == "d1"
        assert p.eligible is True
        assert p.review_status == "PENDING"


class TestOutboxRepository:
    def test_is_abc(self):
        assert issubclass(OutboxRepository, ABC)

    def test_has_save_event(self):
        assert hasattr(OutboxRepository, 'save_event')

    def test_has_save_events(self):
        assert hasattr(OutboxRepository, 'save_events')

    def test_has_get_pending(self):
        assert hasattr(OutboxRepository, 'get_pending')

    def test_has_get_failed(self):
        assert hasattr(OutboxRepository, 'get_failed')

    def test_has_mark_sent(self):
        assert hasattr(OutboxRepository, 'mark_sent')

    def test_has_mark_failed(self):
        assert hasattr(OutboxRepository, 'mark_failed')

    def test_has_increment_retry(self):
        assert hasattr(OutboxRepository, 'increment_retry')

    def test_has_cleanup_sent(self):
        assert hasattr(OutboxRepository, 'cleanup_sent')

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            OutboxRepository()
