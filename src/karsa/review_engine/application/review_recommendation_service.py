"""ReviewRecommendationService — Sprint-10.

Generates recommendations from findings.
Enforces ADR-111 size guardrails.
"""
import uuid
from datetime import datetime
from typing import List

from karsa.review_engine.domain.entities.review_finding import ReviewFinding
from karsa.review_engine.domain.entities.review_recommendation import ReviewRecommendation
from karsa.review_engine.domain.value_objects.enums import (
    FindingSeverity, RecommendationType, RecommendationPriority,
)
from karsa.review_engine.domain.aggregates.review_assessment import MAX_FINDINGS, MAX_RECOMMENDATIONS
from karsa.review_engine.domain.events.review_events import ReviewSizeExceededEvent


class ReviewRecommendationService:
    """Generates recommendations from findings. ADR-111 enforced."""

    SEVERITY_TO_RECOMMENDATION = {
        FindingSeverity.CRITICAL: (RecommendationType.ESCALATE, RecommendationPriority.URGENT),
        FindingSeverity.HIGH: (RecommendationType.ADJUST_ALLOCATION, RecommendationPriority.HIGH),
        FindingSeverity.MEDIUM: (RecommendationType.NO_ACTION, RecommendationPriority.MEDIUM),
        FindingSeverity.LOW: (RecommendationType.NO_ACTION, RecommendationPriority.LOW),
    }

    def generate_recommendations(
        self,
        findings: List[ReviewFinding],
        review_id: str,
    ) -> List[ReviewRecommendation]:
        """Generate recommendations from findings."""
        now = datetime.utcnow().isoformat()
        recommendations = []

        for finding in findings:
            rec_type, priority = self.SEVERITY_TO_RECOMMENDATION.get(
                finding.severity, (RecommendationType.NO_ACTION, RecommendationPriority.LOW)
            )
            recommendations.append(ReviewRecommendation(
                recommendation_id=f"urn:karsa:review:rec:{uuid.uuid4().hex[:16]}",
                finding_id=finding.finding_id,
                recommendation_type=rec_type,
                priority=priority,
                description=f"Recommendation for finding: {finding.description}",
                expected_impact=f"Address {finding.severity.value} severity finding",
                implementation_risk="Low" if finding.severity in (FindingSeverity.LOW, FindingSeverity.MEDIUM) else "Medium",
                created_at=now,
            ))

        return recommendations

    def check_size_guardrail(
        self,
        findings: List[ReviewFinding],
        recommendations: List[ReviewRecommendation],
        review_id: str,
    ) -> ReviewSizeExceededEvent:
        """Check ADR-111 size limits. Returns event if exceeded."""
        now = datetime.utcnow().isoformat()
        if len(findings) > MAX_FINDINGS or len(recommendations) > MAX_RECOMMENDATIONS:
            return ReviewSizeExceededEvent(
                event_id=str(uuid.uuid4()),
                review_id=review_id,
                finding_count=len(findings),
                recommendation_count=len(recommendations),
                limit_findings=MAX_FINDINGS,
                limit_recommendations=MAX_RECOMMENDATIONS,
                exceeded_at=now,
            )
        return None
