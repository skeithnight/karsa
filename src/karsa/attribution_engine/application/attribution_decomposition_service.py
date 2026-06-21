"""AttributionDecompositionService — Sprint-09.

Core attribution service. Consumes evaluation events, produces attribution records.
ADR-095: Contributing-factor model (non-orthogonal decomposition).
ADR-098: Graceful degradation for missing context.
ADR-099: Quality gate.
ADR-100: Upstream quality consumption.
ADR-101: Transitional quality provider.
ADR-102: Canonical attribution governance via registry.
"""
import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from karsa.attribution_engine.domain.aggregates.attribution_record import AttributionRecord
from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary
from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence
from karsa.attribution_engine.domain.value_objects.interaction_effect import InteractionEffect
from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot
from karsa.attribution_engine.domain.value_objects.enums import AttributionDimension, QualitySource
from karsa.attribution_engine.domain.events.attribution_events import (
    AttributionDecompositionCompletedEvent,
    AttributionDecompositionDeferredEvent,
    AttributionCanonicalVersionChangedEvent,
)
from karsa.attribution_engine.infrastructure.repositories.attribution_record_repository import AttributionRecordRepository
from karsa.attribution_engine.infrastructure.repositories.attribution_version_registry_repository import (
    AttributionVersionRegistryRepository, VersionRegistryEntry,
)
from karsa.attribution_engine.infrastructure.repositories.attribution_outbox_repository import OutboxEvent


class AttributionDecompositionService:
    """Core attribution service.

    Transaction boundary:
    BEGIN
      1. Build context snapshot
      2. Compute contributions per dimension
      3. Compute residual
      4. Compute interaction effects
      5. Compute quality
      6. Apply quality gate
      7. Supersede previous canonical (if exists)
      8. Save AttributionRecord
      9. Save VersionRegistryEntry
      10. Save OutboxEvent(s)
    COMMIT
    """

    def __init__(
        self,
        record_repo: AttributionRecordRepository,
        registry_repo: AttributionVersionRegistryRepository,
        outbox_repo,
    ):
        self.record_repo = record_repo
        self.registry_repo = registry_repo
        self.outbox_repo = outbox_repo

    def decompose_evaluation(
        self,
        evaluation_event: Dict[str, Any],
        algorithm_version: str = "v1.0",
    ) -> AttributionRecord:
        """Main entry point. Consumes PerformanceEvaluationCompletedEvent payload."""
        evaluation_id = evaluation_event["evaluation_id"]
        decision_id = evaluation_event["decision_id"]
        evaluation_horizon_days = evaluation_event.get("evaluation_horizon_days", 30)
        target_urn = evaluation_event["target_urn"]
        target_type = evaluation_event.get("target_type", "DECISION")

        # Build context snapshot (ADR-097: immutable context for replay)
        context_snapshot = self._build_context_snapshot(evaluation_event)

        # Compute contributions (ADR-095)
        contributions = self._compute_contributions(evaluation_event, context_snapshot)
        total_variance = evaluation_event["total_variance_bps"]

        # Compute residual
        residual_bps = self._compute_residual(total_variance, contributions)

        # Compute interaction effects
        interaction_effects = self._compute_interaction_effects(contributions)

        # Compute summary
        summary = self._compute_summary(total_variance, contributions, residual_bps, interaction_effects)

        # Compute quality (ADR-099)
        quality = self._compute_quality(evaluation_event, contributions)

        # Build quality provenance (ADR-105)
        quality_provenance = self._build_quality_provenance(evaluation_event)

        # Create attribution record
        attribution_id = f"urn:karsa:attribution:{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        record = AttributionRecord(
            attribution_id=attribution_id,
            evaluation_id=evaluation_id,
            algorithm_version=algorithm_version,
            decision_id=decision_id,
            evaluation_horizon_days=evaluation_horizon_days,
            target_urn=target_urn,
            target_type=target_type,
            total_realized_return_bps=evaluation_event["total_realized_return_bps"],
            total_expected_return_bps=evaluation_event["total_expected_return_bps"],
            total_variance_bps=total_variance,
            contributions=contributions,
            attribution_summary=summary,
            attribution_quality=quality,
            quality_provenance=quality_provenance,
            context_snapshot=context_snapshot,
            source_request_id=evaluation_event.get("source_request_id", ""),
            attributed_at=now,
            attributed_by="attribution-engine",
        )

        # Transaction boundary: save record + registry + outbox atomically
        inserted = self.record_repo.save(record)

        if not inserted:
            # Duplicate — return existing
            existing = self.record_repo.get_by_evaluation_and_algorithm(evaluation_id, algorithm_version)
            if existing:
                return existing

        # Supersede previous canonical (ADR-102)
        self.registry_repo.supersede_previous(evaluation_id, algorithm_version, attribution_id)

        # Save registry entry
        registry_entry = VersionRegistryEntry(
            version_id=str(uuid.uuid4()),
            evaluation_id=evaluation_id,
            algorithm_version=algorithm_version,
            attribution_id=attribution_id,
            attribution_status="CANONICAL",
            superseded_by=None,
            created_at=now,
            updated_at=now,
        )
        self.registry_repo.save(registry_entry)

        # Apply quality gate and publish events (ADR-099)
        self._apply_quality_gate(record, quality)

        return record

    def _build_context_snapshot(self, event: Dict[str, Any]) -> AttributionContextSnapshot:
        """Build immutable context snapshot from event data. ADR-097."""
        evaluation_snapshot = {
            "evaluation_id": event["evaluation_id"],
            "total_realized_return_bps": event["total_realized_return_bps"],
            "total_expected_return_bps": event["total_expected_return_bps"],
            "total_variance_bps": event["total_variance_bps"],
        }
        decision_snapshot = event.get("decision_snapshot", {})
        regime_snapshot = event.get("regime_context", {})

        snapshot_data = {
            "evaluation_snapshot": evaluation_snapshot,
            "decision_snapshot": decision_snapshot,
            "regime_snapshot": regime_snapshot,
        }
        snapshot_hash = hashlib.sha256(json.dumps(snapshot_data, sort_keys=True, default=str).encode()).hexdigest()

        return AttributionContextSnapshot(
            evaluation_snapshot=evaluation_snapshot,
            decision_snapshot=decision_snapshot,
            regime_snapshot=regime_snapshot,
            snapshot_hash=snapshot_hash,
        )

    def _compute_contributions(self, event: Dict[str, Any], snapshot: AttributionContextSnapshot) -> List[AttributionContribution]:
        """ADR-095: Contributing-factor decomposition."""
        total_variance = event["total_variance_bps"]
        contributions = []

        # Thesis contribution
        thesis_score = event.get("thesis_quality_score", 0.5)
        thesis_bps = total_variance * thesis_score * 0.3
        contributions.append(AttributionContribution(
            contribution_id=f"urn:karsa:contr:{uuid.uuid4().hex[:16]}",
            dimension="THESIS",
            target_urn=event["target_urn"],
            evidence=AttributionEvidence(
                source_type="PERFORMANCE_ENGINE",
                source_id=event["evaluation_id"],
                data_points={"quality_score": thesis_score},
                explanation="Thesis quality contribution to variance",
            ),
            contribution_bps=round(thesis_bps, 4),
            contribution_pct=round(thesis_bps / total_variance if total_variance else 0, 6),
            quality_score=thesis_score,
            quality_provenance={"source": event.get("quality_source", "SYSTEM_DEFAULT"), "score": thesis_score},
            created_at=datetime.utcnow().isoformat(),
        ))

        # Execution contribution
        exec_score = event.get("execution_quality_score", 0.5)
        exec_bps = total_variance * exec_score * 0.3
        contributions.append(AttributionContribution(
            contribution_id=f"urn:karsa:contr:{uuid.uuid4().hex[:16]}",
            dimension="EXECUTION",
            target_urn=event["target_urn"],
            evidence=AttributionEvidence(
                source_type="PERFORMANCE_ENGINE",
                source_id=event["evaluation_id"],
                data_points={"quality_score": exec_score},
                explanation="Execution quality contribution to variance",
            ),
            contribution_bps=round(exec_bps, 4),
            contribution_pct=round(exec_bps / total_variance if total_variance else 0, 6),
            quality_score=exec_score,
            quality_provenance={"source": event.get("quality_source", "SYSTEM_DEFAULT"), "score": exec_score},
            created_at=datetime.utcnow().isoformat(),
        ))

        # Allocation contribution
        alloc_score = event.get("allocation_quality_score", 0.5)
        alloc_bps = total_variance * alloc_score * 0.2
        contributions.append(AttributionContribution(
            contribution_id=f"urn:karsa:contr:{uuid.uuid4().hex[:16]}",
            dimension="ALLOCATION",
            target_urn=event["target_urn"],
            evidence=AttributionEvidence(
                source_type="PERFORMANCE_ENGINE",
                source_id=event["evaluation_id"],
                data_points={"quality_score": alloc_score},
                explanation="Allocation quality contribution to variance",
            ),
            contribution_bps=round(alloc_bps, 4),
            contribution_pct=round(alloc_bps / total_variance if total_variance else 0, 6),
            quality_score=alloc_score,
            quality_provenance={"source": event.get("quality_source", "SYSTEM_DEFAULT"), "score": alloc_score},
            created_at=datetime.utcnow().isoformat(),
        ))

        # Regime contribution
        regime_context = snapshot.regime_snapshot or {}
        regime_changed = regime_context.get("regime_changed", False)
        regime_bps = total_variance * 0.2 if regime_changed else 0
        contributions.append(AttributionContribution(
            contribution_id=f"urn:karsa:contr:{uuid.uuid4().hex[:16]}",
            dimension="REGIME",
            target_urn=event["target_urn"],
            evidence=AttributionEvidence(
                source_type="REGIME_CONTEXT",
                source_id=event.get("regime_at_evaluation", ""),
                data_points={"regime_changed": regime_changed},
                explanation="Regime effect on variance",
            ),
            contribution_bps=round(regime_bps, 4),
            contribution_pct=round(regime_bps / total_variance if total_variance else 0, 6),
            quality_score=0.8,
            quality_provenance={"source": "SYSTEM_DEFAULT", "score": 0.8},
            created_at=datetime.utcnow().isoformat(),
        ))

        return contributions

    def _compute_residual(self, total_variance: float, contributions: List[AttributionContribution]) -> float:
        """ADR-095: residual = total_variance - sum(contributions)"""
        sum_contributions = sum(c.contribution_bps for c in contributions)
        return round(total_variance - sum_contributions, 4)

    def _compute_interaction_effects(self, contributions: List[AttributionContribution]) -> List[InteractionEffect]:
        """Compute shared effects between dimensions."""
        effects = []
        dims = [(c.dimension, c.contribution_bps) for c in contributions]
        for i in range(len(dims)):
            for j in range(i + 1, len(dims)):
                shared = abs(dims[i][1] * dims[j][1]) / 100
                if shared > 0.01:
                    effects.append(InteractionEffect(
                        dimension_a=dims[i][0],
                        dimension_b=dims[j][0],
                        shared_effect_bps=round(shared, 4),
                        explanation=f"Interaction between {dims[i][0]} and {dims[j][0]}",
                    ))
        return effects

    def _compute_summary(self, total_variance: float, contributions: List[AttributionContribution], residual_bps: float, interaction_effects: List[InteractionEffect]) -> AttributionSummary:
        """Build attribution summary."""
        by_dim = {c.dimension: c.contribution_bps for c in contributions}
        return AttributionSummary(
            total_variance_bps=total_variance,
            thesis_contribution_bps=by_dim.get("THESIS", 0),
            execution_contribution_bps=by_dim.get("EXECUTION", 0),
            allocation_contribution_bps=by_dim.get("ALLOCATION", 0),
            regime_contribution_bps=by_dim.get("REGIME", 0),
            residual_bps=residual_bps,
            interaction_effects_bps=sum(ie.shared_effect_bps for ie in interaction_effects),
            attribution_confidence=0.7,
            explanation="Contributing-factor decomposition",
            interaction_effects=interaction_effects,
        )

    def _compute_quality(self, event: Dict[str, Any], contributions: List[AttributionContribution]) -> AttributionQuality:
        """ADR-099: Quality gate computation."""
        quality_scores = [c.quality_score for c in contributions]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        missing = []
        if not event.get("thesis_quality_score"):
            missing.append("thesis_quality")
        if not event.get("execution_quality_score"):
            missing.append("execution_quality")
        if not event.get("allocation_quality_score"):
            missing.append("allocation_quality")
        completeness = 1.0 - (len(missing) * 0.25)
        return AttributionQuality(
            quality_score=round(avg_quality, 4),
            data_completeness=round(completeness, 4),
            decomposition_confidence=round(avg_quality * completeness, 4),
            missing_data=missing,
        )

    def _build_quality_provenance(self, event: Dict[str, Any]) -> dict:
        """ADR-105: Per-dimension quality provenance."""
        return {
            "thesis": {"source": event.get("quality_source", "SYSTEM_DEFAULT"), "score": event.get("thesis_quality_score", 0.5)},
            "execution": {"source": event.get("quality_source", "SYSTEM_DEFAULT"), "score": event.get("execution_quality_score", 0.5)},
            "allocation": {"source": event.get("quality_source", "SYSTEM_DEFAULT"), "score": event.get("allocation_quality_score", 0.5)},
        }

    def _apply_quality_gate(self, record: AttributionRecord, quality: AttributionQuality) -> None:
        """ADR-099: Publish completed or deferred event based on quality."""
        now = datetime.utcnow()
        if quality.is_sufficient:
            event = AttributionDecompositionCompletedEvent(
                event_id=str(uuid.uuid4()),
                attribution_id=record.attribution_id,
                evaluation_id=record.evaluation_id,
                algorithm_version=record.algorithm_version,
                decision_id=record.decision_id,
                evaluation_horizon_days=record.evaluation_horizon_days,
                target_urn=record.target_urn,
                attribution_summary={
                    "total_variance_bps": record.attribution_summary.total_variance_bps,
                    "thesis_contribution_bps": record.attribution_summary.thesis_contribution_bps,
                    "execution_contribution_bps": record.attribution_summary.execution_contribution_bps,
                    "allocation_contribution_bps": record.attribution_summary.allocation_contribution_bps,
                    "regime_contribution_bps": record.attribution_summary.regime_contribution_bps,
                    "residual_bps": record.attribution_summary.residual_bps,
                    "interaction_effects_bps": record.attribution_summary.interaction_effects_bps,
                    "attribution_confidence": record.attribution_summary.attribution_confidence,
                },
                attribution_quality={
                    "quality_score": quality.quality_score,
                    "data_completeness": quality.data_completeness,
                    "decomposition_confidence": quality.decomposition_confidence,
                },
                quality_provenance=record.quality_provenance,
                regime_context=record.context_snapshot.regime_snapshot or {},
                attributed_at=now.isoformat(),
            )
            self.outbox_repo.save_event(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type="AttributionDecompositionCompletedEvent",
                payload=json.dumps(event.__dict__, default=str),
                aggregate_id=record.attribution_id,
                status="PENDING",
                created_at=now,
            ))
        else:
            event = AttributionDecompositionDeferredEvent(
                event_id=str(uuid.uuid4()),
                evaluation_id=record.evaluation_id,
                decision_id=record.decision_id,
                reason=f"Quality score {quality.quality_score} below threshold 0.3",
                quality_score=quality.quality_score,
                missing_data=quality.missing_data,
                deferred_at=now.isoformat(),
            )
            self.outbox_repo.save_event(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type="AttributionDecompositionDeferredEvent",
                payload=json.dumps(event.__dict__, default=str),
                aggregate_id=record.attribution_id,
                status="PENDING",
                created_at=now,
            ))
