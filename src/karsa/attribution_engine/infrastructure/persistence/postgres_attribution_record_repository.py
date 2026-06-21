"""PostgresAttributionRecordRepository — Sprint-09.

Postgres implementation of AttributionRecordRepository.
Write-once, immutable. ADR-093.
"""
import json
from typing import List, Optional
from datetime import datetime
import psycopg

from karsa.attribution_engine.domain.aggregates.attribution_record import AttributionRecord
from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary
from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence
from karsa.attribution_engine.domain.value_objects.interaction_effect import InteractionEffect
from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot
from karsa.attribution_engine.infrastructure.repositories.attribution_record_repository import AttributionRecordRepository


class PostgresAttributionRecordRepository(AttributionRecordRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, record: AttributionRecord) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO attribution_records (
                        attribution_id, evaluation_id, algorithm_version,
                        decision_id, evaluation_horizon_days, target_urn, target_type,
                        total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                        contributions, attribution_summary, attribution_quality,
                        quality_provenance, context_snapshot,
                        source_request_id, attributed_at, attributed_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (evaluation_id, algorithm_version) DO NOTHING
                    """,
                    (
                        record.attribution_id,
                        record.evaluation_id,
                        record.algorithm_version,
                        record.decision_id,
                        record.evaluation_horizon_days,
                        record.target_urn,
                        record.target_type,
                        record.total_realized_return_bps,
                        record.total_expected_return_bps,
                        record.total_variance_bps,
                        json.dumps([self._serialize_contribution(c) for c in record.contributions]),
                        json.dumps(self._serialize_summary(record.attribution_summary)),
                        json.dumps(self._serialize_quality(record.attribution_quality)),
                        json.dumps(record.quality_provenance),
                        json.dumps(self._serialize_snapshot(record.context_snapshot)),
                        record.source_request_id,
                        record.attributed_at,
                        record.attributed_by,
                    )
                )
                return cur.rowcount > 0
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_by_id(self, attribution_id: str) -> Optional[AttributionRecord]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM attribution_records WHERE attribution_id = %s", (attribution_id,))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def get_by_evaluation_and_algorithm(self, evaluation_id: str, algorithm_version: str) -> Optional[AttributionRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM attribution_records WHERE evaluation_id = %s AND algorithm_version = %s",
                (evaluation_id, algorithm_version)
            )
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def get_by_target_urn(self, target_urn: str) -> List[AttributionRecord]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM attribution_records WHERE target_urn = %s ORDER BY created_at DESC", (target_urn,))
            return [self._row_to_record(row) for row in cur.fetchall()]

    def list_attributions(self, page: int = 1, size: int = 50) -> List[AttributionRecord]:
        offset = (page - 1) * size
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM attribution_records ORDER BY created_at DESC LIMIT %s OFFSET %s", (size, offset))
            return [self._row_to_record(row) for row in cur.fetchall()]

    def _row_to_record(self, row) -> AttributionRecord:
        # Column order matches table definition
        contributions_data = json.loads(row[10]) if isinstance(row[10], str) else row[10]
        summary_data = json.loads(row[11]) if isinstance(row[11], str) else row[11]
        quality_data = json.loads(row[12]) if isinstance(row[12], str) else row[12]
        provenance_data = json.loads(row[13]) if isinstance(row[13], str) else row[13]
        snapshot_data = json.loads(row[14]) if isinstance(row[14], str) else row[14]

        contributions = [self._deserialize_contribution(c) for c in contributions_data]
        summary = self._deserialize_summary(summary_data)
        quality = self._deserialize_quality(quality_data)
        snapshot = self._deserialize_snapshot(snapshot_data)

        return AttributionRecord(
            attribution_id=row[0],
            evaluation_id=row[1],
            algorithm_version=row[2],
            decision_id=row[3],
            evaluation_horizon_days=row[4],
            target_urn=row[5],
            target_type=row[6],
            total_realized_return_bps=float(row[7]),
            total_expected_return_bps=float(row[8]),
            total_variance_bps=float(row[9]),
            contributions=contributions,
            attribution_summary=summary,
            attribution_quality=quality,
            quality_provenance=provenance_data,
            context_snapshot=snapshot,
            source_request_id=row[15],
            attributed_at=row[16],
            attributed_by=row[17],
            created_at=row[18],
        )

    def _serialize_contribution(self, c: AttributionContribution) -> dict:
        return {
            "contribution_id": c.contribution_id,
            "dimension": c.dimension,
            "target_urn": c.target_urn,
            "evidence": {"source_type": c.evidence.source_type, "source_id": c.evidence.source_id, "data_points": c.evidence.data_points, "explanation": c.evidence.explanation},
            "contribution_bps": c.contribution_bps,
            "contribution_pct": c.contribution_pct,
            "quality_score": c.quality_score,
            "quality_provenance": c.quality_provenance,
            "interaction_effects": [{"dimension_a": ie.dimension_a, "dimension_b": ie.dimension_b, "shared_effect_bps": ie.shared_effect_bps, "explanation": ie.explanation} for ie in c.interaction_effects],
            "created_at": c.created_at,
        }

    def _deserialize_contribution(self, d: dict) -> AttributionContribution:
        evidence = d.get("evidence", {})
        interactions = [InteractionEffect(**ie) for ie in d.get("interaction_effects", [])]
        return AttributionContribution(
            contribution_id=d["contribution_id"],
            dimension=d["dimension"],
            target_urn=d["target_urn"],
            evidence=AttributionEvidence(**evidence),
            contribution_bps=d["contribution_bps"],
            contribution_pct=d["contribution_pct"],
            quality_score=d["quality_score"],
            quality_provenance=d.get("quality_provenance", {"source": "SYSTEM_DEFAULT", "score": 0.5}),
            interaction_effects=interactions,
            created_at=d.get("created_at", ""),
        )

    def _serialize_summary(self, s: AttributionSummary) -> dict:
        return {
            "total_variance_bps": s.total_variance_bps,
            "thesis_contribution_bps": s.thesis_contribution_bps,
            "execution_contribution_bps": s.execution_contribution_bps,
            "allocation_contribution_bps": s.allocation_contribution_bps,
            "regime_contribution_bps": s.regime_contribution_bps,
            "residual_bps": s.residual_bps,
            "interaction_effects_bps": s.interaction_effects_bps,
            "attribution_confidence": s.attribution_confidence,
            "explanation": s.explanation,
            "interaction_effects": [{"dimension_a": ie.dimension_a, "dimension_b": ie.dimension_b, "shared_effect_bps": ie.shared_effect_bps, "explanation": ie.explanation} for ie in s.interaction_effects],
        }

    def _deserialize_summary(self, d: dict) -> AttributionSummary:
        interactions = [InteractionEffect(**ie) for ie in d.get("interaction_effects", [])]
        return AttributionSummary(
            total_variance_bps=d["total_variance_bps"],
            thesis_contribution_bps=d["thesis_contribution_bps"],
            execution_contribution_bps=d["execution_contribution_bps"],
            allocation_contribution_bps=d["allocation_contribution_bps"],
            regime_contribution_bps=d["regime_contribution_bps"],
            residual_bps=d["residual_bps"],
            interaction_effects_bps=d["interaction_effects_bps"],
            attribution_confidence=d["attribution_confidence"],
            explanation=d["explanation"],
            interaction_effects=interactions,
        )

    def _serialize_quality(self, q: AttributionQuality) -> dict:
        return {"quality_score": q.quality_score, "data_completeness": q.data_completeness, "decomposition_confidence": q.decomposition_confidence, "missing_data": q.missing_data}

    def _deserialize_quality(self, d: dict) -> AttributionQuality:
        return AttributionQuality(**d)

    def _serialize_snapshot(self, s: AttributionContextSnapshot) -> dict:
        return {"evaluation_snapshot": s.evaluation_snapshot, "decision_snapshot": s.decision_snapshot, "journal_snapshot": s.journal_snapshot, "regime_snapshot": s.regime_snapshot, "snapshot_hash": s.snapshot_hash}

    def _deserialize_snapshot(self, d: dict) -> AttributionContextSnapshot:
        return AttributionContextSnapshot(**d)
