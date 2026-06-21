"""CapabilityEventDispatcher -- Sprint-11. Wave-6.

Routes domain events to registered handlers with ordering guarantees.

Supported events:
- CapabilityEvolutionRecordedEvent
- CapabilityHealthScoreUpdatedEvent
- CapabilityEvolutionCanonicalChangedEvent
- CapabilityEvolutionDeferredEvent
- ScoringAlgorithmChangedEvent
- GovernanceCapabilitySuspendedEvent
- GovernanceCapabilityUnsuspendedEvent
- CapabilityHealthScoreUpdateFailedEvent (synthetic)
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from karsa.capability_engine.domain.events.capability_events import (
    CapabilityEvolutionCanonicalChangedEvent,
    CapabilityEvolutionDeferredEvent,
    CapabilityEvolutionRecordedEvent,
    CapabilityHealthScoreUpdatedEvent,
    GovernanceCapabilitySuspendedEvent,
    GovernanceCapabilityUnsuspendedEvent,
    ScoringAlgorithmChangedEvent,
)

# All supported event type strings
SUPPORTED_EVENT_TYPES: frozenset = frozenset([
    "CapabilityEvolutionRecordedEvent",
    "CapabilityHealthScoreUpdatedEvent",
    "CapabilityEvolutionCanonicalChangedEvent",
    "CapabilityEvolutionDeferredEvent",
    "ScoringAlgorithmChangedEvent",
    "GovernanceCapabilitySuspendedEvent",
    "GovernanceCapabilityUnsuspendedEvent",
    "CapabilityHealthScoreUpdateFailedEvent",
])


@dataclass
class DispatchResult:
    """Result of dispatching a single event."""

    event_type: str
    handled: bool
    handler_name: Optional[str] = None
    error: Optional[str] = None


class CapabilityEventDispatcher:
    """Routes domain events to registered handlers.

    Ordering guarantees:
    - Events are dispatched in the order they are received.
    - Each event is dispatched to exactly one handler.
    - Unknown event types are rejected (not silently dropped).
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._handler_names: Dict[str, str] = {}

    def register(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], None],
        handler_name: Optional[str] = None,
    ) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The event_type string (e.g. "CapabilityEvolutionRecordedEvent")
            handler: Callable that receives the event payload as a dict
            handler_name: Optional human-readable name for logging
        """
        self._handlers[event_type] = handler
        self._handler_names[event_type] = handler_name or handler.__name__

    def dispatch(self, event_type: str, payload: Dict[str, Any]) -> DispatchResult:
        """Dispatch a single event to its registered handler.

        Args:
            event_type: The event type string
            payload: The event payload as a dict

        Returns:
            DispatchResult with success/failure info

        Raises:
            ValueError: If event_type is not in SUPPORTED_EVENT_TYPES
        """
        if event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(
                f"Unknown event type: {event_type}. "
                f"Supported: {sorted(SUPPORTED_EVENT_TYPES)}"
            )

        handler = self._handlers.get(event_type)
        if handler is None:
            return DispatchResult(
                event_type=event_type,
                handled=False,
                error=f"No handler registered for {event_type}",
            )

        try:
            handler(payload)
            return DispatchResult(
                event_type=event_type,
                handled=True,
                handler_name=self._handler_names.get(event_type),
            )
        except Exception as e:
            return DispatchResult(
                event_type=event_type,
                handled=False,
                handler_name=self._handler_names.get(event_type),
                error=str(e),
            )

    def dispatch_batch(
        self, events: List[tuple]
    ) -> List[DispatchResult]:
        """Dispatch a batch of events in order.

        Args:
            events: List of (event_type, payload) tuples

        Returns:
            List of DispatchResult, one per event
        """
        results = []
        for event_type, payload in events:
            result = self.dispatch(event_type, payload)
            results.append(result)
        return results

    def has_handler(self, event_type: str) -> bool:
        """Check if a handler is registered for an event type."""
        return event_type in self._handlers

    @property
    def registered_event_types(self) -> List[str]:
        """List all registered event types."""
        return list(self._handlers.keys())
