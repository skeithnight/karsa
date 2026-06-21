"""ReviewAssessment aggregate — Sprint-10.

Write-once immutable ledger entry. ADR-106, ADR-111.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from karsa.review_engine.domain.entities.review_finding import ReviewFinding
from karsa.review_engine.domain.entities.review_recommendation import ReviewRecommendation
from karsa.review_engine.domain.value_objects.enums import ReviewType
from karsa.review_engine.domain.value_objects.review_summary import ReviewSummary
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.value_objects.review_context_snapshot import ReviewContextSnapshot
from karsa.review_engine.domain.exceptions import InvalidReviewError, SizeGuardrailExceededError


# ADR-111: Size guardrails
MAX_FINDINGS = 100
MAX_RECOMMENDATIONS = 50


class ImmutableLedgerEntry:
    """Base class for write-once immutable ledger entries. ADR-106."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise AttributeError(f"Cannot modify '{name}' of an immutable ledger entry.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise AttributeError("Cannot delete attribute of an immutable ledger entry.")


@dataclass
class ReviewAssessment(ImmutableLedgerEntry):
    """Write-once review assessment. ADR-106.

    Business identity: (evaluation_id, review_type, review_version)
    Technical identity: review_id

    Status is NOT stored here.
    Canonical governance is handled exclusively by review_version_registry — ADR-107.
    """
    review_id: str
    evaluation_id: str
    review_type: ReviewType
    review_version: str
    target_urn: str
    target_type: str
    decision_id: str
    attribution_id: str
    findings: List[ReviewFinding]
    recommendations: List[ReviewRecommendation]
    review_summary: ReviewSummary
    review_quality: ReviewQuality
    context_snapshot: ReviewContextSnapshot
    reviewed_at: datetime
    reviewed_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if not self.review_id:
            raise InvalidReviewError("review_id required")
        if not self.evaluation_id:
            raise InvalidReviewError("evaluation_id required")
        if not self.target_urn:
            raise InvalidReviewError("target_urn required")
        if not self.decision_id:
            raise InvalidReviewError("decision_id required")
        if not self.reviewed_by:
            raise InvalidReviewError("reviewed_by required")

        # ADR-111: Size guardrails
        if len(self.findings) > MAX_FINDINGS:
            raise SizeGuardrailExceededError(
                f"Findings count {len(self.findings)} exceeds maximum {MAX_FINDINGS}"
            )
        if len(self.recommendations) > MAX_RECOMMENDATIONS:
            raise SizeGuardrailExceededError(
                f"Recommendations count {len(self.recommendations)} exceeds maximum {MAX_RECOMMENDATIONS}"
            )

        # Validate child entities
        for f in self.findings:
            f._validate()
        for r in self.recommendations:
            r._validate()
