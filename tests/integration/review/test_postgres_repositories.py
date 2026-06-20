"""Repository integration tests — Sprint-07 Wave-2C.

Uses in-memory implementations to verify repository contracts.
Postgres-specific tests require a running database.
"""
import pytest
from datetime import datetime
from typing import Optional, List, Dict

from karsa.review.domain.aggregates.review_cycle import ReviewCycle
from karsa.review.domain.aggregates.review_record import ReviewRecord
from karsa.review.domain.aggregates.attribution_entry import AttributionEntry
from karsa.review.domain.aggregates.capability_score_adjustment import CapabilityScoreAdjustment
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


# --- In-memory implementations ---

class InMemoryReviewCycleRepository(ReviewCycleRepository):
    def __init__(self):
        self._store: Dict[str, ReviewCycle] = {}

    def save_cycle(self, cycle: ReviewCycle) -> None:
        if cycle.cycle_id in self._store:
            raise ValueError(f"Duplicate cycle_id: {cycle.cycle_id}")
        self._store[cycle.cycle_id] = cycle

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


# --- Fixtures ---

def _make_snapshot():
    return DecisionSnapshot(
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


def _make_cycle(**overrides):
    defaults = dict(
        cycle_id="c1", decision_id="dec-1", proposal_id="p1", journal_ref="j1",
        review_type=ReviewType.ALLOCATION_REVIEW, decision_snapshot=_make_snapshot(),
        schedule_policy=SchedulePolicy.create(30, 7, datetime(2026, 6, 20)),
        review_template=ReviewTemplate.default_allocation_review(),
        eligibility_event_ref="elig-1", created_at=datetime.utcnow(), created_by="system",
    )
    defaults.update(overrides)
    return ReviewCycle(**defaults)


def _make_record(**overrides):
    defaults = dict(
        review_id="r1", cycle_id="c1",
        review_type=ReviewType.ALLOCATION_REVIEW, decision_snapshot=_make_snapshot(),
        actual_outcome=ActualOutcomeSnapshot(
            evaluation_id="e1", target_urn="w1", observation_window_days=30,
            realized_return_bps=60.0, realized_drawdown_pct=3.0,
            realized_sharpe_ratio=1.8, benchmark_return_bps=40.0,
            regime_during_period="BULL",
        ),
        variance=VarianceAnalysis.compute(50.0, 5.0, 1.5, 60.0, 3.0, 1.8, 0.7, []),
        verdict=ReviewVerdict.OUTPERFORMED, rationale="Exceeded.",
        executed_at=datetime.utcnow(), executed_by="cio",
    )
    defaults.update(overrides)
    return ReviewRecord(**defaults)


# --- Tests ---

class TestReviewCycleRepository:
    def test_save_and_get(self):
        repo = InMemoryReviewCycleRepository()
        cycle = _make_cycle()
        repo.save_cycle(cycle)
        assert repo.get_cycle_by_id("c1") == cycle

    def test_get_by_decision_id(self):
        repo = InMemoryReviewCycleRepository()
        repo.save_cycle(_make_cycle())
        assert repo.get_cycle_by_decision_id("dec-1") is not None

    def test_get_by_eligibility_ref(self):
        repo = InMemoryReviewCycleRepository()
        repo.save_cycle(_make_cycle())
        assert repo.get_cycle_by_eligibility_ref("elig-1") is not None

    def test_list_pagination(self):
        repo = InMemoryReviewCycleRepository()
        for i in range(5):
            repo.save_cycle(_make_cycle(cycle_id=f"c{i}"))
        assert len(repo.list_cycles(page=1, size=2)) == 2
        assert len(repo.list_cycles(page=3, size=2)) == 1

    def test_duplicate_raises(self):
        repo = InMemoryReviewCycleRepository()
        repo.save_cycle(_make_cycle())
        with pytest.raises(ValueError):
            repo.save_cycle(_make_cycle())


class TestReviewRecordRepository:
    def test_save_and_get(self):
        repo = InMemoryReviewRecordRepository()
        record = _make_record()
        repo.save_record(record)
        assert repo.get_record_by_id("r1") == record

    def test_get_by_cycle_id(self):
        repo = InMemoryReviewRecordRepository()
        repo.save_record(_make_record())
        repo.save_record(_make_record(review_id="r2", cycle_id="c1"))
        repo.save_record(_make_record(review_id="r3", cycle_id="c2"))
        assert len(repo.get_records_by_cycle_id("c1")) == 2

    def test_list_pagination(self):
        repo = InMemoryReviewRecordRepository()
        for i in range(5):
            repo.save_record(_make_record(review_id=f"r{i}"))
        assert len(repo.list_records(page=1, size=2)) == 2

    def test_duplicate_raises(self):
        repo = InMemoryReviewRecordRepository()
        repo.save_record(_make_record())
        with pytest.raises(ValueError):
            repo.save_record(_make_record())


class TestAttributionEntryRepository:
    def test_save_and_get_by_review(self):
        repo = InMemoryAttributionEntryRepository()
        entry = AttributionEntry.from_contribution(
            "a1", "r1", AttributionDimension.WORKER, "w1",
            30.0, 60.0, {}, datetime.utcnow(),
        )
        repo.save_entry(entry)
        assert len(repo.get_entries_by_review_id("r1")) == 1

    def test_batch_save(self):
        repo = InMemoryAttributionEntryRepository()
        entries = [
            AttributionEntry.from_contribution(
                f"a{i}", "r1", AttributionDimension.WORKER, f"w{i}",
                10.0, 60.0, {}, datetime.utcnow(),
            )
            for i in range(4)
        ]
        repo.save_entries(entries)
        assert len(repo.get_entries_by_review_id("r1")) == 4

    def test_get_by_target_urn(self):
        repo = InMemoryAttributionEntryRepository()
        repo.save_entry(AttributionEntry.from_contribution(
            "a1", "r1", AttributionDimension.WORKER, "w1", 30.0, 60.0, {}, datetime.utcnow(),
        ))
        repo.save_entry(AttributionEntry.from_contribution(
            "a2", "r2", AttributionDimension.WORKER, "w1", 20.0, 40.0, {}, datetime.utcnow(),
        ))
        assert len(repo.get_entries_by_target_urn("w1")) == 2

    def test_get_by_dimension(self):
        repo = InMemoryAttributionEntryRepository()
        repo.save_entry(AttributionEntry.from_contribution(
            "a1", "r1", AttributionDimension.WORKER, "w1", 30.0, 60.0, {}, datetime.utcnow(),
        ))
        repo.save_entry(AttributionEntry.from_contribution(
            "a2", "r1", AttributionDimension.CIO, "cio-1", 10.0, 60.0, {}, datetime.utcnow(),
        ))
        assert len(repo.get_entries_by_dimension("r1", AttributionDimension.WORKER)) == 1
        assert len(repo.get_entries_by_dimension("r1", AttributionDimension.CIO)) == 1


class TestCapabilityScoreAdjustmentRepository:
    def test_save_and_get(self):
        repo = InMemoryCapabilityScoreAdjustmentRepository()
        adj = CapabilityScoreAdjustment.from_attribution(
            "adj1", "w1", "WORKER", 50.0, "r1", datetime.utcnow(),
        )
        repo.save_adjustment(adj)
        assert len(repo.get_adjustments_by_review_id("r1")) == 1

    def test_batch_save(self):
        repo = InMemoryCapabilityScoreAdjustmentRepository()
        adjs = [
            CapabilityScoreAdjustment.from_attribution(
                f"adj{i}", f"w{i}", "WORKER", 10.0, "r1", datetime.utcnow(),
            )
            for i in range(3)
        ]
        repo.save_adjustments(adjs)
        assert len(repo.get_adjustments_by_review_id("r1")) == 3

    def test_get_by_target_urn(self):
        repo = InMemoryCapabilityScoreAdjustmentRepository()
        repo.save_adjustment(CapabilityScoreAdjustment.from_attribution(
            "adj1", "w1", "WORKER", 50.0, "r1", datetime.utcnow(),
        ))
        repo.save_adjustment(CapabilityScoreAdjustment.from_attribution(
            "adj2", "w1", "WORKER", 30.0, "r2", datetime.utcnow(),
        ))
        assert len(repo.get_adjustments_by_target_urn("w1")) == 2

    def test_duplicate_raises(self):
        repo = InMemoryCapabilityScoreAdjustmentRepository()
        adj = CapabilityScoreAdjustment.from_attribution(
            "adj1", "w1", "WORKER", 50.0, "r1", datetime.utcnow(),
        )
        repo.save_adjustment(adj)
        with pytest.raises(ValueError):
            repo.save_adjustment(adj)
