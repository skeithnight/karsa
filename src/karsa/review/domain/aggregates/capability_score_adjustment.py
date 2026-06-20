"""CapabilityScoreAdjustment aggregate — Sprint-07 Wave-1."""
from dataclasses import dataclass
from datetime import datetime

from karsa.review.domain.aggregates.review_cycle import ImmutableLedgerEntry


@dataclass
class CapabilityScoreAdjustment(ImmutableLedgerEntry):
    """Write-once ledger entry for capability score adjustments.

    Stores only deltas. Current score derived from
    CapabilityScoreProjection via SUM(score_delta).
    """
    adjustment_id: str
    target_urn: str
    target_type: str  # WORKER | THESIS | STRATEGY
    score_delta: float
    confidence_delta: float
    review_id: str
    rationale: str
    created_at: datetime

    def __post_init__(self):
        if not self.adjustment_id or not self.adjustment_id.strip():
            raise ValueError("adjustment_id cannot be empty.")
        if not self.target_urn or not self.target_urn.strip():
            raise ValueError("target_urn cannot be empty.")
        if not self.target_type or not self.target_type.strip():
            raise ValueError("target_type cannot be empty.")
        if not self.review_id or not self.review_id.strip():
            raise ValueError("review_id cannot be empty.")
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale cannot be empty.")

    @classmethod
    def from_attribution(
        cls,
        adjustment_id: str,
        target_urn: str,
        target_type: str,
        contribution_bps: float,
        review_id: str,
        created_at: datetime,
    ) -> "CapabilityScoreAdjustment":
        """Factory that computes score_delta from attribution contribution."""
        # Score delta is proportional to contribution
        # Positive contribution → positive delta
        # Negative contribution → negative delta
        score_delta = contribution_bps / 10000.0  # Convert bps to decimal
        confidence_delta = 0.01 if contribution_bps > 0 else (-0.01 if contribution_bps < 0 else 0.0)

        rationale = f"Score adjustment from review {review_id}: contribution {contribution_bps:.1f} bps"

        return cls(
            adjustment_id=adjustment_id,
            target_urn=target_urn,
            target_type=target_type,
            score_delta=round(score_delta, 6),
            confidence_delta=round(confidence_delta, 4),
            review_id=review_id,
            rationale=rationale,
            created_at=created_at,
        )
