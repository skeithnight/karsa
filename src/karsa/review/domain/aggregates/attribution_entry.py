"""AttributionEntry aggregate — Sprint-07 Wave-1."""
from dataclasses import dataclass
from datetime import datetime

from karsa.review.domain.aggregates.review_cycle import ImmutableLedgerEntry
from karsa.review.domain.value_objects.review_verdict import AttributionDimension, AttributionType


@dataclass
class AttributionEntry(ImmutableLedgerEntry):
    """Write-once ledger entry for attribution tracking.

    Variable cardinality: multiple entries per review per dimension.
    WORKER: 1..N entries
    ALLOCATION: 1..N entries
    CIO: 0..1 entries
    PORTFOLIO: 0..1 entries
    """
    attribution_id: str
    review_id: str
    dimension: AttributionDimension
    target_urn: str
    contribution_bps: float
    contribution_pct: float
    attribution_type: AttributionType
    evidence: dict
    created_at: datetime

    def __post_init__(self):
        if not self.attribution_id or not self.attribution_id.strip():
            raise ValueError("attribution_id cannot be empty.")
        if not self.review_id or not self.review_id.strip():
            raise ValueError("review_id cannot be empty.")
        if not self.target_urn or not self.target_urn.strip():
            raise ValueError("target_urn cannot be empty.")

    @classmethod
    def from_contribution(
        cls,
        attribution_id: str,
        review_id: str,
        dimension: AttributionDimension,
        target_urn: str,
        contribution_bps: float,
        total_bps: float,
        evidence: dict,
        created_at: datetime,
    ) -> "AttributionEntry":
        """Factory that computes attribution_type from contribution sign."""
        if total_bps != 0:
            contribution_pct = contribution_bps / total_bps
        else:
            contribution_pct = 0.0

        if contribution_bps > 0:
            attr_type = AttributionType.POSITIVE
        elif contribution_bps < 0:
            attr_type = AttributionType.NEGATIVE
        else:
            attr_type = AttributionType.NEUTRAL

        return cls(
            attribution_id=attribution_id,
            review_id=review_id,
            dimension=dimension,
            target_urn=target_urn,
            contribution_bps=round(contribution_bps, 4),
            contribution_pct=round(contribution_pct, 6),
            attribution_type=attr_type,
            evidence=evidence,
            created_at=created_at,
        )
