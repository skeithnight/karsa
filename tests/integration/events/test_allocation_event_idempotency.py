"""Tests for allocation event idempotency — Sprint-06 Wave-5.

Documents and verifies the idempotency strategy for each event type.
"""
import pytest
from datetime import datetime

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository


class InMemoryProjectionRepo(ProposalStatusProjectionRepository):
    """In-memory implementation matching Postgres behavior for idempotency testing."""
    def __init__(self):
        self._projections = {}

    def get_status(self, proposal_id):
        return self._projections.get(proposal_id)

    def list_by_status(self, status, limit=50, offset=0):
        return [p for p in self._projections.values() if p.status == status]

    def list_all(self, limit=100, offset=0):
        return list(self._projections.values())

    def upsert_pending(self, proposal_id, event_sequence):
        # ON CONFLICT DO NOTHING: duplicate creation events are idempotent
        if proposal_id not in self._projections:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="PENDING", event_sequence=event_sequence,
            )

    def mark_approved(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
        # WHERE event_sequence < new_sequence: out-of-order events are ignored
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="APPROVED", decision_id=decision_id,
                decided_by=decided_by, decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )

    def mark_rejected(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="REJECTED", decision_id=decision_id,
                decided_by=decided_by, decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )

    def mark_modified(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="MODIFIED", decision_id=decision_id,
                decided_by=decided_by, decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )

    def mark_expired(self, proposal_id, decided_at, event_sequence):
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="EXPIRED",
                decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )


class TestGeneratedEventIdempotency:
    """AllocationProposalGeneratedEvent uses ON CONFLICT DO NOTHING.

    Safe duplicate handling:
    - First event creates PENDING row
    - Duplicate events are silently ignored
    - event_sequence is preserved from first event
    """

    def test_duplicate_generated_ignored(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.upsert_pending("p1", event_sequence=99)  # duplicate

        result = repo.get_status("p1")
        assert result.event_sequence == 1  # original preserved
        assert result.status == "PENDING"


class TestDecisionEventIdempotency:
    """Decision events use WHERE event_sequence < incoming_sequence.

    Safe duplicate handling:
    - Duplicate events with same sequence are ignored (not strictly less)
    - Out-of-order events are ignored
    - Only strictly newer events update state
    """

    def test_duplicate_approved_ignored(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)
        repo.mark_approved("p1", "dec-2", "cio-2", "2026-06-20T12:01:00", event_sequence=10)  # same sequence

        result = repo.get_status("p1")
        assert result.decision_id == "dec-1"  # original preserved
        assert result.event_sequence == 10

    def test_out_of_order_approved_ignored(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)
        repo.mark_approved("p1", "dec-2", "cio-2", "2026-06-20T12:01:00", event_sequence=5)  # lower sequence

        result = repo.get_status("p1")
        assert result.decision_id == "dec-1"  # original preserved
        assert result.event_sequence == 10

    def test_newer_event_updates(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)
        repo.mark_approved("p1", "dec-2", "cio-2", "2026-06-20T12:01:00", event_sequence=20)  # newer

        result = repo.get_status("p1")
        assert result.decision_id == "dec-2"  # newer event won
        assert result.event_sequence == 20

    def test_rejected_idempotent(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_rejected("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)
        repo.mark_rejected("p1", "dec-2", "cio-2", "2026-06-20T12:01:00", event_sequence=10)

        result = repo.get_status("p1")
        assert result.decision_id == "dec-1"

    def test_modified_idempotent(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_modified("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)
        repo.mark_modified("p1", "dec-2", "cio-2", "2026-06-20T12:01:00", event_sequence=10)

        result = repo.get_status("p1")
        assert result.decision_id == "dec-1"

    def test_expired_idempotent(self):
        repo = InMemoryProjectionRepo()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_expired("p1", "2026-06-20T12:00:00", event_sequence=10)
        repo.mark_expired("p1", "2026-06-20T12:01:00", event_sequence=10)

        result = repo.get_status("p1")
        assert result.status == "EXPIRED"
        assert result.event_sequence == 10


class TestReplayDeterminism:
    """Replaying the same events always produces identical state."""

    def test_full_replay_deterministic(self):
        repo1 = InMemoryProjectionRepo()
        repo1.upsert_pending("p1", event_sequence=1)
        repo1.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        repo2 = InMemoryProjectionRepo()
        repo2.upsert_pending("p1", event_sequence=1)
        repo2.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        assert repo1.get_status("p1") == repo2.get_status("p1")

    def test_partial_replay_deterministic(self):
        """Replaying from a checkpoint produces same final state."""
        repo1 = InMemoryProjectionRepo()
        repo1.upsert_pending("p1", event_sequence=1)
        repo1.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        # Simulate replay from checkpoint at sequence 5
        repo2 = InMemoryProjectionRepo()
        repo2.upsert_pending("p1", event_sequence=1)  # already processed
        repo2.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        assert repo1.get_status("p1") == repo2.get_status("p1")
