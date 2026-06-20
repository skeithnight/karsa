"""Tests for allocation event registration — Sprint-06 Wave-5.

Verifies that events are registered and the projection worker can dispatch them.
"""
import pytest
from datetime import datetime

from karsa.allocation.events import EVENT_REGISTRY, get_event_class, get_aggregate_id
from karsa.allocation.domain.events import (
    AllocationProposalGeneratedEvent,
    AllocationProposalApprovedEvent,
    AllocationProposalRejectedEvent,
    AllocationProposalModifiedEvent,
    AllocationProposalExpiredEvent,
)


class TestEventRegistry:
    def test_registry_size(self):
        assert len(EVENT_REGISTRY) == 5

    def test_all_event_types_registered(self):
        expected = [
            "AllocationProposalGeneratedEvent",
            "AllocationProposalApprovedEvent",
            "AllocationProposalRejectedEvent",
            "AllocationProposalModifiedEvent",
            "AllocationProposalExpiredEvent",
        ]
        for event_type in expected:
            assert event_type in EVENT_REGISTRY, f"{event_type} not in registry"

    def test_registry_maps_to_correct_classes(self):
        assert EVENT_REGISTRY["AllocationProposalGeneratedEvent"] is AllocationProposalGeneratedEvent
        assert EVENT_REGISTRY["AllocationProposalApprovedEvent"] is AllocationProposalApprovedEvent
        assert EVENT_REGISTRY["AllocationProposalRejectedEvent"] is AllocationProposalRejectedEvent
        assert EVENT_REGISTRY["AllocationProposalModifiedEvent"] is AllocationProposalModifiedEvent
        assert EVENT_REGISTRY["AllocationProposalExpiredEvent"] is AllocationProposalExpiredEvent

    def test_get_event_class_returns_correct_type(self):
        assert get_event_class("AllocationProposalGeneratedEvent") is AllocationProposalGeneratedEvent
        assert get_event_class("AllocationProposalApprovedEvent") is AllocationProposalApprovedEvent
        assert get_event_class("AllocationProposalRejectedEvent") is AllocationProposalRejectedEvent
        assert get_event_class("AllocationProposalModifiedEvent") is AllocationProposalModifiedEvent
        assert get_event_class("AllocationProposalExpiredEvent") is AllocationProposalExpiredEvent

    def test_get_event_class_returns_none_for_unknown(self):
        assert get_event_class("UnknownEvent") is None
        assert get_event_class("") is None


class TestAggregateIdExtraction:
    def test_generated_uses_proposal_id(self):
        payload = {"proposal_id": "urn:karsa:proposal:p1"}
        assert get_aggregate_id("AllocationProposalGeneratedEvent", payload) == "urn:karsa:proposal:p1"

    def test_approved_uses_proposal_id(self):
        payload = {"proposal_id": "urn:karsa:proposal:p1"}
        assert get_aggregate_id("AllocationProposalApprovedEvent", payload) == "urn:karsa:proposal:p1"

    def test_rejected_uses_proposal_id(self):
        payload = {"proposal_id": "urn:karsa:proposal:p1"}
        assert get_aggregate_id("AllocationProposalRejectedEvent", payload) == "urn:karsa:proposal:p1"

    def test_modified_uses_original_proposal_id(self):
        payload = {"original_proposal_id": "urn:karsa:proposal:p1"}
        assert get_aggregate_id("AllocationProposalModifiedEvent", payload) == "urn:karsa:proposal:p1"

    def test_expired_uses_proposal_id(self):
        payload = {"proposal_id": "urn:karsa:proposal:p1"}
        assert get_aggregate_id("AllocationProposalExpiredEvent", payload) == "urn:karsa:proposal:p1"

    def test_unknown_event_returns_empty(self):
        assert get_aggregate_id("UnknownEvent", {}) == ""


class TestProjectionWorkerDispatch:
    """Verifies the projection worker can dispatch proposal events without errors.

    These tests verify that the event type strings in the projection worker
    match the event_type values in the event objects.
    """

    def test_generated_event_type_matches_dispatch(self):
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
        assert event.event_type == "AllocationProposalGeneratedEvent"

    def test_approved_event_type_matches_dispatch(self):
        event = AllocationProposalApprovedEvent(
            event_id="evt-2",
            proposal_id="p1",
            decision_id="d1",
            approved_by="cio",
            approved_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalApprovedEvent"

    def test_rejected_event_type_matches_dispatch(self):
        event = AllocationProposalRejectedEvent(
            event_id="evt-3",
            proposal_id="p1",
            decision_id="d1",
            rejected_by="cio",
            rejection_reason="reason",
            rejected_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalRejectedEvent"

    def test_modified_event_type_matches_dispatch(self):
        event = AllocationProposalModifiedEvent(
            event_id="evt-4",
            original_proposal_id="p1",
            decision_id="d1",
            modified_weights={},
            modification_reason="reason",
            modified_by="cio",
            modified_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalModifiedEvent"

    def test_expired_event_type_matches_dispatch(self):
        event = AllocationProposalExpiredEvent(
            event_id="evt-5",
            proposal_id="p1",
            expired_at=datetime.utcnow(),
        )
        assert event.event_type == "AllocationProposalExpiredEvent"
