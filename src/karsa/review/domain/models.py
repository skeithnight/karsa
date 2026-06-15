import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.review.domain.value_objects import (
    DecisionQualityAssessment,
    FailureClassification,
    SuccessClassification,
    ImprovementRecommendation,
    ReviewMethodologyManifest
)

class StateTransitionError(ValueError):
    pass

class ImmutabilityViolationError(TypeError):
    pass


class ReviewSession(VersionedAggregate):
    """
    ReviewSession aggregate manages the metadata and status of a review run.
    Allowed states: INITIATED -> CONDUCTING -> COMPLETED
    """
    def __init__(
        self,
        session_id: str,
        session_urn: str,
        horizon_start: datetime,
        horizon_end: datetime,
        raw_input_manifest_hash: str,
        status: str = "INITIATED",
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.session_id = str(uuid.UUID(session_id))  # Validate UUID format
        if not session_urn.startswith("urn:karsa:review:session:"):
            raise ValueError(f"Invalid session_urn format: {session_urn}")
        self.session_urn = session_urn
        
        if horizon_start >= horizon_end:
            raise ValueError("horizon_start must be strictly before horizon_end")
        self.horizon_start = horizon_start
        self.horizon_end = horizon_end
        
        if len(raw_input_manifest_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in raw_input_manifest_hash):
            raise ValueError("raw_input_manifest_hash must be a valid 64-character SHA-256 hash")
        self.raw_input_manifest_hash = raw_input_manifest_hash
        
        if status not in ("INITIATED", "CONDUCTING", "COMPLETED"):
            raise ValueError(f"Invalid session status: {status}")
        self.status = status
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if self.status == "COMPLETED" and name != "aggregate_version":
                raise ImmutabilityViolationError("Cannot modify completed ReviewSession")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            if self.status == "COMPLETED":
                raise ImmutabilityViolationError("Cannot delete attribute on completed ReviewSession")
        super().__delattr__(name)

    def start_reviews(self) -> None:
        if self.status != "INITIATED":
            raise StateTransitionError(f"Cannot transition to CONDUCTING from state {self.status}")
        self.status = "CONDUCTING"
        self.aggregate_version += 1

    def complete(self) -> None:
        if self.status != "CONDUCTING":
            raise StateTransitionError(f"Cannot transition to COMPLETED from state {self.status}")
        self.status = "COMPLETED"
        self.aggregate_version += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_urn": self.session_urn,
            "horizon_start": self.horizon_start.isoformat(),
            "horizon_end": self.horizon_end.isoformat(),
            "raw_input_manifest_hash": self.raw_input_manifest_hash,
            "status": self.status,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewSession':
        return cls(
            session_id=data["session_id"],
            session_urn=data["session_urn"],
            horizon_start=datetime.fromisoformat(data["horizon_start"]),
            horizon_end=datetime.fromisoformat(data["horizon_end"]),
            raw_input_manifest_hash=data["raw_input_manifest_hash"],
            status=data["status"],
            aggregate_version=data.get("aggregate_version", 1)
        )


class ReviewRecord(VersionedAggregate):
    """
    ReviewRecord is a write-once ledger record representing a reviewer's ex-post quality assessment.
    """
    def __init__(
        self,
        record_id: str,
        record_urn: str,
        session_urn: str,
        decision_id: str,
        worker_urn: str,
        review_methodology_urn: str,
        review_policy_hash: str,
        review_prompt_version: str,
        reviewer_model_version: str,
        review_methodology_manifest_hash: str,
        decision_quality: DecisionQualityAssessment,
        reviewed_at: datetime,
        review_version: int = 1,
        is_active: bool = True,
        superseded_by_version: Optional[int] = None,
        invalidated_by_version: Optional[int] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.record_id = str(uuid.UUID(record_id))
        
        if not record_urn.startswith("urn:karsa:review:record:"):
            raise ValueError(f"Invalid record_urn format: {record_urn}")
        self.record_urn = record_urn
        
        if not session_urn.startswith("urn:karsa:review:session:"):
            raise ValueError(f"Invalid session_urn format: {session_urn}")
        self.session_urn = session_urn
        
        if not decision_id:
            raise ValueError("decision_id cannot be empty")
        self.decision_id = decision_id
        
        if not worker_urn.startswith("urn:karsa:worker:"):
            raise ValueError(f"Invalid worker_urn format: {worker_urn}")
        self.worker_urn = worker_urn
        
        # Verify methodology manifest matches recomputed hash
        manifest = ReviewMethodologyManifest(
            review_methodology_urn=review_methodology_urn,
            review_policy_hash=review_policy_hash,
            review_prompt_version=review_prompt_version,
            reviewer_model_version=reviewer_model_version
        )
        if manifest.compute_hash() != review_methodology_manifest_hash:
            raise ValueError("review_methodology_manifest_hash mismatch with computed manifest properties")
            
        self.review_methodology_urn = review_methodology_urn
        self.review_policy_hash = review_policy_hash
        self.review_prompt_version = review_prompt_version
        self.reviewer_model_version = reviewer_model_version
        self.review_methodology_manifest_hash = review_methodology_manifest_hash
        
        self.decision_quality = decision_quality
        self.reviewed_at = reviewed_at
        
        if review_version < 1:
            raise ValueError("review_version must be positive integer >= 1")
        self.review_version = review_version
        self.is_active = is_active
        
        if superseded_by_version is not None and superseded_by_version < 1:
            raise ValueError("superseded_by_version must be positive integer >= 1")
        self.superseded_by_version = superseded_by_version
        
        if invalidated_by_version is not None and invalidated_by_version < 1:
            raise ValueError("invalidated_by_version must be positive integer >= 1")
        self.invalidated_by_version = invalidated_by_version
        
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if name in ("is_active", "superseded_by_version", "invalidated_by_version", "aggregate_version"):
                if name == "is_active" and self.is_active is False and value is True:
                    raise ImmutabilityViolationError("Cannot reactivate an inactive record")
                super().__setattr__(name, value)
                return
            else:
                raise ImmutabilityViolationError(f"Cannot modify immutable field '{name}' on ReviewRecord")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise ImmutabilityViolationError("Cannot delete attribute on write-once records")
        super().__delattr__(name)

    def supersede(self, next_version: int) -> None:
        if not self.is_active:
            raise ImmutabilityViolationError("Cannot supersede an inactive record")
        self.is_active = False
        self.superseded_by_version = next_version
        self.aggregate_version += 1

    def invalidate(self, invalidating_version: int) -> None:
        if not self.is_active:
            raise ImmutabilityViolationError("Cannot invalidate an inactive record")
        self.is_active = False
        self.invalidated_by_version = invalidating_version
        self.aggregate_version += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_urn": self.record_urn,
            "session_urn": self.session_urn,
            "decision_id": self.decision_id,
            "worker_urn": self.worker_urn,
            "review_methodology_urn": self.review_methodology_urn,
            "review_policy_hash": self.review_policy_hash,
            "review_prompt_version": self.review_prompt_version,
            "reviewer_model_version": self.reviewer_model_version,
            "review_methodology_manifest_hash": self.review_methodology_manifest_hash,
            "decision_quality": self.decision_quality.to_dict(),
            "reviewed_at": self.reviewed_at.isoformat(),
            "review_version": self.review_version,
            "is_active": self.is_active,
            "superseded_by_version": self.superseded_by_version,
            "invalidated_by_version": self.invalidated_by_version,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewRecord':
        return cls(
            record_id=data["record_id"],
            record_urn=data["record_urn"],
            session_urn=data["session_urn"],
            decision_id=data["decision_id"],
            worker_urn=data["worker_urn"],
            review_methodology_urn=data["review_methodology_urn"],
            review_policy_hash=data["review_policy_hash"],
            review_prompt_version=data["review_prompt_version"],
            reviewer_model_version=data["reviewer_model_version"],
            review_methodology_manifest_hash=data["review_methodology_manifest_hash"],
            decision_quality=DecisionQualityAssessment.from_dict(data["decision_quality"]),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
            review_version=data["review_version"],
            is_active=data["is_active"],
            superseded_by_version=data.get("superseded_by_version"),
            invalidated_by_version=data.get("invalidated_by_version"),
            aggregate_version=data.get("aggregate_version", 1)
        )


class PostMortemRecord(VersionedAggregate):
    """
    PostMortemRecord is a write-once ledger record representing synthesized consensus post-mortem outcomes.
    """
    def __init__(
        self,
        postmortem_id: str,
        postmortem_urn: str,
        session_urn: str,
        decision_id: str,
        consensus_methodology_urn: str,
        consensus_policy_hash: str,
        input_review_record_urns: List[str],
        failure_classification: FailureClassification,
        success_classification: SuccessClassification,
        recommendation: ImprovementRecommendation,
        created_at: datetime,
        postmortem_version: int = 1,
        is_active: bool = True,
        superseded_by_version: Optional[int] = None,
        invalidated_by_version: Optional[int] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.postmortem_id = str(uuid.UUID(postmortem_id))
        
        if not postmortem_urn.startswith("urn:karsa:postmortem:record:"):
            raise ValueError(f"Invalid postmortem_urn format: {postmortem_urn}")
        self.postmortem_urn = postmortem_urn
        
        if not session_urn.startswith("urn:karsa:review:session:"):
            raise ValueError(f"Invalid session_urn format: {session_urn}")
        self.session_urn = session_urn
        
        if not decision_id:
            raise ValueError("decision_id cannot be empty")
        self.decision_id = decision_id
        
        if not consensus_methodology_urn.startswith("urn:karsa:consensus:"):
            raise ValueError(f"Invalid consensus_methodology_urn format: {consensus_methodology_urn}")
        self.consensus_methodology_urn = consensus_methodology_urn
        
        if len(consensus_policy_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in consensus_policy_hash):
            raise ValueError("consensus_policy_hash must be a valid 64-character SHA-256 hash")
        self.consensus_policy_hash = consensus_policy_hash
        
        if not input_review_record_urns or not isinstance(input_review_record_urns, list):
            raise ValueError("input_review_record_urns must be a non-empty list of URN strings")
        for urn in input_review_record_urns:
            if not urn.startswith("urn:karsa:review:record:"):
                raise ValueError(f"Invalid input_review_record_urn format: {urn}")
        self.input_review_record_urns = list(input_review_record_urns)
        
        self.failure_classification = failure_classification
        self.success_classification = success_classification
        self.recommendation = recommendation
        self.created_at = created_at
        
        if postmortem_version < 1:
            raise ValueError("postmortem_version must be positive integer >= 1")
        self.postmortem_version = postmortem_version
        self.is_active = is_active
        
        if superseded_by_version is not None and superseded_by_version < 1:
            raise ValueError("superseded_by_version must be positive integer >= 1")
        self.superseded_by_version = superseded_by_version
        
        if invalidated_by_version is not None and invalidated_by_version < 1:
            raise ValueError("invalidated_by_version must be positive integer >= 1")
        self.invalidated_by_version = invalidated_by_version
        
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if name in ("is_active", "superseded_by_version", "invalidated_by_version", "aggregate_version"):
                if name == "is_active" and self.is_active is False and value is True:
                    raise ImmutabilityViolationError("Cannot reactivate an inactive record")
                super().__setattr__(name, value)
                return
            else:
                raise ImmutabilityViolationError(f"Cannot modify immutable field '{name}' on PostMortemRecord")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise ImmutabilityViolationError("Cannot delete attribute on write-once records")
        super().__delattr__(name)

    def supersede(self, next_version: int) -> None:
        if not self.is_active:
            raise ImmutabilityViolationError("Cannot supersede an inactive record")
        self.is_active = False
        self.superseded_by_version = next_version
        self.aggregate_version += 1

    def invalidate(self, invalidating_version: int) -> None:
        if not self.is_active:
            raise ImmutabilityViolationError("Cannot invalidate an inactive record")
        self.is_active = False
        self.invalidated_by_version = invalidating_version
        self.aggregate_version += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "postmortem_id": self.postmortem_id,
            "postmortem_urn": self.postmortem_urn,
            "session_urn": self.session_urn,
            "decision_id": self.decision_id,
            "consensus_methodology_urn": self.consensus_methodology_urn,
            "consensus_policy_hash": self.consensus_policy_hash,
            "input_review_record_urns": list(self.input_review_record_urns),
            "failure_classification": self.failure_classification.to_dict(),
            "success_classification": self.success_classification.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "created_at": self.created_at.isoformat(),
            "postmortem_version": self.postmortem_version,
            "is_active": self.is_active,
            "superseded_by_version": self.superseded_by_version,
            "invalidated_by_version": self.invalidated_by_version,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PostMortemRecord':
        return cls(
            postmortem_id=data["postmortem_id"],
            postmortem_urn=data["postmortem_urn"],
            session_urn=data["session_urn"],
            decision_id=data["decision_id"],
            consensus_methodology_urn=data["consensus_methodology_urn"],
            consensus_policy_hash=data["consensus_policy_hash"],
            input_review_record_urns=list(data["input_review_record_urns"]),
            failure_classification=FailureClassification.from_dict(data["failure_classification"]),
            success_classification=SuccessClassification.from_dict(data["success_classification"]),
            recommendation=ImprovementRecommendation.from_dict(data["recommendation"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            postmortem_version=data["postmortem_version"],
            is_active=data["is_active"],
            superseded_by_version=data.get("superseded_by_version"),
            invalidated_by_version=data.get("invalidated_by_version"),
            aggregate_version=data.get("aggregate_version", 1)
        )
