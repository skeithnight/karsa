from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class CommitteeVote:
    voter_id: str
    vote_type: str  # "APPROVE", "REJECT"
    timestamp: datetime

    def __post_init__(self):
        if not self.voter_id or not self.voter_id.strip():
            raise ValueError("voter_id cannot be empty.")
        if self.vote_type not in ("APPROVE", "REJECT"):
            raise ValueError("vote_type must be either APPROVE or REJECT.")

@dataclass(frozen=True)
class AllocationApproval:
    calculation_id: str
    approved_weights: Dict[str, float]

    def __post_init__(self):
        if not self.calculation_id or not self.calculation_id.strip():
            raise ValueError("calculation_id cannot be empty.")
        if not self.approved_weights:
            raise ValueError("approved_weights cannot be empty.")
        for worker, weight in self.approved_weights.items():
            if weight < 0.0:
                raise ValueError(f"Weight for {worker} cannot be negative.")

@dataclass(frozen=True)
class OverrideReason:
    justification: str
    referenced_incident_urn: Optional[str] = None

    def __post_init__(self):
        if not self.justification or not self.justification.strip():
            raise ValueError("justification cannot be empty.")

@dataclass(frozen=True)
class PortfolioSnapshotReference:
    snapshot_id: str
    snapshot_hash: str
    created_at: datetime

    def __post_init__(self):
        if not self.snapshot_id or not self.snapshot_id.strip():
            raise ValueError("snapshot_id cannot be empty.")
        if not self.snapshot_hash or not self.snapshot_hash.strip():
            raise ValueError("snapshot_hash cannot be empty.")

@dataclass(frozen=True)
class SignaturePayload:
    decision_id: str
    target_node_id: str
    allocated_weights: Dict[str, float]
    portfolio_snapshot_hash: str
    governance_exception_id: Optional[str] = None

    def __post_init__(self):
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.target_node_id or not self.target_node_id.strip():
            raise ValueError("target_node_id cannot be empty.")
        if not self.allocated_weights:
            raise ValueError("allocated_weights cannot be empty.")
        if not self.portfolio_snapshot_hash or not self.portfolio_snapshot_hash.strip():
            raise ValueError("portfolio_snapshot_hash cannot be empty.")
        for w, weight in self.allocated_weights.items():
            if weight < 0.0:
                raise ValueError(f"Weight for {w} cannot be negative.")

    def serialize(self) -> str:
        """Serializes the payload deterministically for cryptographic signing."""
        sorted_weights = sorted(self.allocated_weights.items())
        weights_str = ",".join(f"{k}:{v}" for k, v in sorted_weights)
        exc_str = self.governance_exception_id or "none"
        return f"{self.decision_id}|{self.target_node_id}|{weights_str}|{self.portfolio_snapshot_hash}|{exc_str}"
