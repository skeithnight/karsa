import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    event_version: int

    def __post_init__(self):
        # Validate UUID structure
        uuid.UUID(self.event_id)
        if not self.correlation_id:
            raise ValueError("correlation_id cannot be empty")
        if not self.causation_id:
            raise ValueError("causation_id cannot be empty")
        if not isinstance(self.occurred_at, datetime):
            raise ValueError("occurred_at must be a datetime object")
        if self.event_version < 1:
            raise ValueError("event_version must be positive integer >= 1")


@dataclass(frozen=True)
class ReviewRecordRecordedEvent(DomainEvent):
    record_urn: str
    session_urn: str
    decision_id: str
    reviewer_urn: str
    review_methodology_manifest_hash: str
    review_version: int

    def __post_init__(self):
        super().__post_init__()
        if not self.record_urn.startswith("urn:karsa:review:record:"):
            raise ValueError(f"Invalid record_urn: {self.record_urn}")
        if not self.session_urn.startswith("urn:karsa:review:session:"):
            raise ValueError(f"Invalid session_urn: {self.session_urn}")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty")
        if not self.reviewer_urn.startswith("urn:karsa:worker:"):
            raise ValueError(f"Invalid reviewer_urn: {self.reviewer_urn}")
        if len(self.review_methodology_manifest_hash) != 64:
            raise ValueError("review_methodology_manifest_hash must be 64 characters")
        if self.review_version < 1:
            raise ValueError("review_version must be positive integer >= 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat(),
            "event_version": self.event_version,
            "record_urn": self.record_urn,
            "session_urn": self.session_urn,
            "decision_id": self.decision_id,
            "reviewer_urn": self.reviewer_urn,
            "review_methodology_manifest_hash": self.review_methodology_manifest_hash,
            "review_version": self.review_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewRecordRecordedEvent':
        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            event_version=int(data["event_version"]),
            record_urn=data["record_urn"],
            session_urn=data["session_urn"],
            decision_id=data["decision_id"],
            reviewer_urn=data["reviewer_urn"],
            review_methodology_manifest_hash=data["review_methodology_manifest_hash"],
            review_version=int(data["review_version"])
        )


@dataclass(frozen=True)
class FailureClassificationRecordedEvent(DomainEvent):
    decision_id: str
    thesis_error: bool
    execution_error: bool
    timing_error: bool
    sizing_error: bool
    calibration_error: bool
    recommendation_code: str
    severity: str

    def __post_init__(self):
        super().__post_init__()
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty")
        if not all(isinstance(v, bool) for v in (self.thesis_error, self.execution_error, self.timing_error, self.sizing_error, self.calibration_error)):
            raise ValueError("Failure flags must be booleans")
        if not self.recommendation_code:
            raise ValueError("recommendation_code cannot be empty")
        if not self.severity:
            raise ValueError("severity cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat(),
            "event_version": self.event_version,
            "decision_id": self.decision_id,
            "thesis_error": self.thesis_error,
            "execution_error": self.execution_error,
            "timing_error": self.timing_error,
            "sizing_error": self.sizing_error,
            "calibration_error": self.calibration_error,
            "recommendation_code": self.recommendation_code,
            "severity": self.severity
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailureClassificationRecordedEvent':
        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            event_version=int(data["event_version"]),
            decision_id=data["decision_id"],
            thesis_error=bool(data["thesis_error"]),
            execution_error=bool(data["execution_error"]),
            timing_error=bool(data["timing_error"]),
            sizing_error=bool(data["sizing_error"]),
            calibration_error=bool(data["calibration_error"]),
            recommendation_code=data["recommendation_code"],
            severity=data["severity"]
        )


@dataclass(frozen=True)
class PostMortemFinalizedEvent(DomainEvent):
    postmortem_urn: str
    session_urn: str
    decision_id: str
    input_review_record_urns: List[str]
    postmortem_version: int
    consensus_methodology_urn: str
    consensus_policy_hash: str

    def __post_init__(self):
        super().__post_init__()
        if not self.postmortem_urn.startswith("urn:karsa:postmortem:record:"):
            raise ValueError(f"Invalid postmortem_urn: {self.postmortem_urn}")
        if not self.session_urn.startswith("urn:karsa:review:session:"):
            raise ValueError(f"Invalid session_urn: {self.session_urn}")
        if not self.decision_id:
            raise ValueError("decision_id cannot be empty")
        if not self.input_review_record_urns:
            raise ValueError("input_review_record_urns cannot be empty")
        for urn in self.input_review_record_urns:
            if not urn.startswith("urn:karsa:review:record:"):
                raise ValueError(f"Invalid input review record URN: {urn}")
        if self.postmortem_version < 1:
            raise ValueError("postmortem_version must be positive integer >= 1")
        if not self.consensus_methodology_urn.startswith("urn:karsa:consensus:"):
            raise ValueError(f"Invalid consensus_methodology_urn: {self.consensus_methodology_urn}")
        if len(self.consensus_policy_hash) != 64:
            raise ValueError("consensus_policy_hash must be 64 characters")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat(),
            "event_version": self.event_version,
            "postmortem_urn": self.postmortem_urn,
            "session_urn": self.session_urn,
            "decision_id": self.decision_id,
            "input_review_record_urns": list(self.input_review_record_urns),
            "postmortem_version": self.postmortem_version,
            "consensus_methodology_urn": self.consensus_methodology_urn,
            "consensus_policy_hash": self.consensus_policy_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PostMortemFinalizedEvent':
        return cls(
            event_id=data["event_id"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            event_version=int(data["event_version"]),
            postmortem_urn=data["postmortem_urn"],
            session_urn=data["session_urn"],
            decision_id=data["decision_id"],
            input_review_record_urns=list(data["input_review_record_urns"]),
            postmortem_version=int(data["postmortem_version"]),
            consensus_methodology_urn=data["consensus_methodology_urn"],
            consensus_policy_hash=data["consensus_policy_hash"]
        )
