"""Tests for projection worker integration — Sprint-06 Wave-6.

Verifies that the ProposalStatusProjectionService correctly handles
events as they would be dispatched by the projection worker.
"""
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


def _simulate_worker_dispatch(service, events):
    """Simulates how the projection worker dispatches events."""
    for event in events:
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})
        service.handle_event(event_type, payload)


class TestWorkerDispatchGenerated:
    def test_dispatch_creates_pending(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
        ])

        assert repo.get_status("p1").status == "PENDING"


class TestWorkerDispatchApproved:
    def test_dispatch_updates_to_approved(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalApprovedEvent",
             "payload": {"proposal_id": "p1", "decision_id": "d1",
                         "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
                         "event_sequence": 10}},
        ])

        result = repo.get_status("p1")
        assert result.status == "APPROVED"
        assert result.decision_id == "d1"


class TestWorkerDispatchRejected:
    def test_dispatch_updates_to_rejected(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalRejectedEvent",
             "payload": {"proposal_id": "p1", "decision_id": "d1",
                         "rejected_by": "cio", "rejected_at": "2026-06-20T12:00:00",
                         "event_sequence": 10}},
        ])

        result = repo.get_status("p1")
        assert result.status == "REJECTED"
        assert result.decision_id == "d1"


class TestWorkerDispatchModified:
    def test_dispatch_updates_to_modified(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalModifiedEvent",
             "payload": {"original_proposal_id": "p1", "decision_id": "d1",
                         "modified_by": "cio", "modified_at": "2026-06-20T12:00:00",
                         "event_sequence": 10}},
        ])

        result = repo.get_status("p1")
        assert result.status == "MODIFIED"
        assert result.decision_id == "d1"


class TestWorkerDispatchExpired:
    def test_dispatch_updates_to_expired(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalExpiredEvent",
             "payload": {"proposal_id": "p1", "expired_at": "2026-06-20T12:00:00",
                         "event_sequence": 10}},
        ])

        result = repo.get_status("p1")
        assert result.status == "EXPIRED"


class TestWorkerDispatchMixed:
    def test_multiple_proposals_different_lifecycles(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p2", "event_sequence": 2}},
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p3", "event_sequence": 3}},
            {"event_type": "AllocationProposalApprovedEvent",
             "payload": {"proposal_id": "p1", "decision_id": "d1",
                         "approved_by": "cio", "approved_at": "2026-06-20T12:00:00",
                         "event_sequence": 10}},
            {"event_type": "AllocationProposalRejectedEvent",
             "payload": {"proposal_id": "p2", "decision_id": "d2",
                         "rejected_by": "cio", "rejected_at": "2026-06-20T12:00:00",
                         "event_sequence": 11}},
            # p3 stays PENDING
        ])

        assert repo.get_status("p1").status == "APPROVED"
        assert repo.get_status("p2").status == "REJECTED"
        assert repo.get_status("p3").status == "PENDING"

    def test_non_proposal_events_ignored(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            {"event_type": "OrderFilledEvent", "payload": {"order_id": "o1"}},
            {"event_type": "ThesisProposedEvent", "payload": {"thesis_id": "t1"}},
            {"event_type": "PortfolioDecisionMadeEvent", "payload": {"decision_id": "d1"}},
        ])

        assert len(repo.list_all()) == 0


class TestWorkerDispatchFullLifecycle:
    def test_complete_lifecycle(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)

        _simulate_worker_dispatch(service, [
            # Generate
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            # Approve
            {"event_type": "AllocationProposalApprovedEvent",
             "payload": {"proposal_id": "p1", "decision_id": "d1",
                         "approved_by": "cio-1", "approved_at": "2026-06-20T12:05:00",
                         "event_sequence": 10}},
            # Replay (should be idempotent)
            {"event_type": "AllocationProposalGeneratedEvent",
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalApprovedEvent",
             "payload": {"proposal_id": "p1", "decision_id": "d1",
                         "approved_by": "cio-1", "approved_at": "2026-06-20T12:05:00",
                         "event_sequence": 10}},
        ])

        result = repo.get_status("p1")
        assert result.status == "APPROVED"
        assert result.decision_id == "d1"
        assert result.event_sequence == 10
        assert len(repo.list_all()) == 1  # no duplicates
