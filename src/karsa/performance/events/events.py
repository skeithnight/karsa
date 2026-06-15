from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any
from karsa.domain.events import DomainEvent

@dataclass
class PerformanceSessionStagedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    staged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    event_type: str = "PerformanceSessionStagedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "staged_at": self.staged_at.isoformat(),
            "event_version": self.event_version
        }

@dataclass
class PerformanceSessionEvaluatedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    records: List[Dict[str, Any]] = field(default_factory=list)
    event_version: int = 1
    event_type: str = "PerformanceSessionEvaluatedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "records": self.records,
            "event_version": self.event_version
        }

@dataclass
class PerformanceSessionSealedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    sealed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_version: int = 1
    event_type: str = "PerformanceSessionSealedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "sealed_at": self.sealed_at.isoformat(),
            "event_version": self.event_version
        }

@dataclass
class BrierScoreCalibratedEvent(DomainEvent):
    event_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    calibrated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    calibrations: List[Dict[str, Any]] = field(default_factory=list)
    event_version: int = 1
    event_type: str = "BrierScoreCalibratedEvent"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "session_id": self.session_id,
            "calibrated_at": self.calibrated_at.isoformat(),
            "calibrations": self.calibrations,
            "event_version": self.event_version
        }
