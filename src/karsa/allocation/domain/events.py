import uuid
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    schema_version: int

    def __post_init__(self):
        uuid.UUID(self.event_id)
        if not self.correlation_id:
            raise ValueError("correlation_id cannot be empty")
        if not self.causation_id:
            raise ValueError("causation_id cannot be empty")
        if not isinstance(self.occurred_at, datetime):
            raise ValueError("occurred_at must be a datetime object")
        if self.schema_version < 1:
            raise ValueError("schema_version must be positive integer >= 1")


@dataclass(frozen=True)
class AllocationCalculatedEvent(DomainEvent):
    record_urn: str
    session_urn: str
    worker_urn: str
    decision_id: str
    recommended_weight: float
    allocation_version: int

    def __post_init__(self):
        super().__post_init__()
        if not self.record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid record_urn: {self.record_urn}")
        if not self.session_urn.startswith("urn:karsa:allocation:session:"):
            raise ValueError(f"Invalid session_urn: {self.session_urn}")
        if not self.worker_urn.startswith("urn:karsa:worker:"):
            raise ValueError(f"Invalid worker_urn: {self.worker_urn}")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty")
        if not isinstance(self.recommended_weight, (int, float)):
            raise ValueError("recommended_weight must be a numeric value")
        if self.allocation_version < 1:
            raise ValueError("allocation_version must be positive integer >= 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat(),
            "schema_version": self.schema_version,
            "record_urn": self.record_urn,
            "session_urn": self.session_urn,
            "worker_urn": self.worker_urn,
            "decision_id": self.decision_id,
            "recommended_weight": float(self.recommended_weight),
            "allocation_version": self.allocation_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationCalculatedEvent':
        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            schema_version=int(data["schema_version"]),
            record_urn=data["record_urn"],
            session_urn=data["session_urn"],
            worker_urn=data["worker_urn"],
            decision_id=data["decision_id"],
            recommended_weight=float(data["recommended_weight"]),
            allocation_version=int(data["allocation_version"])
        )


@dataclass(frozen=True)
class AllocationSupersededEvent(DomainEvent):
    record_urn: str
    superseded_by_record_urn: str
    allocation_version: int

    def __post_init__(self):
        super().__post_init__()
        if not self.record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid record_urn: {self.record_urn}")
        if not self.superseded_by_record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid superseded_by_record_urn: {self.superseded_by_record_urn}")
        if self.allocation_version < 1:
            raise ValueError("allocation_version must be positive integer >= 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat(),
            "schema_version": self.schema_version,
            "record_urn": self.record_urn,
            "superseded_by_record_urn": self.superseded_by_record_urn,
            "allocation_version": self.allocation_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationSupersededEvent':
        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            schema_version=int(data["schema_version"]),
            record_urn=data["record_urn"],
            superseded_by_record_urn=data["superseded_by_record_urn"],
            allocation_version=int(data["allocation_version"])
        )


@dataclass(frozen=True)
class AllocationInvalidatedEvent(DomainEvent):
    record_urn: str
    invalidated_by_version: int

    def __post_init__(self):
        super().__post_init__()
        if not self.record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid record_urn: {self.record_urn}")
        if self.invalidated_by_version < 1:
            raise ValueError("invalidated_by_version must be positive integer >= 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat(),
            "schema_version": self.schema_version,
            "record_urn": self.record_urn,
            "invalidated_by_version": self.invalidated_by_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationInvalidatedEvent':
        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            schema_version=int(data["schema_version"]),
            record_urn=data["record_urn"],
            invalidated_by_version=int(data["invalidated_by_version"])
        )
