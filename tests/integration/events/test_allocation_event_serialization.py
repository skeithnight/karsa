"""Tests for allocation event serialization — Sprint-06 Wave-5.

Verifies:
- All 5 proposal events serialize correctly
- All 5 proposal events deserialize correctly
- Roundtrip serialization is identity
- JSON storage compatibility
"""
import json
import pytest
from datetime import datetime

from karsa.allocation.domain.events import (
    AllocationProposalGeneratedEvent,
    AllocationProposalApprovedEvent,
    AllocationProposalRejectedEvent,
    AllocationProposalModifiedEvent,
    AllocationProposalExpiredEvent,
)
from karsa.allocation.events import (
    serialize_event, deserialize_event, roundtrip_event,
    EVENT_REGISTRY, get_event_class, get_aggregate_id,
)


def _make_generated():
    return AllocationProposalGeneratedEvent(
        event_id="evt-gen-1",
        proposal_id="urn:karsa:proposal:p1",
        policy_id="policy-1",
        journal_ref="urn:karsa:journal:j1",
        proposed_weights={"w1": {"worker_urn": "w1", "proposed_weight": 0.6}},
        total_capital=100000.0,
        proposal_rationale="Test rationale.",
        context_hash="abc123",
        generated_at=datetime(2026, 6, 20, 12, 0, 0),
        event_sequence=1,
    )


def _make_approved():
    return AllocationProposalApprovedEvent(
        event_id="evt-app-1",
        proposal_id="urn:karsa:proposal:p1",
        decision_id="dec-1",
        approved_by="cio-1",
        approved_at=datetime(2026, 6, 20, 12, 5, 0),
        event_sequence=2,
    )


def _make_rejected():
    return AllocationProposalRejectedEvent(
        event_id="evt-rej-1",
        proposal_id="urn:karsa:proposal:p1",
        decision_id="dec-2",
        rejected_by="cio-1",
        rejection_reason="Insufficient conviction.",
        rejected_at=datetime(2026, 6, 20, 12, 5, 0),
        event_sequence=2,
    )


def _make_modified():
    return AllocationProposalModifiedEvent(
        event_id="evt-mod-1",
        original_proposal_id="urn:karsa:proposal:p1",
        decision_id="dec-3",
        modified_weights={"w1": 0.7, "w2": 0.3},
        modification_reason="Risk adjustment.",
        modified_by="cio-1",
        modified_at=datetime(2026, 6, 20, 12, 5, 0),
        event_sequence=2,
    )


def _make_expired():
    return AllocationProposalExpiredEvent(
        event_id="evt-exp-1",
        proposal_id="urn:karsa:proposal:p1",
        expired_at=datetime(2026, 6, 20, 12, 5, 0),
        event_sequence=2,
    )


class TestEventRegistry:
    def test_registry_contains_all_5_events(self):
        assert len(EVENT_REGISTRY) == 5
        assert "AllocationProposalGeneratedEvent" in EVENT_REGISTRY
        assert "AllocationProposalApprovedEvent" in EVENT_REGISTRY
        assert "AllocationProposalRejectedEvent" in EVENT_REGISTRY
        assert "AllocationProposalModifiedEvent" in EVENT_REGISTRY
        assert "AllocationProposalExpiredEvent" in EVENT_REGISTRY

    def test_get_event_class(self):
        assert get_event_class("AllocationProposalGeneratedEvent") is AllocationProposalGeneratedEvent
        assert get_event_class("UnknownEvent") is None

    def test_get_aggregate_id(self):
        assert get_aggregate_id("AllocationProposalGeneratedEvent", {"proposal_id": "p1"}) == "p1"
        assert get_aggregate_id("AllocationProposalModifiedEvent", {"original_proposal_id": "p1"}) == "p1"
        assert get_aggregate_id("UnknownEvent", {}) == ""


class TestGeneratedEventSerialization:
    def test_serialize(self):
        event = _make_generated()
        data = serialize_event(event)

        assert data["event_id"] == "evt-gen-1"
        assert data["proposal_id"] == "urn:karsa:proposal:p1"
        assert data["event_type"] == "AllocationProposalGeneratedEvent"
        assert data["event_version"] == 1
        assert data["total_capital"] == 100000.0

    def test_json_roundtrip(self):
        event = _make_generated()
        data = serialize_event(event)
        json_str = json.dumps(data, default=str)
        restored = json.loads(json_str)

        assert restored["proposal_id"] == event.proposal_id
        assert restored["total_capital"] == event.total_capital

    def test_full_roundtrip(self):
        event = _make_generated()
        assert roundtrip_event(event) is True

    def test_deserialize(self):
        event = _make_generated()
        data = serialize_event(event)
        json_str = json.dumps(data, default=str)
        payload = json.loads(json_str)

        result = deserialize_event("AllocationProposalGeneratedEvent", payload)
        assert result is not None
        assert result.proposal_id == event.proposal_id
        assert result.total_capital == event.total_capital


class TestApprovedEventSerialization:
    def test_serialize(self):
        event = _make_approved()
        data = serialize_event(event)

        assert data["event_id"] == "evt-app-1"
        assert data["proposal_id"] == "urn:karsa:proposal:p1"
        assert data["decision_id"] == "dec-1"
        assert data["event_type"] == "AllocationProposalApprovedEvent"

    def test_full_roundtrip(self):
        event = _make_approved()
        assert roundtrip_event(event) is True

    def test_deserialize(self):
        event = _make_approved()
        data = serialize_event(event)
        json_str = json.dumps(data, default=str)
        payload = json.loads(json_str)

        result = deserialize_event("AllocationProposalApprovedEvent", payload)
        assert result is not None
        assert result.decision_id == "dec-1"
        assert result.approved_by == "cio-1"


class TestRejectedEventSerialization:
    def test_serialize(self):
        event = _make_rejected()
        data = serialize_event(event)

        assert data["rejection_reason"] == "Insufficient conviction."
        assert data["event_type"] == "AllocationProposalRejectedEvent"

    def test_full_roundtrip(self):
        event = _make_rejected()
        assert roundtrip_event(event) is True

    def test_deserialize(self):
        event = _make_rejected()
        data = serialize_event(event)
        json_str = json.dumps(data, default=str)
        payload = json.loads(json_str)

        result = deserialize_event("AllocationProposalRejectedEvent", payload)
        assert result is not None
        assert result.rejection_reason == "Insufficient conviction."


class TestModifiedEventSerialization:
    def test_serialize(self):
        event = _make_modified()
        data = serialize_event(event)

        assert data["original_proposal_id"] == "urn:karsa:proposal:p1"
        assert data["modified_weights"] == {"w1": 0.7, "w2": 0.3}
        assert data["event_type"] == "AllocationProposalModifiedEvent"

    def test_full_roundtrip(self):
        event = _make_modified()
        assert roundtrip_event(event) is True

    def test_deserialize(self):
        event = _make_modified()
        data = serialize_event(event)
        json_str = json.dumps(data, default=str)
        payload = json.loads(json_str)

        result = deserialize_event("AllocationProposalModifiedEvent", payload)
        assert result is not None
        assert result.modified_weights == {"w1": 0.7, "w2": 0.3}


class TestExpiredEventSerialization:
    def test_serialize(self):
        event = _make_expired()
        data = serialize_event(event)

        assert data["proposal_id"] == "urn:karsa:proposal:p1"
        assert data["event_type"] == "AllocationProposalExpiredEvent"

    def test_full_roundtrip(self):
        event = _make_expired()
        assert roundtrip_event(event) is True

    def test_deserialize(self):
        event = _make_expired()
        data = serialize_event(event)
        json_str = json.dumps(data, default=str)
        payload = json.loads(json_str)

        result = deserialize_event("AllocationProposalExpiredEvent", payload)
        assert result is not None
        assert result.proposal_id == "urn:karsa:proposal:p1"


class TestEventMetadata:
    def test_all_events_have_required_fields(self):
        events = [
            _make_generated(), _make_approved(), _make_rejected(),
            _make_modified(), _make_expired(),
        ]
        for event in events:
            assert hasattr(event, 'event_id')
            assert hasattr(event, 'event_type')
            assert hasattr(event, 'event_version')
            assert event.event_version == 1
            assert len(event.event_id) > 0
            assert len(event.event_type) > 0

    def test_all_events_frozen(self):
        events = [
            _make_generated(), _make_approved(), _make_rejected(),
            _make_modified(), _make_expired(),
        ]
        for event in events:
            with pytest.raises(AttributeError):
                event.event_id = "changed"


class TestReplayCompatibility:
    def test_payload_stability(self):
        """Same event always produces same serialized payload."""
        event = _make_generated()
        data1 = serialize_event(event)
        data2 = serialize_event(event)
        assert json.dumps(data1, sort_keys=True) == json.dumps(data2, sort_keys=True)

    def test_version_stability(self):
        """Event version is always 1 for Sprint-06."""
        events = [
            _make_generated(), _make_approved(), _make_rejected(),
            _make_modified(), _make_expired(),
        ]
        for event in events:
            assert event.event_version == 1

    def test_json_storage_compatible(self):
        """All events can be stored as JSON strings."""
        events = [
            _make_generated(), _make_approved(), _make_rejected(),
            _make_modified(), _make_expired(),
        ]
        for event in events:
            data = serialize_event(event)
            json_str = json.dumps(data, default=str)
            assert len(json_str) > 0
            # Verify it can be parsed back
            parsed = json.loads(json_str)
            assert parsed["event_type"] == event.event_type
