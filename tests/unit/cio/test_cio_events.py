"""Tests for Sprint-06 CIO events — Wave-2."""
import pytest
from datetime import datetime

from karsa.cio.events import (
    AllocationProposalApprovedEvent,
    AllocationProposalRejectedEvent,
    AllocationProposalModifiedEvent,
)
from karsa.allocation.domain.events import (
    AllocationProposalGeneratedEvent,
    AllocationProposalExpiredEvent,
)


class TestAllocationProposalGeneratedEvent:
    def test_valid_event(self):
        event = AllocationProposalGeneratedEvent(
            event_id="evt-1",
            proposal_id="urn:karsa:proposal:test-1",
            policy_id="policy-1",
            journal_ref="urn:karsa:journal:test-1",
            proposed_weights={"w1": {"weight": 0.5}},
            total_capital=100000.0,
            proposal_rationale="Test rationale",
            context_hash="hash123",
            generated_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalGeneratedEvent"
        assert event.event_version == 1

    def test_empty_proposal_id_raises(self):
        with pytest.raises(ValueError, match="proposal_id cannot be empty"):
            AllocationProposalGeneratedEvent(
                event_id="evt-1",
                proposal_id="",
                policy_id="p1",
                journal_ref="j1",
                proposed_weights={},
                total_capital=0,
                proposal_rationale="r",
                context_hash="h",
                generated_at=datetime.utcnow(),
            )

    def test_empty_journal_ref_raises(self):
        with pytest.raises(ValueError, match="journal_ref cannot be empty"):
            AllocationProposalGeneratedEvent(
                event_id="evt-1",
                proposal_id="p1",
                policy_id="p1",
                journal_ref="",
                proposed_weights={},
                total_capital=0,
                proposal_rationale="r",
                context_hash="h",
                generated_at=datetime.utcnow(),
            )

    def test_to_dict_roundtrip(self):
        now = datetime.utcnow()
        event = AllocationProposalGeneratedEvent(
            event_id="evt-1",
            proposal_id="urn:karsa:proposal:test-1",
            policy_id="policy-1",
            journal_ref="urn:karsa:journal:test-1",
            proposed_weights={"w1": {"weight": 0.5}},
            total_capital=100000.0,
            proposal_rationale="Test rationale",
            context_hash="hash123",
            generated_at=now,
            event_sequence=42,
        )
        d = event.to_dict()
        assert d["proposal_id"] == "urn:karsa:proposal:test-1"
        assert d["event_sequence"] == 42
        assert d["total_capital"] == 100000.0

    def test_frozen_immutability(self):
        event = AllocationProposalGeneratedEvent(
            event_id="evt-1",
            proposal_id="p1",
            policy_id="p1",
            journal_ref="j1",
            proposed_weights={},
            total_capital=0,
            proposal_rationale="r",
            context_hash="h",
            generated_at=datetime.utcnow(),
        )
        with pytest.raises(AttributeError):
            event.proposal_id = "changed"


class TestAllocationProposalApprovedEvent:
    def test_valid_event(self):
        event = AllocationProposalApprovedEvent(
            event_id="evt-2",
            proposal_id="urn:karsa:proposal:test-1",
            decision_id="dec-1",
            approved_by="cio-1",
            approved_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalApprovedEvent"
        assert event.event_version == 1

    def test_empty_proposal_id_raises(self):
        with pytest.raises(ValueError, match="proposal_id cannot be empty"):
            AllocationProposalApprovedEvent(
                event_id="evt-2",
                proposal_id="",
                decision_id="dec-1",
                approved_by="cio-1",
                approved_at=datetime.utcnow(),
            )

    def test_empty_decision_id_raises(self):
        with pytest.raises(ValueError, match="decision_id cannot be empty"):
            AllocationProposalApprovedEvent(
                event_id="evt-2",
                proposal_id="p1",
                decision_id="",
                approved_by="cio-1",
                approved_at=datetime.utcnow(),
            )


class TestAllocationProposalRejectedEvent:
    def test_valid_event(self):
        event = AllocationProposalRejectedEvent(
            event_id="evt-3",
            proposal_id="urn:karsa:proposal:test-1",
            decision_id="dec-2",
            rejected_by="cio-1",
            rejection_reason="Insufficient conviction",
            rejected_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalRejectedEvent"
        assert event.rejection_reason == "Insufficient conviction"

    def test_empty_proposal_id_raises(self):
        with pytest.raises(ValueError, match="proposal_id cannot be empty"):
            AllocationProposalRejectedEvent(
                event_id="evt-3",
                proposal_id="",
                decision_id="dec-2",
                rejected_by="cio-1",
                rejection_reason="reason",
                rejected_at=datetime.utcnow(),
            )


class TestAllocationProposalModifiedEvent:
    def test_valid_event(self):
        event = AllocationProposalModifiedEvent(
            event_id="evt-4",
            original_proposal_id="urn:karsa:proposal:test-1",
            decision_id="dec-3",
            modified_weights={"w1": 0.5, "w2": 0.5},
            modification_reason="Adjust for risk",
            modified_by="cio-1",
            modified_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalModifiedEvent"
        assert event.modified_weights == {"w1": 0.5, "w2": 0.5}

    def test_empty_original_proposal_id_raises(self):
        with pytest.raises(ValueError, match="original_proposal_id cannot be empty"):
            AllocationProposalModifiedEvent(
                event_id="evt-4",
                original_proposal_id="",
                decision_id="dec-3",
                modified_weights={},
                modification_reason="r",
                modified_by="cio-1",
                modified_at=datetime.utcnow(),
            )

    def test_empty_decision_id_raises(self):
        with pytest.raises(ValueError, match="decision_id cannot be empty"):
            AllocationProposalModifiedEvent(
                event_id="evt-4",
                original_proposal_id="p1",
                decision_id="",
                modified_weights={},
                modification_reason="r",
                modified_by="cio-1",
                modified_at=datetime.utcnow(),
            )


class TestAllocationProposalExpiredEvent:
    def test_valid_event(self):
        event = AllocationProposalExpiredEvent(
            event_id="evt-5",
            proposal_id="urn:karsa:proposal:test-1",
            expired_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalExpiredEvent"
        assert event.event_version == 1

    def test_empty_proposal_id_raises(self):
        with pytest.raises(ValueError, match="proposal_id cannot be empty"):
            AllocationProposalExpiredEvent(
                event_id="evt-5",
                proposal_id="",
                expired_at=datetime.utcnow(),
            )

    def test_to_dict(self):
        now = datetime.utcnow()
        event = AllocationProposalExpiredEvent(
            event_id="evt-5",
            proposal_id="p1",
            expired_at=now,
            event_sequence=99,
        )
        d = event.to_dict()
        assert d["proposal_id"] == "p1"
        assert d["event_sequence"] == 99
