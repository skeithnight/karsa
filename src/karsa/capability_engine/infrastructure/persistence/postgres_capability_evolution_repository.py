"""PostgresCapabilityEvolutionRepository -- Sprint-11. ADR-120, ADR-133."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.entities.evolution_attribution_ref import (
    EvolutionAttributionRef,
)
from karsa.capability_engine.domain.entities.evolution_finding import (
    EvolutionFinding,
)
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
)
from karsa.capability_engine.domain.value_objects.evolution_delta import (
    EvolutionDelta,
)
from karsa.capability_engine.domain.value_objects.evolution_evidence import (
    EvolutionEvidence,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_repository import (
    CapabilityEvolutionRepository,
)

TABLE = "capability_evolutions"


class PostgresCapabilityEvolutionRepository(CapabilityEvolutionRepository):
    """Write-once Postgres repository for capability evolution records.

    ADR-120: UNIQUE (capability_family_id, evaluation_id, trigger_type).
    ADR-133: ON CONFLICT DO NOTHING for idempotent inserts.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def save(self, record: CapabilityEvolution) -> bool:
        sql = f"""
            INSERT INTO {TABLE} (
                evolution_id, capability_family_id, evaluation_id,
                trigger_type, capability_version_id, capability_urn,
                attribution_id, review_id, evolution_type,
                delta, evidence, findings, attribution_refs,
                context_snapshot, evaluation_sequence,
                reviewed_at, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (capability_family_id, evaluation_id, trigger_type)
            DO NOTHING
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        record.evolution_id,
                        record.capability_family_id,
                        record.evaluation_id,
                        record.trigger_type,
                        record.capability_version_id,
                        record.capability_urn,
                        record.attribution_id,
                        record.review_id,
                        record.evolution_type,
                        json.dumps(self._serialize_delta(record.delta)),
                        json.dumps(self._serialize_evidence(record.evidence)),
                        json.dumps(
                            [self._serialize_finding(f) for f in record.findings]
                        ),
                        json.dumps(
                            [
                                self._serialize_attribution_ref(a)
                                for a in record.attribution_refs
                            ]
                        ),
                        json.dumps(
                            self._serialize_context_snapshot(
                                record.context_snapshot
                            )
                        ),
                        record.evaluation_sequence,
                        record.reviewed_at.isoformat()
                        if isinstance(record.reviewed_at, datetime)
                        else record.reviewed_at,
                        record.created_at,
                    ),
                )
                return cur.rowcount > 0
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e))

    def get_by_id(self, evolution_id: str) -> Optional[CapabilityEvolution]:
        sql = f"SELECT * FROM {TABLE} WHERE evolution_id = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (evolution_id,))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[CapabilityEvolution]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s AND evaluation_id = %s
            ORDER BY trigger_type
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id, evaluation_id))
            return [self._row_to_record(row) for row in cur.fetchall()]

    def get_by_family_evaluation_and_trigger(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[CapabilityEvolution]:
        sql = f"""
            SELECT * FROM {TABLE}
            WHERE capability_family_id = %s
              AND evaluation_id = %s
              AND trigger_type = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (capability_family_id, evaluation_id, trigger_type))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def list_evolutions(
        self, page: int = 1, size: int = 50
    ) -> List[CapabilityEvolution]:
        offset = (page - 1) * size
        sql = f"""
            SELECT * FROM {TABLE}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (size, offset))
            return [self._row_to_record(row) for row in cur.fetchall()]

    # ── Serialization helpers ────────────────────────────────────

    def _serialize_delta(self, delta: EvolutionDelta) -> Dict[str, Any]:
        return {
            "before_score": delta.before_score,
            "after_score": delta.after_score,
            "score_change_bps": delta.score_change_bps,
            "before_lifecycle_state": delta.before_lifecycle_state,
            "after_lifecycle_state": delta.after_lifecycle_state,
            "before_contract_fingerprint": delta.before_contract_fingerprint,
            "after_contract_fingerprint": delta.after_contract_fingerprint,
        }

    def _serialize_evidence(self, ev: EvolutionEvidence) -> Dict[str, Any]:
        return {
            "source_type": ev.source_type,
            "source_id": ev.source_id,
            "finding_ids": ev.finding_ids,
            "attribution_contribution_ids": ev.attribution_contribution_ids,
            "data_points": ev.data_points,
            "explanation": ev.explanation,
        }

    def _serialize_finding(self, f: EvolutionFinding) -> Dict[str, Any]:
        return {
            "finding_id": f.finding_id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "dimension": f.dimension,
            "description": f.description,
        }

    def _serialize_attribution_ref(
        self, a: EvolutionAttributionRef
    ) -> Dict[str, Any]:
        return {
            "contribution_id": a.contribution_id,
            "dimension": a.dimension,
            "contribution_bps": a.contribution_bps,
            "quality_score": a.quality_score,
        }

    def _serialize_context_snapshot(
        self, s: EvolutionContextSnapshot
    ) -> Dict[str, Any]:
        return {
            "capability_snapshot": s.capability_snapshot,
            "review_snapshot": s.review_snapshot,
            "attribution_snapshot": s.attribution_snapshot,
            "execution_snapshot": s.execution_snapshot,
            "snapshot_hash": s.snapshot_hash,
            "snapshot_source_versions": s.snapshot_source_versions,
        }

    # ── Deserialization helpers ──────────────────────────────────

    def _row_to_record(self, row: tuple) -> CapabilityEvolution:
        delta_dict = json.loads(row[9]) if isinstance(row[9], str) else row[9]
        evidence_dict = (
            json.loads(row[10]) if isinstance(row[10], str) else row[10]
        )
        findings_list = json.loads(row[11]) if isinstance(row[11], str) else row[11]
        attr_refs_list = (
            json.loads(row[12]) if isinstance(row[12], str) else row[12]
        )
        snapshot_dict = (
            json.loads(row[13]) if isinstance(row[13], str) else row[13]
        )

        return CapabilityEvolution(
            evolution_id=row[0],
            capability_family_id=row[1],
            evaluation_id=row[2],
            trigger_type=row[3],
            capability_version_id=row[4],
            capability_urn=row[5],
            attribution_id=row[6],
            review_id=row[7],
            evolution_type=row[8],
            delta=EvolutionDelta(**delta_dict),
            evidence=EvolutionEvidence(**evidence_dict),
            findings=[EvolutionFinding(**f) for f in findings_list],
            attribution_refs=[
                EvolutionAttributionRef(**a) for a in attr_refs_list
            ],
            context_snapshot=EvolutionContextSnapshot(**snapshot_dict),
            evaluation_sequence=row[14],
            reviewed_at=row[15],
            created_at=row[16],
        )
