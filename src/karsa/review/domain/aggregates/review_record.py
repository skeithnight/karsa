"""ReviewRecord aggregate — Sprint-07 Wave-1."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from karsa.review.domain.aggregates.review_cycle import ImmutableLedgerEntry
from karsa.review.domain.value_objects.review_verdict import ReviewType, ReviewVerdict
from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis


@dataclass
class ReviewRecord(ImmutableLedgerEntry):
    """Write-once ledger entry for review executions.

    Created when a review is executed against actual outcomes.
    Separate aggregate from ReviewCycle because:
    1. Different write patterns (created days/weeks after cycle)
    2. Different event streams
    3. Potential for multiple reviews per cycle
    """
    review_id: str
    cycle_id: str
    review_type: ReviewType
    decision_snapshot: DecisionSnapshot
    actual_outcome: ActualOutcomeSnapshot
    variance: VarianceAnalysis
    verdict: ReviewVerdict
    rationale: str
    executed_at: datetime
    executed_by: str
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.review_id or not self.review_id.strip():
            raise ValueError("review_id cannot be empty.")
        if not self.cycle_id or not self.cycle_id.strip():
            raise ValueError("cycle_id cannot be empty.")
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale cannot be empty.")
        if not self.executed_by or not self.executed_by.strip():
            raise ValueError("executed_by cannot be empty.")

    @classmethod
    def determine_verdict(cls, variance: VarianceAnalysis, return_threshold: float = 0.0) -> ReviewVerdict:
        """Determines verdict from variance analysis."""
        if variance.overall_accuracy < 0.3:
            return ReviewVerdict.FAILED
        if variance.return_variance_bps > return_threshold:
            return ReviewVerdict.OUTPERFORMED
        if variance.return_variance_bps < -abs(return_threshold) * 2:
            return ReviewVerdict.UNDERPERFORMED
        if abs(variance.return_variance_bps) <= abs(return_threshold):
            return ReviewVerdict.MET_EXPECTATIONS
        return ReviewVerdict.INCONCLUSIVE
