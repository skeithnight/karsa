"""Tests for ProposalStatusProjectionRepository — Sprint-06 Wave-3.

Uses in-memory implementation for testing.
Validates event_sequence guard, idempotency, and replay determinism.
"""
import pytest
from datetime import datetime
from typing import Optional, List

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository


class InMemoryProposalStatusProjectionRepository(ProposalStatusProjectionRepository):
    """In-memory implementation for testing."""
    def __init__(self):
        self._projections = {}  # proposal_id -> ProposalStatusProjection

    def get_status(self, proposal_id: str) -> Optional[ProposalStatusProjection]:
        return self._projections.get(proposal_id)

    def list_by_status(self, status: str, limit: int = 50, offset: int = 0) -> List[ProposalStatusProjection]:
        filtered = [p for p in self._projections.values() if p.status == status]
        filtered.sort(key=lambda p: p.decided_at or datetime.min, reverse=True)
        return filtered[offset:offset + limit]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ProposalStatusProjection]:
        all_projections = sorted(self._projections.values(), key=lambda p: p.proposal_id)
        return all_projections[offset:offset + limit]

    def upsert_pending(self, proposal_id: str, event_sequence: int) -> None:
        if proposal_id not in self._projections:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id,
                status="PENDING",
                event_sequence=event_sequence,
            )

    def mark_approved(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id,
                status="APPROVED",
                decision_id=decision_id,
                decided_by=decided_by,
                decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )

    def mark_rejected(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id,
                status="REJECTED",
                decision_id=decision_id,
                decided_by=decided_by,
                decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )

    def mark_modified(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id,
                status="MODIFIED",
                decision_id=decision_id,
                decided_by=decided_by,
                decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )

    def mark_expired(self, proposal_id: str, decided_at: str, event_sequence: int) -> None:
        proj = self._projections.get(proposal_id)
        if proj and proj.event_sequence < event_sequence:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id,
                status="EXPIRED",
                decided_at=datetime.fromisoformat(decided_at),
                event_sequence=event_sequence,
            )


class TestProposalStatusProjectionRepository:
    def test_upsert_pending(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)

        result = repo.get_status("p1")
        assert result is not None
        assert result.status == "PENDING"
        assert result.event_sequence == 1

    def test_mark_approved(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=5)

        result = repo.get_status("p1")
        assert result.status == "APPROVED"
        assert result.decision_id == "dec-1"
        assert result.decided_by == "cio-1"
        assert result.event_sequence == 5

    def test_mark_rejected(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_rejected("p1", "dec-2", "cio-1", "2026-06-20T12:00:00", event_sequence=5)

        result = repo.get_status("p1")
        assert result.status == "REJECTED"
        assert result.decision_id == "dec-2"

    def test_mark_modified(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_modified("p1", "dec-3", "cio-1", "2026-06-20T12:00:00", event_sequence=5)

        result = repo.get_status("p1")
        assert result.status == "MODIFIED"
        assert result.decision_id == "dec-3"

    def test_mark_expired(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_expired("p1", "2026-06-20T12:00:00", event_sequence=5)

        result = repo.get_status("p1")
        assert result.status == "EXPIRED"

    def test_duplicate_pending_ignored(self):
        """ON CONFLICT DO NOTHING: duplicate creation events are idempotent."""
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.upsert_pending("p1", event_sequence=99)  # duplicate, should be ignored

        result = repo.get_status("p1")
        assert result.event_sequence == 1  # original preserved

    def test_out_of_order_event_ignored(self):
        """event_sequence guard: out-of-order events are ignored."""
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=10)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=5)

        result = repo.get_status("p1")
        assert result.status == "PENDING"  # not changed, sequence 5 < 10

    def test_event_sequence_guard(self):
        """Higher sequence wins, lower sequence ignored."""
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        # Try to reject with lower sequence — should be ignored
        repo.mark_rejected("p1", "dec-2", "cio-1", "2026-06-20T12:00:00", event_sequence=5)

        result = repo.get_status("p1")
        assert result.status == "APPROVED"  # not overridden

    def test_replay_determinism(self):
        """Replaying the same events produces identical state."""
        repo1 = InMemoryProposalStatusProjectionRepository()
        repo1.upsert_pending("p1", event_sequence=1)
        repo1.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        repo2 = InMemoryProposalStatusProjectionRepository()
        repo2.upsert_pending("p1", event_sequence=1)
        repo2.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        assert repo1.get_status("p1") == repo2.get_status("p1")

    def test_list_by_status(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.upsert_pending("p2", event_sequence=2)
        repo.mark_approved("p1", "dec-1", "cio-1", "2026-06-20T12:00:00", event_sequence=10)

        pending = repo.list_by_status("PENDING")
        assert len(pending) == 1
        assert pending[0].proposal_id == "p2"

        approved = repo.list_by_status("APPROVED")
        assert len(approved) == 1
        assert approved[0].proposal_id == "p1"

    def test_list_all(self):
        repo = InMemoryProposalStatusProjectionRepository()
        repo.upsert_pending("p1", event_sequence=1)
        repo.upsert_pending("p2", event_sequence=2)
        repo.upsert_pending("p3", event_sequence=3)

        all_projections = repo.list_all()
        assert len(all_projections) == 3

    def test_get_nonexistent_returns_none(self):
        repo = InMemoryProposalStatusProjectionRepository()
        assert repo.get_status("nonexistent") is None


class TestProposalStatusProjectionModel:
    def test_valid_projection(self):
        proj = ProposalStatusProjection(proposal_id="p1", status="PENDING")
        assert proj.status == "PENDING"
        assert proj.decision_id is None

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status must be one of"):
            ProposalStatusProjection(proposal_id="p1", status="INVALID")

    def test_empty_proposal_id_raises(self):
        with pytest.raises(ValueError, match="proposal_id cannot be empty"):
            ProposalStatusProjection(proposal_id="", status="PENDING")

    def test_frozen_immutability(self):
        proj = ProposalStatusProjection(proposal_id="p1", status="PENDING")
        with pytest.raises(AttributeError):
            proj.status = "APPROVED"
