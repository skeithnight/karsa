import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.allocation.domain.value_objects import (
    PortfolioHorizon,
    AllocationScore,
    AllocationRecommendation,
    AllocationMethodologyManifest
)

class StateTransitionError(ValueError):
    pass

class ImmutabilityViolationError(TypeError):
    pass


class AllocationSession(VersionedAggregate):
    """
    AllocationSession aggregate controls the lifecycle of an allocation run.
    States: INITIATED -> CALCULATING -> COMPLETED -> ARCHIVED
    """
    def __init__(
        self,
        session_id: str,
        session_urn: str,
        horizon: PortfolioHorizon,
        strategy_key: str,
        status: str = "INITIATED",
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.session_id = str(uuid.UUID(session_id))
        
        if not session_urn.startswith("urn:karsa:allocation:session:"):
            raise ValueError(f"Invalid session_urn format: {session_urn}")
        self.session_urn = session_urn
        
        if not isinstance(horizon, PortfolioHorizon):
            raise ValueError("horizon must be a PortfolioHorizon object")
        self.horizon = horizon
        
        if not strategy_key or not isinstance(strategy_key, str):
            raise ValueError("strategy_key must be a non-empty string")
        self.strategy_key = strategy_key
        
        if status not in ("INITIATED", "CALCULATING", "COMPLETED", "ARCHIVED"):
            raise ValueError(f"Invalid session status: {status}")
        self.status = status
        
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if self.status in ("COMPLETED", "ARCHIVED") and name != "aggregate_version" and name != "status":
                raise ImmutabilityViolationError("Cannot modify completed or archived AllocationSession")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            if self.status in ("COMPLETED", "ARCHIVED"):
                raise ImmutabilityViolationError("Cannot delete attribute on completed or archived AllocationSession")
        super().__delattr__(name)

    def start(self) -> None:
        if self.status != "INITIATED":
            raise StateTransitionError(f"Cannot transition to CALCULATING from {self.status}")
        self.status = "CALCULATING"
        self.increment_version()

    def complete(self) -> None:
        if self.status != "CALCULATING":
            raise StateTransitionError(f"Cannot transition to COMPLETED from {self.status}")
        self.status = "COMPLETED"
        self.increment_version()

    def archive(self) -> None:
        if self.status != "COMPLETED":
            raise StateTransitionError(f"Cannot transition to ARCHIVED from {self.status}")
        self.status = "ARCHIVED"
        self.increment_version()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_urn": self.session_urn,
            "horizon": self.horizon.to_dict(),
            "strategy_key": self.strategy_key,
            "status": self.status,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationSession':
        return cls(
            session_id=data["session_id"],
            session_urn=data["session_urn"],
            horizon=PortfolioHorizon.from_dict(data["horizon"]),
            strategy_key=data["strategy_key"],
            status=data["status"],
            aggregate_version=data.get("aggregate_version", 1)
        )


class AllocationDecisionRecord(VersionedAggregate):
    """
    AllocationDecisionRecord is an immutable ledger entry of a capital allocation decision.
    """
    def __init__(
        self,
        record_id: str,
        record_urn: str,
        session_urn: str,
        worker_urn: str,
        decision_id: str,
        horizon: PortfolioHorizon,
        allocation_score: AllocationScore,
        recommendation: AllocationRecommendation,
        allocation_methodology_urn: str,
        allocation_policy_hash: str,
        allocation_strategy_version: str,
        allocation_manifest_hash: str,
        supersedes_record_urn: Optional[str] = None,
        invalidates_record_urn: Optional[str] = None,
        is_active: bool = True,
        superseded_by_version: Optional[int] = None,
        invalidated_by_version: Optional[int] = None,
        allocated_at: Optional[datetime] = None,
        allocation_version: int = 1,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.record_id = str(uuid.UUID(record_id))
        
        if not record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid record_urn format: {record_urn}")
        self.record_urn = record_urn
        
        if not session_urn.startswith("urn:karsa:allocation:session:"):
            raise ValueError(f"Invalid session_urn format: {session_urn}")
        self.session_urn = session_urn
        
        if not worker_urn.startswith("urn:karsa:worker:"):
            raise ValueError(f"Invalid worker_urn format: {worker_urn}")
        self.worker_urn = worker_urn
        
        if not decision_id:
            raise ValueError("decision_id cannot be empty")
        self.decision_id = decision_id
        
        if not isinstance(horizon, PortfolioHorizon):
            raise ValueError("horizon must be a PortfolioHorizon object")
        self.horizon = horizon
        
        if not isinstance(allocation_score, AllocationScore):
            raise ValueError("allocation_score must be an AllocationScore object")
        self.allocation_score = allocation_score
        
        if not isinstance(recommendation, AllocationRecommendation):
            raise ValueError("recommendation must be an AllocationRecommendation object")
        self.recommendation = recommendation
        
        # Methodology verification
        manifest = AllocationMethodologyManifest(
            allocation_methodology_urn=allocation_methodology_urn,
            allocation_policy_hash=allocation_policy_hash,
            allocation_strategy_version=allocation_strategy_version
        )
        if manifest.compute_hash() != allocation_manifest_hash:
            raise ValueError("allocation_manifest_hash mismatch with computed manifest properties")
            
        self.allocation_methodology_urn = allocation_methodology_urn
        self.allocation_policy_hash = allocation_policy_hash
        self.allocation_strategy_version = allocation_strategy_version
        self.allocation_manifest_hash = allocation_manifest_hash
        
        if supersedes_record_urn is not None and not supersedes_record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid supersedes_record_urn format: {supersedes_record_urn}")
        self.supersedes_record_urn = supersedes_record_urn
        
        if invalidates_record_urn is not None and not invalidates_record_urn.startswith("urn:karsa:allocation:record:"):
            raise ValueError(f"Invalid invalidates_record_urn format: {invalidates_record_urn}")
        self.invalidates_record_urn = invalidates_record_urn
        
        self.is_active = is_active
        
        if superseded_by_version is not None and superseded_by_version < 1:
            raise ValueError("superseded_by_version must be positive integer >= 1")
        self.superseded_by_version = superseded_by_version
        
        if invalidated_by_version is not None and invalidated_by_version < 1:
            raise ValueError("invalidated_by_version must be positive integer >= 1")
        self.invalidated_by_version = invalidated_by_version
        
        self.allocated_at = allocated_at or datetime.now(timezone.utc)
        
        if allocation_version < 1:
            raise ValueError("allocation_version must be positive integer >= 1")
        self.allocation_version = allocation_version
        
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if name in ("is_active", "superseded_by_version", "invalidated_by_version", "aggregate_version"):
                if name == "is_active" and self.is_active is False and value is True:
                    raise ImmutabilityViolationError("Cannot reactivate an inactive record")
                super().__setattr__(name, value)
                return
            else:
                raise ImmutabilityViolationError(f"Cannot modify immutable field '{name}' on AllocationDecisionRecord")
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
        self.increment_version()

    def invalidate(self, invalidating_version: int) -> None:
        if not self.is_active:
            raise ImmutabilityViolationError("Cannot invalidate an inactive record")
        self.is_active = False
        self.invalidated_by_version = invalidating_version
        self.increment_version()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_urn": self.record_urn,
            "session_urn": self.session_urn,
            "worker_urn": self.worker_urn,
            "decision_id": self.decision_id,
            "horizon": self.horizon.to_dict(),
            "allocation_score": self.allocation_score.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "allocation_methodology_urn": self.allocation_methodology_urn,
            "allocation_policy_hash": self.allocation_policy_hash,
            "allocation_strategy_version": self.allocation_strategy_version,
            "allocation_manifest_hash": self.allocation_manifest_hash,
            "supersedes_record_urn": self.supersedes_record_urn,
            "invalidates_record_urn": self.invalidates_record_urn,
            "is_active": self.is_active,
            "superseded_by_version": self.superseded_by_version,
            "invalidated_by_version": self.invalidated_by_version,
            "allocated_at": self.allocated_at.isoformat(),
            "allocation_version": self.allocation_version,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationDecisionRecord':
        return cls(
            record_id=data["record_id"],
            record_urn=data["record_urn"],
            session_urn=data["session_urn"],
            worker_urn=data["worker_urn"],
            decision_id=data["decision_id"],
            horizon=PortfolioHorizon.from_dict(data["horizon"]),
            allocation_score=AllocationScore.from_dict(data["allocation_score"]),
            recommendation=AllocationRecommendation.from_dict(data["recommendation"]),
            allocation_methodology_urn=data["allocation_methodology_urn"],
            allocation_policy_hash=data["allocation_policy_hash"],
            allocation_strategy_version=data["allocation_strategy_version"],
            allocation_manifest_hash=data["allocation_manifest_hash"],
            supersedes_record_urn=data.get("supersedes_record_urn"),
            invalidates_record_urn=data.get("invalidates_record_urn"),
            is_active=data["is_active"],
            superseded_by_version=data.get("superseded_by_version"),
            invalidated_by_version=data.get("invalidated_by_version"),
            allocated_at=datetime.fromisoformat(data["allocated_at"]) if data.get("allocated_at") else None,
            allocation_version=data.get("allocation_version", 1),
            aggregate_version=data.get("aggregate_version", 1)
        )
