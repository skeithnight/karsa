"""ReviewProjectionService — Sprint-10 Wave-6.

Deterministic projection rebuilds from immutable sources.
Rebuilds exclusively from review_assessments JOIN review_version_registry.
Never queries upstream engines.
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List

from karsa.review_engine.infrastructure.repositories.review_projection_repository import ReviewProjectionRepository


class ReviewProjectionService:
    """Deterministic projection rebuilds. ADR-106 compliant.

    All projections rebuilt from:
    - review_assessments (immutable)
    - review_version_registry (canonical filter)

    Never queries:
    - Performance Engine
    - Attribution Engine
    - Decision Journal
    - Capability Engine
    """

    REBUILD_WORKER_REVIEWS = """
    INSERT INTO worker_review_projection (
        target_urn, total_reviews, avg_quality_score,
        total_findings, total_recommendations, last_reviewed
    )
    SELECT
        r.target_urn,
        COUNT(*) as total_reviews,
        AVG((r.review_quality->>'quality_score')::NUMERIC) as avg_quality_score,
        SUM(CASE WHEN jsonb_typeof(r.findings) = 'array' THEN jsonb_array_length(r.findings) ELSE 0 END) as total_findings,
        SUM(CASE WHEN jsonb_typeof(r.recommendations) = 'array' THEN jsonb_array_length(r.recommendations) ELSE 0 END) as total_recommendations,
        MAX(r.reviewed_at) as last_reviewed
    FROM review_assessments r
    JOIN review_version_registry v ON v.review_id = r.review_id
    WHERE v.review_status = 'CANONICAL'
      AND r.review_type = 'WORKER'
    GROUP BY r.target_urn
    ON CONFLICT (target_urn) DO UPDATE SET
        total_reviews = EXCLUDED.total_reviews,
        avg_quality_score = EXCLUDED.avg_quality_score,
        total_findings = EXCLUDED.total_findings,
        total_recommendations = EXCLUDED.total_recommendations,
        last_reviewed = EXCLUDED.last_reviewed
    """

    REBUILD_THESIS_REVIEWS = """
    INSERT INTO thesis_review_projection (
        thesis_urn, total_reviews, avg_quality_score, last_reviewed
    )
    SELECT
        r.target_urn,
        COUNT(*) as total_reviews,
        AVG((r.review_quality->>'quality_score')::NUMERIC) as avg_quality_score,
        MAX(r.reviewed_at) as last_reviewed
    FROM review_assessments r
    JOIN review_version_registry v ON v.review_id = r.review_id
    WHERE v.review_status = 'CANONICAL'
      AND r.review_type = 'THESIS'
    GROUP BY r.target_urn
    ON CONFLICT (thesis_urn) DO UPDATE SET
        total_reviews = EXCLUDED.total_reviews,
        avg_quality_score = EXCLUDED.avg_quality_score,
        last_reviewed = EXCLUDED.last_reviewed
    """

    REBUILD_REVIEW_COVERAGE = """
    INSERT INTO review_coverage_projection (
        decision_id, review_type, review_status, evaluated_at
    )
    SELECT
        r.evaluation_id,
        r.review_type,
        v.review_status,
        r.reviewed_at
    FROM review_assessments r
    JOIN review_version_registry v ON v.review_id = r.review_id
    WHERE v.review_status = 'CANONICAL'
    ON CONFLICT (decision_id) DO UPDATE SET
        review_status = EXCLUDED.review_status,
        evaluated_at = EXCLUDED.evaluated_at
    """

    def __init__(self, projection_repo: ReviewProjectionRepository):
        self.projection_repo = projection_repo

    def rebuild_all(self) -> Dict[str, int]:
        """Rebuild all projections from immutable sources."""
        results = {}
        with self.projection_repo.conn.cursor() as cur:
            results["worker_reviews"] = self._rebuild_worker_reviews(cur)
            results["thesis_reviews"] = self._rebuild_thesis_reviews(cur)
            results["capability_gaps"] = self._rebuild_capability_gaps(cur)
            results["review_coverage"] = self._rebuild_review_coverage(cur)
        return results

    def _rebuild_worker_reviews(self, cur) -> int:
        """Rebuild worker review projection."""
        cur.execute("TRUNCATE TABLE worker_review_projection")
        cur.execute(self.REBUILD_WORKER_REVIEWS)
        return cur.rowcount

    def _rebuild_thesis_reviews(self, cur) -> int:
        """Rebuild thesis review projection."""
        cur.execute("TRUNCATE TABLE thesis_review_projection")
        cur.execute(self.REBUILD_THESIS_REVIEWS)
        return cur.rowcount

    def _rebuild_capability_gaps(self, cur) -> int:
        """Rebuild capability gap projection from JSONB findings.

        Only includes CONCERN and RISK findings.
        Explodes JSONB deterministically.
        """
        cur.execute("TRUNCATE TABLE capability_gap_projection")

        # Get canonical reviews with findings
        cur.execute("""
            SELECT r.target_urn, r.findings
            FROM review_assessments r
            JOIN review_version_registry v ON v.review_id = r.review_id
            WHERE v.review_status = 'CANONICAL'
        """)
        rows = cur.fetchall()

        inserted = 0
        for target_urn, findings_json in rows:
            findings = findings_json if isinstance(findings_json, list) else json.loads(findings_json) if findings_json else []
            for finding in findings:
                finding_type = finding.get("finding_type", "")
                if finding_type in ("CONCERN", "RISK"):
                    cur.execute(
                        """
                        INSERT INTO capability_gap_projection (target_urn, gap_type, severity, description, identified_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (target_urn, gap_type) DO UPDATE SET
                            severity = EXCLUDED.severity,
                            description = EXCLUDED.description,
                            identified_at = EXCLUDED.identified_at
                        """,
                        (
                            target_urn,
                            finding_type,
                            finding.get("severity", "MEDIUM"),
                            finding.get("description", ""),
                            finding.get("created_at", datetime.utcnow().isoformat()),
                        )
                    )
                    inserted += 1

        return inserted

    def _rebuild_review_coverage(self, cur) -> int:
        """Rebuild review coverage projection."""
        cur.execute("TRUNCATE TABLE review_coverage_projection")
        cur.execute(self.REBUILD_REVIEW_COVERAGE)
        return cur.rowcount
