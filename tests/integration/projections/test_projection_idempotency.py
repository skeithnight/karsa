"""Tests for projection idempotency — Sprint-06 Wave-6."""
import pytest
from datetime import datetime
from typing import Optional, List

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository
from karsa.allocation.application.service.proposal_status_projection_service import ProposalStatusProjectionService


class InMemoryProjectionRepo(ProposalStatusProjectionRepository):
    def __init__(self):
        self._projections = {}

    def get_status(self, proposal_id):
        return self._projections.get(proposal_id)

    def list_by_status(self, status, limit=50, offset=0):
        return [p for p in self._projections.values() if p.status == status]

    def list_all(self, limit=100, offset=0):
        return list(self._projections.values())

    def upsert_pending(self, proposal_id, event_sequence):
        if proposal_id not in self._projections:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="PENDING", event_sequence=event_sequence,
            )

    def mark_approved(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
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


class TestDuplicateGeneratedEvent:
    def test_duplicate_does_not_create_second_row(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.upsert_pending({"proposal_id": "p1", "event_sequence": 1})
        service.upsert_pending({"proposal_id": "p1", "event_sequence": 1})  # duplicate

        assert len(repo.list_all()) == 1
        assert repo.get_status("p1").event_sequence == 1

    def test_duplicate_with_different_sequence_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.upsert_pending({"proposal_id": "p1", "event_sequence": 1})
        service.upsert_pending({"proposal_id": "p1", "event_sequence": 99})  # different sequence

        assert len(repo.list_all()) == 1
        assert repo.get_status("p1").event_sequence == 1  # original preserved


class TestDuplicateApprovedEvent:
    def test_duplicate_does_not_change_state(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d1",
            "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d2",
            "approved_by": "cio2", "approved_at": "2026-06-20T12:01:00",
            "event_sequence": 10,  # same sequence
        })

        result = repo.get_status("p1")
        assert result.decision_id == "d1"  # original preserved
        assert result.event_sequence == 10


class TestOutOfOrderApprovedEvent:
    def test_lower_sequence_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d1",
            "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d2",
            "approved_by": "cio2", "approved_at": "2026-06-20T12:01:00",
            "event_sequence": 5,  # lower sequence
        })

        result = repo.get_status("p1")
        assert result.decision_id == "d1"  # original preserved
        assert result.status == "APPROVED"

    def test_higher_sequence_updates(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d1",
            "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d2",
            "approved_by": "cio2", "approved_at": "2026-06-20T12:01:00",
            "event_sequence": 20,  # higher sequence
        })

        result = repo.get_status("p1")
        assert result.decision_id == "d2"  # newer wins


class TestOutOfOrderRejectedEvent:
    def test_lower_sequence_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_rejected({
            "proposal_id": "p1", "decision_id": "d1",
            "rejected_by": "cio", "rejected_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        service.mark_rejected({
            "proposal_id": "p1", "decision_id": "d2",
            "rejected_by": "cio2", "rejected_at": "2026-06-20T12:01:00",
            "event_sequence": 5,
        })

        result = repo.get_status("p1")
        assert result.decision_id == "d1"


class TestNoDuplicateProposalIds:
    def test_no_duplicate_rows_after_full_lifecycle(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        # Process events for same proposal multiple times
        service.upsert_pending({"proposal_id": "p1", "event_sequence": 1})
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d1",
            "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        # Replay
        service.upsert_pending({"proposal_id": "p1", "event_sequence": 1})
        service.mark_approved({
            "proposal_id": "p1", "decision_id": "d1",
            "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        # Verify no duplicates
        all_projections = repo.list_all()
        proposal_ids = [p.proposal_id for p in all_projections]
        assert len(proposal_ids) == len(set(proposal_ids))
