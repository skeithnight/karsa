"""Application service tests — Sprint-07 Wave-3."""
import pytest
from datetime import datetime
from typing import Optional, List, Dict

from karsa.review.domain.aggregates.review_cycle import ReviewCycle
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
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis
from karsa.review.domain.repositories.review_cycle_repository import ReviewCycleRepository
from karsa.review.domain.repositories.review_record_repository import ReviewRecordRepository
from karsa.review.domain.repositories.attribution_entry_repository import AttributionEntryRepository
from karsa.review.domain.repositories.capability_score_adjustment_repository import CapabilityScoreAdjustmentRepository
from karsa.review.domain.repositories.capability_score_projection_repository import CapabilityScoreProjectionRepository, CapabilityScoreProjection
from karsa.review.domain.repositories.review_coverage_projection_repository import ReviewCoverageProjectionRepository, ReviewCoverageProjection
from karsa.review.domain.repositories.review_cycle_status_projection_repository import ReviewCycleStatusProjectionRepository, ReviewCycleStatusProjection
from karsa.review.domain.repositories.outbox_repository import OutboxRepository
from karsa.review.application.dto import (
    ScheduleReviewCommand, ExecuteReviewCommand, ApplyCapabilityAdjustmentCommand,
    RebuildProjectionCommand, PublishOutboxCommand,
)
from karsa.review.application.schedule_review_service import ScheduleReviewService
from karsa.review.application.execute_review_service import ExecuteReviewService
from karsa.review.application.apply_capability_adjustment_service import ApplyCapabilityAdjustmentService
from karsa.review.application.rebuild_projection_service import RebuildProjectionService
from karsa.review.application.publish_outbox_service import PublishOutboxService


# --- In-memory repositories ---

class InMemoryReviewCycleRepository(ReviewCycleRepository):
    def __init__(self):
        self._store: Dict[str, ReviewCycle] = {}

    def save_cycle(self, cycle: ReviewCycle) -> bool:
        # Check for duplicate decision_id (simulates ON CONFLICT DO NOTHING)
        for existing in self._store.values():
            if existing.decision_id == cycle.decision_id:
                return False  # Already exists — not inserted
        self._store[cycle.cycle_id] = cycle
        return True  # Inserted

    def get_cycle_by_id(self, cycle_id: str) -> Optional[ReviewCycle]:
        return self._store.get(cycle_id)

    def get_cycle_by_decision_id(self, decision_id: str) -> Optional[ReviewCycle]:
        for c in self._store.values():
            if c.decision_id == decision_id:
                return c
        return None

    def get_cycle_by_eligibility_ref(self, eligibility_event_ref: str) -> Optional[ReviewCycle]:
        for c in self._store.values():
            if c.eligibility_event_ref == eligibility_event_ref:
                return c
        return None

    def list_cycles(self, page: int = 1, size: int = 50) -> List[ReviewCycle]:
        items = sorted(self._store.values(), key=lambda c: c.created_at, reverse=True)
        offset = (page - 1) * size
        return items[offset:offset + size]


class InMemoryReviewRecordRepository(ReviewRecordRepository):
    def __init__(self):
        self._store: Dict[str, ReviewRecord] = {}

    def save_record(self, record: ReviewRecord) -> None:
        if record.review_id in self._store:
            raise ValueError(f"Duplicate review_id: {record.review_id}")
        self._store[record.review_id] = record

    def get_record_by_id(self, review_id: str) -> Optional[ReviewRecord]:
        return self._store.get(review_id)

    def get_records_by_cycle_id(self, cycle_id: str) -> List[ReviewRecord]:
        return sorted(
            [r for r in self._store.values() if r.cycle_id == cycle_id],
            key=lambda r: r.executed_at,
        )

    def list_records(self, page: int = 1, size: int = 50) -> List[ReviewRecord]:
        items = sorted(self._store.values(), key=lambda r: r.executed_at, reverse=True)
        offset = (page - 1) * size
        return items[offset:offset + size]


class InMemoryAttributionEntryRepository(AttributionEntryRepository):
    def __init__(self):
        self._store: Dict[str, AttributionEntry] = {}

    def save_entry(self, entry: AttributionEntry) -> None:
        if entry.attribution_id in self._store:
            raise ValueError(f"Duplicate attribution_id: {entry.attribution_id}")
        self._store[entry.attribution_id] = entry

    def save_entries(self, entries: List[AttributionEntry]) -> None:
        for e in entries:
            self.save_entry(e)

    def get_entries_by_review_id(self, review_id: str) -> List[AttributionEntry]:
        return sorted(
            [e for e in self._store.values() if e.review_id == review_id],
            key=lambda e: e.created_at,
        )

    def get_entries_by_target_urn(self, target_urn: str) -> List[AttributionEntry]:
        return sorted(
            [e for e in self._store.values() if e.target_urn == target_urn],
            key=lambda e: e.created_at, reverse=True,
        )

    def get_entries_by_dimension(self, review_id: str, dimension: AttributionDimension) -> List[AttributionEntry]:
        return [
            e for e in self._store.values()
            if e.review_id == review_id and e.dimension == dimension
        ]


class InMemoryCapabilityScoreAdjustmentRepository(CapabilityScoreAdjustmentRepository):
    def __init__(self):
        self._store: Dict[str, CapabilityScoreAdjustment] = {}

    def save_adjustment(self, adjustment: CapabilityScoreAdjustment) -> None:
        if adjustment.adjustment_id in self._store:
            raise ValueError(f"Duplicate adjustment_id: {adjustment.adjustment_id}")
        self._store[adjustment.adjustment_id] = adjustment

    def save_adjustments(self, adjustments: List[CapabilityScoreAdjustment]) -> None:
        for a in adjustments:
            self.save_adjustment(a)

    def get_adjustments_by_review_id(self, review_id: str) -> List[CapabilityScoreAdjustment]:
        return sorted(
            [a for a in self._store.values() if a.review_id == review_id],
            key=lambda a: a.created_at,
        )

    def get_adjustments_by_target_urn(self, target_urn: str) -> List[CapabilityScoreAdjustment]:
        return sorted(
            [a for a in self._store.values() if a.target_urn == target_urn],
            key=lambda a: a.created_at,
        )


class InMemoryOutboxRepository(OutboxRepository):
    def __init__(self):
        self._store: Dict[str, OutboxEvent] = {}

    def save_event(self, event: OutboxEvent) -> None:
        self._store[event.outbox_id] = event

    def save_events(self, events: List[OutboxEvent]) -> None:
        for e in events:
            self.save_event(e)

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        pending = [e for e in self._store.values() if e.is_pending]
        pending.sort(key=lambda e: e.created_at or datetime.min)
        return pending[:limit]

    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        failed = [e for e in self._store.values() if e.is_failed]
        failed.sort(key=lambda e: e.created_at or datetime.min)
        return failed[:limit]

    def mark_sent(self, outbox_id: str, sent_at: datetime) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].mark_sent(sent_at)

    def mark_failed(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].mark_failed()

    def increment_retry(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id].increment_retry()

    def cleanup_sent(self, before: datetime) -> int:
        to_delete = [
            oid for oid, e in self._store.items()
            if e.is_sent and e.sent_at and e.sent_at < before
        ]
        for oid in to_delete:
            del self._store[oid]
        return len(to_delete)


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
                target_urn=target_urn, target_type=target_type,
                current_score=existing.current_score + score_delta,
                current_confidence=existing.current_confidence + confidence_delta,
                adjustment_count=existing.adjustment_count + adjustment_count_delta,
                last_updated=datetime.utcnow(),
            )
        else:
            self._store[target_urn] = CapabilityScoreProjection(
                target_urn=target_urn, target_type=target_type,
                current_score=score_delta, current_confidence=confidence_delta,
                adjustment_count=adjustment_count_delta, last_updated=datetime.utcnow(),
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
                      review_due_date=None, executed_at=None, days_overdue=None) -> None:
        if decision_id in self._store:
            existing = self._store[decision_id]
            self._store[decision_id] = ReviewCoverageProjection(
                decision_id=existing.decision_id, proposal_id=existing.proposal_id,
                cycle_id=cycle_id or existing.cycle_id, eligible=existing.eligible,
                review_type=existing.review_type, strategy_name=existing.strategy_name,
                strategy_version=existing.strategy_version, evaluation_reason=existing.evaluation_reason,
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


# --- Fixtures ---

def _make_snapshot_dict():
    return {
        "action_type": "APPROVE_ALLOCATION",
        "target_node_type": "WORKER",
        "target_node_id": "portfolio-main",
        "allocated_weights": {"w1": 0.6, "w2": 0.4},
        "policy_snapshot": {"policy_id": "p1"},
        "expected_return_bps": 50.0,
        "expected_drawdown_pct": 5.0,
        "expected_sharpe_ratio": 1.5,
        "expected_horizon_days": 30,
        "confidence_level": 0.7,
        "decision_rationale": "Test",
        "decision_confidence": 0.7,
        "decision_timestamp": "2026-06-20T00:00:00Z",
        "cryptographic_signature": "sig",
        "snapshot_hash": "hash",
    }


def _make_schedule_command():
    return ScheduleReviewCommand(
        decision_id="dec-1",
        proposal_id="prop-1",
        journal_ref="journal-1",
        review_type="ALLOCATION_REVIEW",
        decision_snapshot=_make_snapshot_dict(),
        schedule_policy={"observation_window_days": 30, "overdue_threshold_days": 7},
        review_template={"template_id": "tmpl-1", "required_metrics": ["return_bps"]},
        eligibility_event_ref="elig-1",
        created_by="test-user",
    )


def _make_execute_command(cycle_id="cycle-1"):
    return ExecuteReviewCommand(
        cycle_id=cycle_id,
        actual_outcome={
            "evaluation_id": "eval-1",
            "target_urn": "w1",
            "observation_window_days": 30,
            "realized_return_bps": 60.0,
            "realized_drawdown_pct": 3.0,
            "realized_sharpe_ratio": 1.8,
            "benchmark_return_bps": 40.0,
            "actual_attribution": {"w1": 30.0, "w2": 20.0},
        },
        executed_by="test-user",
        rationale="Exceeded expectations.",
    )


# --- Tests ---

class TestScheduleReviewService:
    def _make_service(self):
        cycle_repo = InMemoryReviewCycleRepository()
        outbox_repo = InMemoryOutboxRepository()
        coverage_repo = InMemoryReviewCoverageProjectionRepository()
        status_repo = InMemoryReviewCycleStatusProjectionRepository()
        service = ScheduleReviewService(cycle_repo, outbox_repo, coverage_repo, status_repo)
        return service, cycle_repo, outbox_repo, coverage_repo, status_repo

    def test_happy_path(self):
        service, cycle_repo, outbox_repo, coverage_repo, status_repo = self._make_service()
        cmd = _make_schedule_command()
        resp = service.execute(cmd)

        assert resp.decision_id == "dec-1"
        assert resp.review_type == "ALLOCATION_REVIEW"
        assert cycle_repo.get_cycle_by_decision_id("dec-1") is not None
        assert len(outbox_repo.get_pending()) == 1

    def test_idempotency(self):
        service, cycle_repo, outbox_repo, _, _ = self._make_service()
        cmd = _make_schedule_command()
        resp1 = service.execute(cmd)
        resp2 = service.execute(cmd)

        assert resp1.cycle_id == resp2.cycle_id
        assert len(outbox_repo.get_pending()) == 1  # Only one event

    def test_validation_failure_empty_decision_id(self):
        service, _, _, _, _ = self._make_service()
        cmd = ScheduleReviewCommand(
            decision_id="", proposal_id=None, journal_ref="j1",
            review_type="ALLOCATION_REVIEW", decision_snapshot={},
            schedule_policy={}, review_template={},
            eligibility_event_ref="e1", created_by="user",
        )
        with pytest.raises(ValueError, match="decision_id is required"):
            service.execute(cmd)


class TestExecuteReviewService:
    def _make_service(self):
        cycle_repo = InMemoryReviewCycleRepository()
        record_repo = InMemoryReviewRecordRepository()
        attribution_repo = InMemoryAttributionEntryRepository()
        adjustment_repo = InMemoryCapabilityScoreAdjustmentRepository()
        outbox_repo = InMemoryOutboxRepository()
        coverage_repo = InMemoryReviewCoverageProjectionRepository()
        status_repo = InMemoryReviewCycleStatusProjectionRepository()

        # Create a test cycle
        from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot, StructuredAssumption
        from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
        from karsa.review.domain.value_objects.review_template import ReviewTemplate

        snapshot = DecisionSnapshot(
            decision_id="dec-1", proposal_id="p1", journal_ref="j1",
            action_type="APPROVE", target_node_type="WORKER", target_node_id="main",
            allocated_weights={"w1": 0.6}, policy_snapshot={},
            expected_return_bps=50.0, expected_drawdown_pct=5.0,
            expected_sharpe_ratio=1.5, expected_horizon_days=30,
            confidence_level=0.7, benchmark_urn=None, regime_at_decision=None,
            key_assumptions=[], attribution_expectations={},
            decision_rationale="Test", decision_confidence=0.7,
            decision_timestamp="2026-06-20T00:00:00Z",
            cryptographic_signature="sig", snapshot_hash="hash",
        )
        schedule = SchedulePolicy.create(30, 7, datetime(2026, 6, 20))
        template = ReviewTemplate.default_allocation_review()

        cycle = ReviewCycle(
            cycle_id="cycle-1", decision_id="dec-1", proposal_id="p1",
            journal_ref="j1", review_type=ReviewType.ALLOCATION_REVIEW,
            decision_snapshot=snapshot, schedule_policy=schedule,
            review_template=template, eligibility_event_ref="elig-1",
            created_at=datetime.utcnow(), created_by="test",
        )
        cycle_repo.save_cycle(cycle)

        service = ExecuteReviewService(
            cycle_repo, record_repo, attribution_repo, adjustment_repo,
            outbox_repo, coverage_repo, status_repo,
        )
        return service, record_repo, attribution_repo, adjustment_repo, outbox_repo

    def test_happy_path(self):
        service, record_repo, attribution_repo, adjustment_repo, outbox_repo = self._make_service()
        cmd = _make_execute_command("cycle-1")
        resp = service.execute(cmd)

        assert resp.cycle_id == "cycle-1"
        assert resp.verdict in [v.value for v in ReviewVerdict]
        assert resp.attribution_count == 2  # w1 and w2
        assert resp.adjustment_count == 2  # one per attribution
        assert len(record_repo._store) == 1
        assert len(attribution_repo._store) == 2
        assert len(adjustment_repo._store) == 2
        assert len(outbox_repo._store) == 5  # 1 review + 2 attributions + 2 adjustments

    def test_cycle_not_found(self):
        service, _, _, _, _ = self._make_service()
        cmd = _make_execute_command("nonexistent")
        with pytest.raises(ValueError, match="not found"):
            service.execute(cmd)

    def test_empty_attribution(self):
        service, record_repo, attribution_repo, adjustment_repo, outbox_repo = self._make_service()
        cmd = ExecuteReviewCommand(
            cycle_id="cycle-1",
            actual_outcome={
                "evaluation_id": "eval-1",
                "target_urn": "w1",
                "observation_window_days": 30,
                "realized_return_bps": 60.0,
                "realized_drawdown_pct": 3.0,
                "realized_sharpe_ratio": 1.8,
                "benchmark_return_bps": 40.0,
                "actual_attribution": {},
            },
            executed_by="test-user",
            rationale="No attribution.",
        )
        resp = service.execute(cmd)

        assert resp.attribution_count == 0
        assert resp.adjustment_count == 0
        assert len(outbox_repo._store) == 1  # Only review event


class TestApplyCapabilityAdjustmentService:
    def _make_service(self):
        adjustment_repo = InMemoryCapabilityScoreAdjustmentRepository()
        projection_repo = InMemoryCapabilityScoreProjectionRepository()
        outbox_repo = InMemoryOutboxRepository()
        service = ApplyCapabilityAdjustmentService(adjustment_repo, projection_repo, outbox_repo)
        return service, adjustment_repo, projection_repo, outbox_repo

    def test_happy_path(self):
        service, adjustment_repo, projection_repo, outbox_repo = self._make_service()
        cmd = ApplyCapabilityAdjustmentCommand(
            review_id="r1", target_urn="w1", target_type="WORKER",
            contribution_bps=50.0,
        )
        resp = service.execute(cmd)

        assert resp.target_urn == "w1"
        assert resp.score_delta > 0
        assert len(adjustment_repo._store) == 1
        assert projection_repo.get_by_target_urn("w1") is not None
        assert len(outbox_repo._store) == 1

    def test_validation_failure(self):
        service, _, _, _ = self._make_service()
        cmd = ApplyCapabilityAdjustmentCommand(
            review_id="", target_urn="w1", target_type="WORKER",
            contribution_bps=50.0,
        )
        with pytest.raises(ValueError, match="review_id is required"):
            service.execute(cmd)


class TestRebuildProjectionService:
    def _make_service(self):
        capability_repo = InMemoryCapabilityScoreProjectionRepository()
        coverage_repo = InMemoryReviewCoverageProjectionRepository()
        status_repo = InMemoryReviewCycleStatusProjectionRepository()
        service = RebuildProjectionService(capability_repo, coverage_repo, status_repo)
        return service, capability_repo

    def test_rebuild_capability_score(self):
        service, capability_repo = self._make_service()
        capability_repo.upsert("w1", "WORKER", 0.05, 0.01)
        capability_repo.upsert("w2", "WORKER", 0.03, 0.02)

        cmd = RebuildProjectionCommand(projection_name="capability_score")
        resp = service.execute(cmd)

        assert resp.projection_name == "capability_score"
        assert resp.rows_affected == 0  # Rebuild cleared

    def test_invalid_projection_name(self):
        service, _ = self._make_service()
        cmd = RebuildProjectionCommand(projection_name="invalid")
        with pytest.raises(ValueError, match="Unknown projection"):
            service.execute(cmd)


class TestPublishOutboxService:
    def _make_service(self):
        outbox_repo = InMemoryOutboxRepository()
        published = []
        def publisher(payload):
            published.append(payload)
        service = PublishOutboxService(outbox_repo, publisher)
        return service, outbox_repo, published

    def test_happy_path(self):
        service, outbox_repo, published = self._make_service()
        outbox_repo.save_event(OutboxEvent(
            outbox_id="o1", event_type="TestEvent",
            payload={"key": "value"}, aggregate_id="a1",
            created_at=datetime.utcnow(),
        ))

        cmd = PublishOutboxCommand(batch_size=10, max_retries=3)
        resp = service.execute(cmd)

        assert resp.published_count == 1
        assert resp.failed_count == 0
        assert len(published) == 1

    def test_failed_publish_retries(self):
        service, outbox_repo, published = self._make_service()
        outbox_repo.save_event(OutboxEvent(
            outbox_id="o1", event_type="TestEvent",
            payload={"key": "value"}, aggregate_id="a1",
            created_at=datetime.utcnow(),
        ))

        # Override publisher to fail
        def failing_publisher(payload):
            raise Exception("Publish failed")
        service.event_publisher = failing_publisher

        # First attempt: retry_count=0, max_retries=3 → increment retry
        cmd = PublishOutboxCommand(batch_size=10, max_retries=3)
        resp = service.execute(cmd)
        assert resp.published_count == 0
        assert resp.failed_count == 0  # Not failed yet, just retried
        assert outbox_repo._store["o1"].retry_count == 1

    def test_failed_publish_max_retries_exceeded(self):
        service, outbox_repo, published = self._make_service()
        event = OutboxEvent(
            outbox_id="o1", event_type="TestEvent",
            payload={"key": "value"}, aggregate_id="a1",
            created_at=datetime.utcnow(),
        )
        # Simulate already retried 2 times
        event.increment_retry()
        event.increment_retry()
        outbox_repo.save_event(event)

        # Override publisher to fail
        def failing_publisher(payload):
            raise Exception("Publish failed")
        service.event_publisher = failing_publisher

        # retry_count=2, max_retries=2 → mark as failed
        cmd = PublishOutboxCommand(batch_size=10, max_retries=2)
        resp = service.execute(cmd)
        assert resp.published_count == 0
        assert resp.failed_count == 1

    def test_empty_outbox(self):
        service, _, published = self._make_service()
        cmd = PublishOutboxCommand(batch_size=10, max_retries=3)
        resp = service.execute(cmd)

        assert resp.published_count == 0
        assert resp.failed_count == 0
