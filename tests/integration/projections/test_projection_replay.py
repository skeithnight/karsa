"""Tests for projection replay — Sprint-06 Wave-6."""
import pytest
from datetime import datetime
from typing import Optional, List

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository
from karsa.allocation.application.service.proposal_status_projection_service import ProposalStatusProjectionService
from karsa.allocation.application.service.proposal_projection_rebuilder import ProposalProjectionRebuilder


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


def _make_events():
    """Creates a sample event stream for testing."""
    return [
        {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 1,
         "payload": {"proposal_id": "p1", "event_sequence": 1}},
        {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 2,
         "payload": {"proposal_id": "p2", "event_sequence": 2}},
        {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 3,
         "payload": {"proposal_id": "p3", "event_sequence": 3}},
        {"event_type": "AllocationProposalApprovedEvent", "global_sequence": 4,
         "payload": {"proposal_id": "p1", "decision_id": "d1", "approved_by": "cio",
                     "approved_at": "2026-06-20T12:00:00", "event_sequence": 4}},
        {"event_type": "AllocationProposalRejectedEvent", "global_sequence": 5,
         "payload": {"proposal_id": "p2", "decision_id": "d2", "rejected_by": "cio",
                     "rejected_at": "2026-06-20T12:00:00", "event_sequence": 5}},
        {"event_type": "AllocationProposalExpiredEvent", "global_sequence": 6,
         "payload": {"proposal_id": "p3", "expired_at": "2026-06-20T12:00:00", "event_sequence": 6}},
        # Non-proposal event (should be ignored)
        {"event_type": "OrderFilledEvent", "global_sequence": 7,
         "payload": {"order_id": "o1"}},
    ]


class TestFullReplayRebuild:
    def test_rebuild_processes_proposal_events(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        events = _make_events()
        processed = rebuilder.rebuild(events)

        assert processed == 6  # 3 generated + 1 approved + 1 rejected + 1 expired
        assert len(repo.list_all()) == 3

    def test_rebuild_produces_correct_states(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        rebuilder.rebuild(_make_events())

        assert repo.get_status("p1").status == "APPROVED"
        assert repo.get_status("p2").status == "REJECTED"
        assert repo.get_status("p3").status == "EXPIRED"

    def test_rebuild_ignores_non_proposal_events(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        events = [
            {"event_type": "OrderFilledEvent", "global_sequence": 1, "payload": {}},
            {"event_type": "ThesisProposedEvent", "global_sequence": 2, "payload": {}},
        ]
        processed = rebuilder.rebuild(events)

        assert processed == 0
        assert len(repo.list_all()) == 0


class TestReplayDeterminism:
    def test_replay_produces_identical_state(self):
        events = _make_events()

        # First replay
        repo1 = InMemoryProjectionRepo()
        service1 = ProposalStatusProjectionService(repo1)
        rebuilder1 = ProposalProjectionRebuilder(repo1, service1)
        rebuilder1.rebuild(events)

        # Second replay
        repo2 = InMemoryProjectionRepo()
        service2 = ProposalStatusProjectionService(repo2)
        rebuilder2 = ProposalProjectionRebuilder(repo2, service2)
        rebuilder2.rebuild(events)

        # Compare
        state1 = {p.proposal_id: (p.status, p.decision_id, p.event_sequence) for p in repo1.list_all()}
        state2 = {p.proposal_id: (p.status, p.decision_id, p.event_sequence) for p in repo2.list_all()}

        assert state1 == state2

    def test_partial_replay_produces_same_result(self):
        """Replaying from checkpoint produces same final state."""
        events = _make_events()

        # Full replay
        repo1 = InMemoryProjectionRepo()
        service1 = ProposalStatusProjectionService(repo1)
        rebuilder1 = ProposalProjectionRebuilder(repo1, service1)
        rebuilder1.rebuild(events)

        # Partial replay (from sequence 3)
        repo2 = InMemoryProjectionRepo()
        service2 = ProposalStatusProjectionService(repo2)
        rebuilder2 = ProposalProjectionRebuilder(repo2, service2)
        # Pre-populate with events up to sequence 3
        for e in events[:3]:
            service2.handle_event(e["event_type"], e["payload"])
        # Replay remaining
        rebuilder2.rebuild(events[3:])

        state1 = {p.proposal_id: (p.status, p.decision_id) for p in repo1.list_all()}
        state2 = {p.proposal_id: (p.status, p.decision_id) for p in repo2.list_all()}

        assert state1 == state2


class TestProjectionReset:
    def test_reset_clears_projections(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        rebuilder.rebuild(_make_events())
        assert len(repo.list_all()) == 3

        rebuilder.reset_projection()
        assert len(repo.list_all()) == 0

    def test_reset_then_rebuild_restores_state(self):
        events = _make_events()

        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        # Build
        rebuilder.rebuild(events)
        state_before = {p.proposal_id: p.status for p in repo.list_all()}

        # Reset
        rebuilder.reset_projection()
        assert len(repo.list_all()) == 0

        # Rebuild
        rebuilder.rebuild(events)
        state_after = {p.proposal_id: p.status for p in repo.list_all()}

        assert state_before == state_after


class TestMixedProposalStates:
    def test_multiple_proposals_different_states(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        events = [
            {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 1,
             "payload": {"proposal_id": "p1", "event_sequence": 1}},
            {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 2,
             "payload": {"proposal_id": "p2", "event_sequence": 2}},
            {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 3,
             "payload": {"proposal_id": "p3", "event_sequence": 3}},
            {"event_type": "AllocationProposalGeneratedEvent", "global_sequence": 4,
             "payload": {"proposal_id": "p4", "event_sequence": 4}},
            {"event_type": "AllocationProposalApprovedEvent", "global_sequence": 5,
             "payload": {"proposal_id": "p1", "decision_id": "d1", "approved_by": "cio",
                         "approved_at": "2026-06-20T12:00:00", "event_sequence": 5}},
            {"event_type": "AllocationProposalRejectedEvent", "global_sequence": 6,
             "payload": {"proposal_id": "p2", "decision_id": "d2", "rejected_by": "cio",
                         "rejected_at": "2026-06-20T12:00:00", "event_sequence": 6}},
            {"event_type": "AllocationProposalModifiedEvent", "global_sequence": 7,
             "payload": {"original_proposal_id": "p3", "decision_id": "d3", "modified_by": "cio",
                         "modified_at": "2026-06-20T12:00:00", "event_sequence": 7}},
        ]

        rebuilder.rebuild(events)

        assert repo.get_status("p1").status == "APPROVED"
        assert repo.get_status("p2").status == "REJECTED"
        assert repo.get_status("p3").status == "MODIFIED"
        assert repo.get_status("p4").status == "PENDING"

        dist = rebuilder.get_status_distribution()
        assert dist == {"APPROVED": 1, "REJECTED": 1, "MODIFIED": 1, "PENDING": 1}

    def test_verify_rebuild_passes(self):
        repo = InMemoryProjectionRepo()
        service = ProposalStatusProjectionService(repo)
        rebuilder = ProposalProjectionRebuilder(repo, service)

        rebuilder.rebuild(_make_events())
        assert rebuilder.verify_rebuild() is True
