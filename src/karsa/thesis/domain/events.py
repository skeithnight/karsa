from dataclasses import dataclass, field
from typing import Dict, Any, List
from karsa.shared.domain.event import DomainEvent

@dataclass
class ThesisProposedEvent(DomainEvent):
    correlation_id: str = ""
    causation_id: str = ""
    stream_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "stream_version": self.stream_version,
            "payload": self.payload
        }

@dataclass
class ThesisActivatedEvent(DomainEvent):
    correlation_id: str = ""
    causation_id: str = ""
    stream_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "stream_version": self.stream_version,
            "payload": self.payload
        }

@dataclass
class ThesisChallengedEvent(DomainEvent):
    correlation_id: str = ""
    causation_id: str = ""
    stream_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "stream_version": self.stream_version,
            "payload": self.payload
        }

@dataclass
class ThesisRefinedEvent(DomainEvent):
    correlation_id: str = ""
    causation_id: str = ""
    stream_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "stream_version": self.stream_version,
            "payload": self.payload
        }

@dataclass
class ThesisInvalidatedEvent(DomainEvent):
    correlation_id: str = ""
    causation_id: str = ""
    stream_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "stream_version": self.stream_version,
            "payload": self.payload
        }

@dataclass
class ThesisRetiredEvent(DomainEvent):
    correlation_id: str = ""
    causation_id: str = ""
    stream_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "stream_version": self.stream_version,
            "payload": self.payload
        }
