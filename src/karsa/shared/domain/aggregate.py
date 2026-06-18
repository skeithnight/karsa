from typing import List, Optional
from .event import DomainEvent

class AggregateRoot:
    """Base class for aggregate roots in DDD."""
    def __init__(self):
        self._domain_events: List[DomainEvent] = []
        self._version: int = 0

    @property
    def version(self) -> int:
        return self._version

    def _increment_version(self) -> None:
        self._version += 1

    @property
    def aggregate_type(self) -> str:
        return self.__class__.__name__

    @property
    def stream_id(self) -> str:
        if not hasattr(self, "aggregate_id"):
            raise NotImplementedError("Aggregate must define self.aggregate_id")
        return f"{self.aggregate_type}:{self.aggregate_id}"

    def record_event(self, event: DomainEvent) -> None:
        """Record a domain event and increment the aggregate version."""
        if hasattr(self, "aggregate_id"):
            event.aggregate_id = self.aggregate_id
            event.aggregate_type = self.aggregate_type
            event.stream_id = self.stream_id
        
        self._domain_events.append(event)
        self._increment_version()

    def pull_domain_events(self) -> List[DomainEvent]:
        """Atomically retrieve and clear recorded domain events to prevent duplicate emission."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

class VersionedAggregate(AggregateRoot):
    """Aggregate root that explicitly tracks version for optimistic concurrency."""
    def __init__(self, aggregate_version: int = 1):
        super().__init__()
        self.aggregate_version = aggregate_version
        self._version = aggregate_version

    def increment_version(self) -> None:
        self.aggregate_version += 1
        super()._increment_version()

