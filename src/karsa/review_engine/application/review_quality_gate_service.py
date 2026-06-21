"""ReviewQualityGateService — Sprint-10.

Pure domain logic. No persistence.
Determines whether review passes quality threshold.
"""
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.events.review_events import (
    ReviewCompletedEvent,
    ReviewDeferredEvent,
)


QUALITY_THRESHOLD = 0.3


class ReviewQualityGateService:
    """Quality gate for review assessments. ADR-099 pattern."""

    def evaluate_quality(
        self,
        quality_score: float,
        data_completeness: float,
        analysis_depth: float,
        missing_data: list,
    ) -> ReviewQuality:
        """Compute ReviewQuality from inputs."""
        return ReviewQuality(
            quality_score=quality_score,
            data_completeness=data_completeness,
            analysis_depth=analysis_depth,
            missing_data=missing_data,
        )

    def should_complete(self, quality: ReviewQuality) -> bool:
        """Determine if review passes quality gate."""
        return quality.is_sufficient

    def create_completed_event(
        self,
        event_id: str,
        review_id: str,
        evaluation_id: str,
        review_type: str,
        review_version: str,
        target_urn: str,
        review_summary: dict,
        review_quality: dict,
        finding_count: int,
        recommendation_count: int,
        reviewed_at: str,
    ) -> ReviewCompletedEvent:
        """Create ReviewCompletedEvent for passing reviews."""
        return ReviewCompletedEvent(
            event_id=event_id,
            review_id=review_id,
            evaluation_id=evaluation_id,
            review_type=review_type,
            review_version=review_version,
            target_urn=target_urn,
            review_summary=review_summary,
            review_quality=review_quality,
            finding_count=finding_count,
            recommendation_count=recommendation_count,
            reviewed_at=reviewed_at,
        )

    def create_deferred_event(
        self,
        event_id: str,
        evaluation_id: str,
        review_type: str,
        quality_score: float,
        missing_data: list,
        deferred_at: str,
    ) -> ReviewDeferredEvent:
        """Create ReviewDeferredEvent for failing reviews."""
        return ReviewDeferredEvent(
            event_id=event_id,
            evaluation_id=evaluation_id,
            review_type=review_type,
            reason=f"Quality score {quality_score:.2f} below threshold {QUALITY_THRESHOLD}",
            quality_score=quality_score,
            missing_data=missing_data,
            deferred_at=deferred_at,
        )
