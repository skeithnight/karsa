"""ReviewExecutionService — Sprint-10.

Main orchestrator for review execution.
Transaction boundary: review_assessments + review_version_registry + review_outbox
"""
import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment
from karsa.review_engine.domain.entities.review_finding import ReviewFinding
from karsa.review_engine.domain.entities.review_recommendation import ReviewRecommendation
from karsa.review_engine.domain.value_objects.enums import (
    ReviewType, FindingType, FindingSeverity, QualitySource,
)
from karsa.review_engine.domain.value_objects.review_evidence import ReviewEvidence
from karsa.review_engine.domain.value_objects.review_summary import ReviewSummary
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.value_objects.review_context_snapshot import ReviewContextSnapshot
from karsa.review_engine.infrastructure.repositories.review_assessment_repository import ReviewAssessmentRepository
from karsa.review_engine.infrastructure.repositories.review_version_registry_repository import (
    ReviewVersionRegistryRepository, VersionRegistryEntry,
)
from karsa.review_engine.infrastructure.repositories.review_outbox_repository import OutboxEvent
from karsa.review_engine.application.review_quality_gate_service import ReviewQualityGateService
from karsa.review_engine.application.review_recommendation_service import ReviewRecommendationService
from karsa.review_engine.application.review_versioning_service import ReviewVersioningService


class ReviewExecutionService:
    """Main orchestrator for review execution.

    Transaction boundary:
    BEGIN
      1. Build context snapshot
      2. Generate findings
      3. Generate recommendations
      4. Apply size guardrail
      5. Compute quality
      6. Apply quality gate
      7. Save ReviewAssessment
      8. Register canonical version
      9. Save outbox events
    COMMIT
    """

    def __init__(
        self,
        assessment_repo: ReviewAssessmentRepository,
        registry_repo: ReviewVersionRegistryRepository,
        outbox_repo,
        quality_gate_service: ReviewQualityGateService,
        recommendation_service: ReviewRecommendationService,
        versioning_service: ReviewVersioningService,
    ):
        self.assessment_repo = assessment_repo
        self.registry_repo = registry_repo
        self.outbox_repo = outbox_repo
        self.quality_gate = quality_gate_service
        self.recommendation_service = recommendation_service
        self.versioning_service = versioning_service

    def execute_review(
        self,
        evaluation_event: Dict[str, Any],
        attribution_event: Optional[Dict[str, Any]] = None,
        review_version: str = "v1.0",
    ) -> ReviewAssessment:
        """Execute a review from performance evaluation and attribution events."""
        evaluation_id = evaluation_event["evaluation_id"]
        review_type_str = evaluation_event.get("review_type", "WORKER")
        review_type = ReviewType(review_type_str)
        target_urn = evaluation_event["target_urn"]

        # Build context snapshot
        context_snapshot = self._build_context_snapshot(evaluation_event, attribution_event)

        # Generate findings
        findings = self._generate_findings(evaluation_id, target_urn, evaluation_event)

        # Generate recommendations
        recommendations = self.recommendation_service.generate_recommendations(findings, f"review-{uuid.uuid4().hex[:8]}")

        # Check size guardrail (ADR-111)
        size_exceeded = self.recommendation_service.check_size_guardrail(
            findings, recommendations, f"review-{uuid.uuid4().hex[:8]}"
        )
        if size_exceeded:
            # Truncate to limits
            findings = findings[:100]
            recommendations = recommendations[:50]

        # Compute quality
        quality = self.quality_gate.evaluate_quality(
            quality_score=evaluation_event.get("quality_score", 0.5),
            data_completeness=evaluation_event.get("data_completeness", 0.8),
            analysis_depth=evaluation_event.get("analysis_depth", 0.7),
            missing_data=evaluation_event.get("missing_data", []),
        )

        # Build summary
        summary = self._build_summary(findings, recommendations)

        # Create review assessment
        review_id = f"urn:karsa:review:{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        assessment = ReviewAssessment(
            review_id=review_id,
            evaluation_id=evaluation_id,
            review_type=review_type,
            review_version=review_version,
            target_urn=target_urn,
            target_type=evaluation_event.get("target_type", "WORKER"),
            decision_id=evaluation_event.get("decision_id", ""),
            attribution_id=attribution_event.get("attribution_id", "") if attribution_event else "",
            findings=findings,
            recommendations=recommendations,
            review_summary=summary,
            review_quality=quality,
            context_snapshot=context_snapshot,
            reviewed_at=now,
            reviewed_by="review-engine",
        )

        # Save assessment
        inserted = self.assessment_repo.save(assessment)
        if not inserted:
            existing = self.assessment_repo.get_by_evaluation_and_type(evaluation_id, review_type.value)
            if existing:
                return existing

        # Register canonical version
        self.versioning_service.register_canonical(
            evaluation_id, review_type.value, review_version, review_id
        )

        # Apply quality gate and publish events
        self._apply_quality_gate(assessment, quality, size_exceeded)

        return assessment

    def _build_context_snapshot(
        self,
        evaluation_event: Dict[str, Any],
        attribution_event: Optional[Dict[str, Any]],
    ) -> ReviewContextSnapshot:
        """Build immutable context snapshot."""
        evaluation_snapshot = {
            "evaluation_id": evaluation_event["evaluation_id"],
            "total_realized_return_bps": evaluation_event.get("total_realized_return_bps", 0),
            "total_expected_return_bps": evaluation_event.get("total_expected_return_bps", 0),
        }
        attribution_snapshot = {}
        if attribution_event:
            attribution_snapshot = {
                "attribution_id": attribution_event.get("attribution_id", ""),
                "quality_score": attribution_event.get("quality_score", 0),
            }
        decision_snapshot = evaluation_event.get("decision_snapshot", {})
        regime_snapshot = evaluation_event.get("regime_context", {})

        snapshot_data = {
            "evaluation_snapshot": evaluation_snapshot,
            "attribution_snapshot": attribution_snapshot,
            "decision_snapshot": decision_snapshot,
            "regime_snapshot": regime_snapshot,
        }
        snapshot_hash = hashlib.sha256(
            json.dumps(snapshot_data, sort_keys=True, default=str).encode()
        ).hexdigest()

        return ReviewContextSnapshot(
            evaluation_snapshot=evaluation_snapshot,
            attribution_snapshot=attribution_snapshot,
            decision_snapshot=decision_snapshot,
            regime_snapshot=regime_snapshot,
            snapshot_hash=snapshot_hash,
        )

    def _generate_findings(
        self,
        evaluation_id: str,
        target_urn: str,
        evaluation_event: Dict[str, Any],
    ) -> List[ReviewFinding]:
        """Generate findings from evaluation data."""
        now = datetime.utcnow().isoformat()
        findings = []
        variance = evaluation_event.get("total_variance_bps", 0)

        # Thesis dimension
        findings.append(ReviewFinding(
            finding_id=f"urn:karsa:finding:{uuid.uuid4().hex[:16]}",
            dimension="THESIS",
            finding_type=FindingType.OBSERVATION,
            severity=FindingSeverity.MEDIUM if abs(variance) > 20 else FindingSeverity.LOW,
            description=f"Thesis evaluation: variance {variance:.1f} bps",
            evidence=ReviewEvidence(
                source_type="PERFORMANCE_ENGINE",
                source_id=evaluation_id,
                data_points={"variance": variance},
                explanation="Performance variance from expected",
            ),
            confidence=0.7,
            created_at=now,
        ))

        # Execution dimension
        findings.append(ReviewFinding(
            finding_id=f"urn:karsa:finding:{uuid.uuid4().hex[:16]}",
            dimension="EXECUTION",
            finding_type=FindingType.OBSERVATION,
            severity=FindingSeverity.LOW,
            description="Execution quality assessment",
            evidence=ReviewEvidence(
                source_type="PERFORMANCE_ENGINE",
                source_id=evaluation_id,
                data_points={},
                explanation="Execution quality from performance evaluation",
            ),
            confidence=0.6,
            created_at=now,
        ))

        return findings

    def _build_summary(
        self,
        findings: List[ReviewFinding],
        recommendations: List[ReviewRecommendation],
    ) -> ReviewSummary:
        """Build review summary."""
        severity_counts = {}
        for f in findings:
            severity_counts[f.severity.value] = severity_counts.get(f.severity.value, 0) + 1

        priority_counts = {}
        for r in recommendations:
            priority_counts[r.priority.value] = priority_counts.get(r.priority.value, 0) + 0

        overall = "NEUTRAL"
        if any(f.severity == FindingSeverity.CRITICAL for f in findings):
            overall = "NEGATIVE"
        elif all(f.severity == FindingSeverity.LOW for f in findings):
            overall = "POSITIVE"

        return ReviewSummary(
            total_findings=len(findings),
            findings_by_severity=severity_counts,
            total_recommendations=len(recommendations),
            recommendations_by_priority=priority_counts,
            overall_assessment=overall,
            confidence=0.7,
            explanation=f"Review of {len(findings)} findings with {len(recommendations)} recommendations",
        )

    def _apply_quality_gate(
        self,
        assessment: ReviewAssessment,
        quality: ReviewQuality,
        size_exceeded,
    ) -> None:
        """Apply quality gate and publish events."""
        now = datetime.utcnow().isoformat()

        if quality.is_sufficient:
            event = self.quality_gate.create_completed_event(
                event_id=str(uuid.uuid4()),
                review_id=assessment.review_id,
                evaluation_id=assessment.evaluation_id,
                review_type=assessment.review_type.value,
                review_version=assessment.review_version,
                target_urn=assessment.target_urn,
                review_summary={
                    "total_findings": assessment.review_summary.total_findings,
                    "overall_assessment": assessment.review_summary.overall_assessment,
                },
                review_quality={
                    "quality_score": quality.quality_score,
                    "data_completeness": quality.data_completeness,
                },
                finding_count=len(assessment.findings),
                recommendation_count=len(assessment.recommendations),
                reviewed_at=now,
            )
            self.outbox_repo.save_event(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type="ReviewCompletedEvent",
                payload=json.dumps(event.__dict__, default=str),
                aggregate_id=assessment.review_id,
                status="PENDING",
                created_at=datetime.utcnow(),
            ))
        else:
            event = self.quality_gate.create_deferred_event(
                event_id=str(uuid.uuid4()),
                evaluation_id=assessment.evaluation_id,
                review_type=assessment.review_type.value,
                quality_score=quality.quality_score,
                missing_data=quality.missing_data,
                deferred_at=now,
            )
            self.outbox_repo.save_event(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type="ReviewDeferredEvent",
                payload=json.dumps(event.__dict__, default=str),
                aggregate_id=assessment.review_id,
                status="PENDING",
                created_at=datetime.utcnow(),
            ))

        # Emit size exceeded event if needed
        if size_exceeded:
            self.outbox_repo.save_event(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type="ReviewSizeExceededEvent",
                payload=json.dumps(size_exceeded.__dict__, default=str),
                aggregate_id=assessment.review_id,
                status="PENDING",
                created_at=datetime.utcnow(),
            ))
