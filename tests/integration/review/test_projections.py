"""Projection tests — Sprint-07 Wave-2C."""
import pytest
from datetime import datetime
from typing import Optional, List, Dict

from karsa.review.domain.repositories.capability_score_projection_repository import (
    CapabilityScoreProjectionRepository, CapabilityScoreProjection,
)
from karsa.review.domain.repositories.review_coverage_projection_repository import (
    ReviewCoverageProjectionRepository, ReviewCoverageProjection,
)
from karsa.review.domain.repositories.review_cycle_status_projection_repository import (
    ReviewCycleStatusProjectionRepository, ReviewCycleStatusProjection,
)


# --- In-memory implementations ---

class InMemoryCapabilityScoreProjectionRepository(CapabilityScoreProjectionRepository):
    def __init__(self):
        self._store: Dict[str, CapabilityScoreProjection] = {}

    def get_by_target_urn(self, target_urn: str) -> Optional[CapabilityScoreProjection]:
        return self._store.get(target_urn)

    def list_all(self) -> List[CapabilityScoreProjection]:
        return sorted(self._store.values(), key=lambda p: p.current_score, reverse=True)

    def upsert(self, target_urn: str, target_type: str, score_delta: float,
               confidence_delta: float, adjustment_count_delta: int = 1) -> None:
        if target_urn in self._store:
            existing = self._store[target_urn]
            self._store[target_urn] = CapabilityScoreProjection(
                target_urn=target_urn,
                target_type=target_type,
                current_score=existing.current_score + score_delta,
                current_confidence=existing.current_confidence + confidence_delta,
                adjustment_count=existing.adjustment_count + adjustment_count_delta,
                last_updated=datetime.utcnow(),
            )
        else:
            self._store[target_urn] = CapabilityScoreProjection(
                target_urn=target_urn,
                target_type=target_type,
                current_score=score_delta,
                current_confidence=confidence_delta,
                adjustment_count=adjustment_count_delta,
                last_updated=datetime.utcnow(),
            )

    def rebuild(self) -> None:
        self._store.clear()


class InMemoryReviewCoverageProjectionRepository(ReviewCoverageProjectionRepository):
    def __init__(self):
        self._store: Dict[str, ReviewCoverageProjection] = {}

    def get_by_decision_id(self, decision_id: str) -> Optional[ReviewCoverageProjection]:
        return self._store.get(decision_id)

    def list_by_status(self, status: str) -> List[ReviewCoverageProjection]:
        return [p for p in self._store.values() if p.review_status == status]

    def list_overdue(self) -> List[ReviewCoverageProjection]:
        return [p for p in self._store.values() if p.review_status == 'OVERDUE']

    def upsert_from_eligibility(self, decision_id: str, eligible: bool, review_type: Optional[str],
                                 strategy_name: str, strategy_version: str,
                                 evaluation_reason: str, evaluated_at: datetime) -> None:
        self._store[decision_id] = ReviewCoverageProjection(
            decision_id=decision_id, proposal_id=None, cycle_id=None,
            eligible=eligible, review_type=review_type,
            strategy_name=strategy_name, strategy_version=strategy_version,
            evaluation_reason=evaluation_reason,
            review_status='NO_REVIEW' if not eligible else 'PENDING',
            review_due_date=None, executed_at=None, days_overdue=None,
            evaluated_at=evaluated_at,
        )

    def update_status(self, decision_id: str, review_status: str, cycle_id: Optional[str] = None,
                      review_due_date: Optional[datetime] = None, executed_at: Optional[datetime] = None,
                      days_overdue: Optional[int] = None) -> None:
        if decision_id in self._store:
            existing = self._store[decision_id]
            self._store[decision_id] = ReviewCoverageProjection(
                decision_id=existing.decision_id,
                proposal_id=existing.proposal_id,
                cycle_id=cycle_id or existing.cycle_id,
                eligible=existing.eligible,
                review_type=existing.review_type,
                strategy_name=existing.strategy_name,
                strategy_version=existing.strategy_version,
                evaluation_reason=existing.evaluation_reason,
                review_status=review_status,
                review_due_date=review_due_date or existing.review_due_date,
                executed_at=executed_at or existing.executed_at,
                days_overdue=days_overdue or existing.days_overdue,
                evaluated_at=existing.evaluated_at,
            )

    def rebuild(self) -> None:
        self._store.clear()


class InMemoryReviewCycleStatusProjectionRepository(ReviewCycleStatusProjectionRepository):
    def __init__(self):
        self._store: Dict[str, ReviewCycleStatusProjection] = {}

    def get_by_cycle_id(self, cycle_id: str) -> Optional[ReviewCycleStatusProjection]:
        return self._store.get(cycle_id)

    def list_by_status(self, status: str) -> List[ReviewCycleStatusProjection]:
        return [p for p in self._store.values() if p.status == status]

    def upsert_created(self, cycle_id: str, event_sequence: int) -> None:
        if cycle_id not in self._store:
            self._store[cycle_id] = ReviewCycleStatusProjection(
                cycle_id=cycle_id, status='CREATED', event_sequence=event_sequence,
            )

    def upsert_due(self, cycle_id: str, event_sequence: int) -> None:
        if cycle_id in self._store and self._store[cycle_id].event_sequence < event_sequence:
            existing = self._store[cycle_id]
            self._store[cycle_id] = ReviewCycleStatusProjection(
                cycle_id=cycle_id, status='DUE', review_id=existing.review_id,
                executed_at=existing.executed_at, event_sequence=event_sequence,
            )

    def upsert_overdue(self, cycle_id: str, event_sequence: int) -> None:
        if cycle_id in self._store and self._store[cycle_id].event_sequence < event_sequence:
            existing = self._store[cycle_id]
            self._store[cycle_id] = ReviewCycleStatusProjection(
                cycle_id=cycle_id, status='OVERDUE', review_id=existing.review_id,
                executed_at=existing.executed_at, event_sequence=event_sequence,
            )

    def upsert_executed(self, cycle_id: str, review_id: str, executed_at: datetime, event_sequence: int) -> None:
        if cycle_id in self._store and self._store[cycle_id].event_sequence < event_sequence:
            self._store[cycle_id] = ReviewCycleStatusProjection(
                cycle_id=cycle_id, status='EXECUTED', review_id=review_id,
                executed_at=executed_at, event_sequence=event_sequence,
            )

    def rebuild(self) -> None:
        self._store.clear()


# --- Tests ---

class TestCapabilityScoreProjection:
    def test_insert(self):
        repo = InMemoryCapabilityScoreProjectionRepository()
        repo.upsert("w1", "WORKER", 0.05, 0.01)
        p = repo.get_by_target_urn("w1")
        assert p is not None
        assert p.current_score == 0.05
        assert p.adjustment_count == 1

    def test_update(self):
        repo = InMemoryCapabilityScoreProjectionRepository()
        repo.upsert("w1", "WORKER", 0.05, 0.01)
        repo.upsert("w1", "WORKER", 0.03, 0.02)
        p = repo.get_by_target_urn("w1")
        assert p.current_score == 0.08
        assert p.current_confidence == 0.03
        assert p.adjustment_count == 2

    def test_list_all(self):
        repo = InMemoryCapabilityScoreProjectionRepository()
        repo.upsert("w1", "WORKER", 0.05, 0.01)
        repo.upsert("w2", "WORKER", 0.10, 0.02)
        all_p = repo.list_all()
        assert len(all_p) == 2
        assert all_p[0].current_score >= all_p[1].current_score

    def test_rebuild(self):
        repo = InMemoryCapabilityScoreProjectionRepository()
        repo.upsert("w1", "WORKER", 0.05, 0.01)
        repo.rebuild()
        assert repo.get_by_target_urn("w1") is None


class TestReviewCoverageProjection:
    def test_eligible_insert(self):
        repo = InMemoryReviewCoverageProjectionRepository()
        repo.upsert_from_eligibility("d1", True, "ALLOCATION_REVIEW", "default", "1.0", "Approved", datetime.utcnow())
        p = repo.get_by_decision_id("d1")
        assert p is not None
        assert p.eligible is True
        assert p.review_status == 'PENDING'

    def test_ineligible_insert(self):
        repo = InMemoryReviewCoverageProjectionRepository()
        repo.upsert_from_eligibility("d2", False, None, "default", "1.0", "Below threshold", datetime.utcnow())
        p = repo.get_by_decision_id("d2")
        assert p.eligible is False
        assert p.review_status == 'NO_REVIEW'

    def test_update_status(self):
        repo = InMemoryReviewCoverageProjectionRepository()
        repo.upsert_from_eligibility("d1", True, "ALLOCATION_REVIEW", "default", "1.0", "Approved", datetime.utcnow())
        repo.update_status("d1", "EXECUTED", cycle_id="c1", executed_at=datetime.utcnow())
        p = repo.get_by_decision_id("d1")
        assert p.review_status == 'EXECUTED'
        assert p.cycle_id == 'c1'

    def test_list_by_status(self):
        repo = InMemoryReviewCoverageProjectionRepository()
        repo.upsert_from_eligibility("d1", True, "ALLOCATION_REVIEW", "default", "1.0", "Approved", datetime.utcnow())
        repo.upsert_from_eligibility("d2", False, None, "default", "1.0", "Below threshold", datetime.utcnow())
        assert len(repo.list_by_status('PENDING')) == 1
        assert len(repo.list_by_status('NO_REVIEW')) == 1

    def test_list_overdue(self):
        repo = InMemoryReviewCoverageProjectionRepository()
        repo.upsert_from_eligibility("d1", True, "ALLOCATION_REVIEW", "default", "1.0", "Approved", datetime.utcnow())
        repo.update_status("d1", "OVERDUE", days_overdue=5)
        assert len(repo.list_overdue()) == 1


class TestReviewCycleStatusProjection:
    def test_created(self):
        repo = InMemoryReviewCycleStatusProjectionRepository()
        repo.upsert_created("c1", 1)
        p = repo.get_by_cycle_id("c1")
        assert p.status == 'CREATED'

    def test_due(self):
        repo = InMemoryReviewCycleStatusProjectionRepository()
        repo.upsert_created("c1", 1)
        repo.upsert_due("c1", 10)
        assert repo.get_by_cycle_id("c1").status == 'DUE'

    def test_overdue(self):
        repo = InMemoryReviewCycleStatusProjectionRepository()
        repo.upsert_created("c1", 1)
        repo.upsert_overdue("c1", 20)
        assert repo.get_by_cycle_id("c1").status == 'OVERDUE'

    def test_executed(self):
        repo = InMemoryReviewCycleStatusProjectionRepository()
        repo.upsert_created("c1", 1)
        repo.upsert_executed("c1", "r1", datetime.utcnow(), 30)
        p = repo.get_by_cycle_id("c1")
        assert p.status == 'EXECUTED'
        assert p.review_id == 'r1'

    def test_out_of_order_ignored(self):
        repo = InMemoryReviewCycleStatusProjectionRepository()
        repo.upsert_created("c1", 10)
        repo.upsert_due("c1", 5)  # lower sequence — should be ignored
        assert repo.get_by_cycle_id("c1").status == 'CREATED'

    def test_list_by_status(self):
        repo = InMemoryReviewCycleStatusProjectionRepository()
        repo.upsert_created("c1", 1)
        repo.upsert_created("c2", 2)
        repo.upsert_due("c1", 10)
        assert len(repo.list_by_status('CREATED')) == 1
        assert len(repo.list_by_status('DUE')) == 1
