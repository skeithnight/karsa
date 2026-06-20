"""Tests for ProposalStatusProjectionService — Sprint-06 Wave-6."""
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


class TestGeneratedEvent:
    def test_creates_pending_state(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.upsert_pending({
            "proposal_id": "p1",
            "event_sequence": 1,
        })

        result = repo.get_status("p1")
        assert result is not None
        assert result.status == "PENDING"
        assert result.event_sequence == 1

    def test_empty_proposal_id_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.upsert_pending({"proposal_id": "", "event_sequence": 1})
        assert len(repo.list_all()) == 0

    def test_missing_proposal_id_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.upsert_pending({"event_sequence": 1})
        assert len(repo.list_all()) == 0


class TestApprovedEvent:
    def test_creates_approved_state(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_approved({
            "proposal_id": "p1",
            "decision_id": "dec-1",
            "approved_by": "cio-1",
            "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        result = repo.get_status("p1")
        assert result.status == "APPROVED"
        assert result.decision_id == "dec-1"
        assert result.decided_by == "cio-1"

    def test_empty_proposal_id_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.mark_approved({
            "proposal_id": "",
            "decision_id": "dec-1",
            "approved_by": "cio-1",
            "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        assert len(repo.list_all()) == 0

    def test_empty_decision_id_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_approved({
            "proposal_id": "p1",
            "decision_id": "",
            "approved_by": "cio-1",
            "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })
        assert repo.get_status("p1").status == "PENDING"


class TestRejectedEvent:
    def test_creates_rejected_state(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_rejected({
            "proposal_id": "p1",
            "decision_id": "dec-1",
            "rejected_by": "cio-1",
            "rejected_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        result = repo.get_status("p1")
        assert result.status == "REJECTED"
        assert result.decision_id == "dec-1"


class TestModifiedEvent:
    def test_creates_modified_state(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_modified({
            "original_proposal_id": "p1",
            "decision_id": "dec-1",
            "modified_by": "cio-1",
            "modified_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        result = repo.get_status("p1")
        assert result.status == "MODIFIED"
        assert result.decision_id == "dec-1"

    def test_uses_original_proposal_id(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_modified({
            "original_proposal_id": "p1",
            "decision_id": "dec-1",
            "modified_by": "cio-1",
            "modified_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        result = repo.get_status("p1")
        assert result is not None


class TestExpiredEvent:
    def test_creates_expired_state(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.mark_expired({
            "proposal_id": "p1",
            "expired_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        result = repo.get_status("p1")
        assert result.status == "EXPIRED"


class TestHandleEvent:
    def test_dispatches_generated(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.handle_event("AllocationProposalGeneratedEvent", {
            "proposal_id": "p1", "event_sequence": 1,
        })

        assert repo.get_status("p1").status == "PENDING"

    def test_dispatches_approved(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.handle_event("AllocationProposalApprovedEvent", {
            "proposal_id": "p1", "decision_id": "d1",
            "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        assert repo.get_status("p1").status == "APPROVED"

    def test_dispatches_rejected(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.handle_event("AllocationProposalRejectedEvent", {
            "proposal_id": "p1", "decision_id": "d1",
            "rejected_by": "cio", "rejected_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        assert repo.get_status("p1").status == "REJECTED"

    def test_dispatches_modified(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.handle_event("AllocationProposalModifiedEvent", {
            "original_proposal_id": "p1", "decision_id": "d1",
            "modified_by": "cio", "modified_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        assert repo.get_status("p1").status == "MODIFIED"

    def test_dispatches_expired(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        repo.upsert_pending("p1", event_sequence=1)
        service.handle_event("AllocationProposalExpiredEvent", {
            "proposal_id": "p1", "expired_at": "2026-06-20T12:00:00",
            "event_sequence": 10,
        })

        assert repo.get_status("p1").status == "EXPIRED"

    def test_unknown_event_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        service.handle_event("UnknownEvent", {"proposal_id": "p1"})
        assert len(repo.list_all()) == 0
