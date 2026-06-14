from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any
from karsa.domain.events import DomainEvent

@dataclass
class AttributionCalculatedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    records: List[Dict[str, Any]] = field(default_factory=list)
    event_version: int = 1
    event_type: str = "AttributionCalculatedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "calculated_at": self.calculated_at.isoformat(),
            "records": self.records,
            "event_version": self.event_version
        }


@dataclass
class AttributionSupersededEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    record_id: str = ""
    old_version: int = 1
    new_version: int = 2
    superseded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    event_type: str = "AttributionSupersededEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "record_id": self.record_id,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "superseded_at": self.superseded_at.isoformat(),
            "event_version": self.event_version
        }


@dataclass
class AttributionInvalidatedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    invalidated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    event_type: str = "AttributionInvalidatedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "invalidated_at": self.invalidated_at.isoformat(),
            "event_version": self.event_version
        }


@dataclass
class AttributionRecomputedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    recomputed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    event_type: str = "AttributionRecomputedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "recomputed_at": self.recomputed_at.isoformat(),
            "event_version": self.event_version
        }
