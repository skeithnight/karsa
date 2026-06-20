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


# --- Sprint-06 Proposal Events ---

@dataclass(frozen=True)
class AllocationProposalGeneratedEvent:
    """Emitted when a new allocation proposal is generated."""
    event_id: str
    proposal_id: str
    policy_id: str
    journal_ref: str
    proposed_weights: Dict[str, Any]
    total_capital: float
    proposal_rationale: str
    context_hash: str
    generated_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalGeneratedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.proposal_id:
            raise ValueError("proposal_id cannot be empty.")
        if not self.journal_ref:
            raise ValueError("journal_ref cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "proposal_id": self.proposal_id,
            "policy_id": self.policy_id,
            "journal_ref": self.journal_ref,
            "proposed_weights": self.proposed_weights,
            "total_capital": float(self.total_capital),
            "proposal_rationale": self.proposal_rationale,
            "context_hash": self.context_hash,
            "generated_at": self.generated_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class AllocationProposalApprovedEvent:
    """Emitted when CIO approves a proposal."""
    event_id: str
    proposal_id: str
    decision_id: str
    approved_by: str
    approved_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalApprovedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.proposal_id:
            raise ValueError("proposal_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "proposal_id": self.proposal_id,
            "decision_id": self.decision_id,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class AllocationProposalRejectedEvent:
    """Emitted when CIO rejects a proposal."""
    event_id: str
    proposal_id: str
    decision_id: str
    rejected_by: str
    rejection_reason: str
    rejected_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalRejectedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.proposal_id:
            raise ValueError("proposal_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "proposal_id": self.proposal_id,
            "decision_id": self.decision_id,
            "rejected_by": self.rejected_by,
            "rejection_reason": self.rejection_reason,
            "rejected_at": self.rejected_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class AllocationProposalModifiedEvent:
    """Emitted when CIO modifies a proposal."""
    event_id: str
    original_proposal_id: str
    decision_id: str
    modified_weights: Dict[str, float]
    modification_reason: str
    modified_by: str
    modified_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalModifiedEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.original_proposal_id:
            raise ValueError("original_proposal_id cannot be empty.")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "original_proposal_id": self.original_proposal_id,
            "decision_id": self.decision_id,
            "modified_weights": self.modified_weights,
            "modification_reason": self.modification_reason,
            "modified_by": self.modified_by,
            "modified_at": self.modified_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }


@dataclass(frozen=True)
class AllocationProposalExpiredEvent:
    """Emitted when a proposal expires."""
    event_id: str
    proposal_id: str
    expired_at: datetime
    event_sequence: int = 0
    event_type: str = "AllocationProposalExpiredEvent"
    event_version: int = 1

    def __post_init__(self):
        if not self.proposal_id:
            raise ValueError("proposal_id cannot be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "proposal_id": self.proposal_id,
            "expired_at": self.expired_at.isoformat(),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
        }
