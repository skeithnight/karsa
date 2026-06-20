"""Allocation event registry — Sprint-06 Wave-5.

Central registry for all allocation proposal events.
Provides serialization, deserialization, and event type mapping.
"""
import json
from datetime import datetime
from typing import Dict, Any, Callable, Optional

from karsa.allocation.domain.events import (
    AllocationProposalGeneratedEvent,
    AllocationProposalApprovedEvent,
    AllocationProposalRejectedEvent,
    AllocationProposalModifiedEvent,
    AllocationProposalExpiredEvent,
)


# Event type -> class mapping
EVENT_REGISTRY: Dict[str, type] = {
    "AllocationProposalGeneratedEvent": AllocationProposalGeneratedEvent,
    "AllocationProposalApprovedEvent": AllocationProposalApprovedEvent,
    "AllocationProposalRejectedEvent": AllocationProposalRejectedEvent,
    "AllocationProposalModifiedEvent": AllocationProposalModifiedEvent,
    "AllocationProposalExpiredEvent": AllocationProposalExpiredEvent,
}

# Event type -> aggregate_id extractor
AGGREGATE_ID_EXTRACTORS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "AllocationProposalGeneratedEvent": lambda p: p.get("proposal_id", ""),
    "AllocationProposalApprovedEvent": lambda p: p.get("proposal_id", ""),
    "AllocationProposalRejectedEvent": lambda p: p.get("proposal_id", ""),
    "AllocationProposalModifiedEvent": lambda p: p.get("original_proposal_id", ""),
    "AllocationProposalExpiredEvent": lambda p: p.get("proposal_id", ""),
}


def get_event_class(event_type: str) -> Optional[type]:
    """Returns the event class for a given event type string."""
    return EVENT_REGISTRY.get(event_type)


def get_aggregate_id(event_type: str, payload: Dict[str, Any]) -> str:
    """Extracts the aggregate_id from an event payload."""
    extractor = AGGREGATE_ID_EXTRACTORS.get(event_type)
    if extractor:
        return extractor(payload)
    return ""


def serialize_event(event) -> Dict[str, Any]:
    """Serializes an event to a dict suitable for JSON storage."""
    if hasattr(event, 'to_dict'):
        return event.to_dict()
    # Fallback for events without to_dict
    return {
        "event_id": getattr(event, 'event_id', ''),
        "event_type": event.__class__.__name__,
        "event_version": getattr(event, 'event_version', 1),
        **{k: v for k, v in event.__dict__.items() if not k.startswith('_')},
    }


def deserialize_event(event_type: str, payload: Dict[str, Any]):
    """Deserializes an event payload back into an event object.

    Args:
        event_type: The event type string (e.g., "AllocationProposalGeneratedEvent").
        payload: The deserialized JSON payload.

    Returns:
        The reconstructed event object, or None if type not recognized.
    """
    event_class = get_event_class(event_type)
    if not event_class:
        return None

    # Convert ISO datetime strings back to datetime objects
    datetime_fields = {
        'generated_at', 'approved_at', 'rejected_at', 'modified_at', 'expired_at',
        'occurred_at', 'timestamp',
    }
    converted = {}
    for k, v in payload.items():
        if k in datetime_fields and isinstance(v, str):
            try:
                converted[k] = datetime.fromisoformat(v)
            except (ValueError, TypeError):
                converted[k] = v
        else:
            converted[k] = v

    # Filter to only fields that the dataclass accepts
    import dataclasses
    if dataclasses.is_dataclass(event_class):
        field_names = {f.name for f in dataclasses.fields(event_class)}
        filtered = {k: v for k, v in converted.items() if k in field_names}
    else:
        filtered = converted

    try:
        return event_class(**filtered)
    except (TypeError, ValueError) as e:
        print(f"Failed to deserialize {event_type}: {e}")
        return None


def roundtrip_event(event) -> bool:
    """Verifies serialization-deserialization roundtrip for an event.

    Returns True if the event survives roundtrip unchanged.
    """
    serialized = serialize_event(event)
    json_str = json.dumps(serialized, default=str)
    deserialized_payload = json.loads(json_str)
    reconstructed = deserialize_event(event.__class__.__name__, deserialized_payload)

    if reconstructed is None:
        return False

    # Compare serialized forms (normalized)
    reserialized = serialize_event(reconstructed)
    return json.dumps(serialized, sort_keys=True, default=str) == json.dumps(reserialized, sort_keys=True, default=str)
