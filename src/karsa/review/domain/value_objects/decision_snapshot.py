"""DecisionSnapshot value object — Sprint-07 Wave-1."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class StructuredAssumption:
    assumption_id: str
    statement: str
    validation_criteria: str
    source_urn: Optional[str] = None


@dataclass(frozen=True)
class DecisionSnapshot:
    """Immutable snapshot of decision context captured at ReviewCycle creation.

    Review Engine never queries upstream systems after cycle creation.
    All review context is in this snapshot.
    """
    decision_id: str
    proposal_id: Optional[str]
    journal_ref: str
    action_type: str
    target_node_type: str
    target_node_id: str
    allocated_weights: Dict[str, float]
    policy_snapshot: Dict[str, Any]
    expected_return_bps: float
    expected_drawdown_pct: float
    expected_sharpe_ratio: float
    expected_horizon_days: int
    confidence_level: float
    benchmark_urn: Optional[str]
    regime_at_decision: Optional[str]
    key_assumptions: List[StructuredAssumption]
    attribution_expectations: Dict[str, float]
    decision_rationale: str
    decision_confidence: float
    decision_timestamp: str  # ISO datetime
    cryptographic_signature: str
    snapshot_hash: str  # SHA-256 of all fields

    def __post_init__(self):
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("decision_id cannot be empty.")
        if not self.journal_ref or not self.journal_ref.strip():
            raise ValueError("journal_ref cannot be empty.")
        if self.confidence_level < 0.0 or self.confidence_level > 1.0:
            raise ValueError("confidence_level must be between 0.0 and 1.0.")
        if self.expected_horizon_days <= 0:
            raise ValueError("expected_horizon_days must be positive.")

    @property
    def expected_outcome_dict(self) -> Dict[str, Any]:
        """Returns expected outcome as a dict for variance computation."""
        return {
            "expected_return_bps": self.expected_return_bps,
            "expected_drawdown_pct": self.expected_drawdown_pct,
            "expected_sharpe_ratio": self.expected_sharpe_ratio,
            "expected_horizon_days": self.expected_horizon_days,
            "confidence_level": self.confidence_level,
        }
