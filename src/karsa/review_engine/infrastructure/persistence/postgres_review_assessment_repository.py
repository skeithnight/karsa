"""PostgresReviewAssessmentRepository — Sprint-10.

Postgres implementation of ReviewAssessmentRepository.
Write-once, immutable. ADR-106.
"""
import json
from typing import List, Optional
from datetime import datetime
import psycopg

from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment
from karsa.review_engine.domain.entities.review_finding import ReviewFinding
from karsa.review_engine.domain.entities.review_recommendation import ReviewRecommendation
from karsa.review_engine.domain.value_objects.enums import (
    ReviewType, FindingType, FindingSeverity,
    RecommendationType, RecommendationPriority,
)
from karsa.review_engine.domain.value_objects.review_evidence import ReviewEvidence
from karsa.review_engine.domain.value_objects.review_summary import ReviewSummary
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.value_objects.review_context_snapshot import ReviewContextSnapshot
from karsa.review_engine.infrastructure.repositories.review_assessment_repository import ReviewAssessmentRepository


class PostgresReviewAssessmentRepository(ReviewAssessmentRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, record: ReviewAssessment) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO review_assessments (
                        review_id, evaluation_id, review_type, review_version,
                        target_urn, target_type, decision_id, attribution_id,
                        findings, recommendations, review_summary, review_quality,
                        context_snapshot, reviewed_at, reviewed_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (evaluation_id, review_type, review_version) DO NOTHING
                    """,
                    (
                        record.review_id,
                        record.evaluation_id,
                        record.review_type.value,
                        record.review_version,
                        record.target_urn,
                        record.target_type,
                        record.decision_id,
                        record.attribution_id,
                        json.dumps([self._serialize_finding(f) for f in record.findings]),
                        json.dumps([self._serialize_recommendation(r) for r in record.recommendations]),
                        json.dumps(self._serialize_summary(record.review_summary)),
                        json.dumps(self._serialize_quality(record.review_quality)),
                        json.dumps(self._serialize_snapshot(record.context_snapshot)),
                        record.reviewed_at,
                        record.reviewed_by,
                    )
                )
                return cur.rowcount > 0
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_by_id(self, review_id: str) -> Optional[ReviewAssessment]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM review_assessments WHERE review_id = %s", (review_id,))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def get_by_evaluation_and_type(self, evaluation_id: str, review_type: str) -> Optional[ReviewAssessment]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM review_assessments WHERE evaluation_id = %s AND review_type = %s",
                (evaluation_id, review_type)
            )
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def get_by_target_urn(self, target_urn: str) -> List[ReviewAssessment]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM review_assessments WHERE target_urn = %s ORDER BY created_at DESC", (target_urn,))
            return [self._row_to_record(row) for row in cur.fetchall()]

    def list_reviews(self, page: int = 1, size: int = 50) -> List[ReviewAssessment]:
        offset = (page - 1) * size
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM review_assessments ORDER BY created_at DESC LIMIT %s OFFSET %s", (size, offset))
            return [self._row_to_record(row) for row in cur.fetchall()]

    def _row_to_record(self, row) -> ReviewAssessment:
        findings_data = json.loads(row[8]) if isinstance(row[8], str) else row[8]
        recs_data = json.loads(row[9]) if isinstance(row[9], str) else row[9]
        summary_data = json.loads(row[10]) if isinstance(row[10], str) else row[10]
        quality_data = json.loads(row[11]) if isinstance(row[11], str) else row[11]
        snapshot_data = json.loads(row[12]) if isinstance(row[12], str) else row[12]

        findings = [self._deserialize_finding(f) for f in findings_data]
        recommendations = [self._deserialize_recommendation(r) for r in recs_data]
        summary = self._deserialize_summary(summary_data)
        quality = self._deserialize_quality(quality_data)
        snapshot = self._deserialize_snapshot(snapshot_data)

        return ReviewAssessment(
            review_id=row[0],
            evaluation_id=row[1],
            review_type=ReviewType(row[2]),
            review_version=row[3],
            target_urn=row[4],
            target_type=row[5],
            decision_id=row[6],
            attribution_id=row[7],
            findings=findings,
            recommendations=recommendations,
            review_summary=summary,
            review_quality=quality,
            context_snapshot=snapshot,
            reviewed_at=row[13],
            reviewed_by=row[14],
            created_at=row[15],
        )

    def _serialize_finding(self, f: ReviewFinding) -> dict:
        return {
            "finding_id": f.finding_id,
            "dimension": f.dimension,
            "finding_type": f.finding_type.value,
            "severity": f.severity.value,
            "description": f.description,
            "evidence": {
                "source_type": f.evidence.source_type,
                "source_id": f.evidence.source_id,
                "data_points": f.evidence.data_points,
                "explanation": f.evidence.explanation,
            },
            "confidence": f.confidence,
            "created_at": f.created_at,
        }

    def _deserialize_finding(self, d: dict) -> ReviewFinding:
        ev = d.get("evidence", {})
        return ReviewFinding(
            finding_id=d["finding_id"],
            dimension=d["dimension"],
            finding_type=FindingType(d["finding_type"]),
            severity=FindingSeverity(d["severity"]),
            description=d["description"],
            evidence=ReviewEvidence(**ev),
            confidence=d["confidence"],
            created_at=d.get("created_at", ""),
        )

    def _serialize_recommendation(self, r: ReviewRecommendation) -> dict:
        return {
            "recommendation_id": r.recommendation_id,
            "finding_id": r.finding_id,
            "recommendation_type": r.recommendation_type.value,
            "priority": r.priority.value,
            "description": r.description,
            "expected_impact": r.expected_impact,
            "implementation_risk": r.implementation_risk,
            "created_at": r.created_at,
        }

    def _deserialize_recommendation(self, d: dict) -> ReviewRecommendation:
        return ReviewRecommendation(
            recommendation_id=d["recommendation_id"],
            finding_id=d["finding_id"],
            recommendation_type=RecommendationType(d["recommendation_type"]),
            priority=RecommendationPriority(d["priority"]),
            description=d["description"],
            expected_impact=d["expected_impact"],
            implementation_risk=d["implementation_risk"],
            created_at=d.get("created_at", ""),
        )

    def _serialize_summary(self, s: ReviewSummary) -> dict:
        return {
            "total_findings": s.total_findings,
            "findings_by_severity": s.findings_by_severity,
            "total_recommendations": s.total_recommendations,
            "recommendations_by_priority": s.recommendations_by_priority,
            "overall_assessment": s.overall_assessment,
            "confidence": s.confidence,
            "explanation": s.explanation,
        }

    def _deserialize_summary(self, d: dict) -> ReviewSummary:
        return ReviewSummary(**d)

    def _serialize_quality(self, q: ReviewQuality) -> dict:
        return {
            "quality_score": q.quality_score,
            "data_completeness": q.data_completeness,
            "analysis_depth": q.analysis_depth,
            "missing_data": q.missing_data,
        }

    def _deserialize_quality(self, d: dict) -> ReviewQuality:
        return ReviewQuality(**d)

    def _serialize_snapshot(self, s: ReviewContextSnapshot) -> dict:
        return {
            "evaluation_snapshot": s.evaluation_snapshot,
            "attribution_snapshot": s.attribution_snapshot,
            "decision_snapshot": s.decision_snapshot,
            "journal_snapshot": s.journal_snapshot,
            "regime_snapshot": s.regime_snapshot,
            "snapshot_hash": s.snapshot_hash,
        }

    def _deserialize_snapshot(self, d: dict) -> ReviewContextSnapshot:
        return ReviewContextSnapshot(**d)
