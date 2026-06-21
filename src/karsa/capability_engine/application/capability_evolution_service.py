"""CapabilityEvolutionService -- Sprint-11. Transaction A.

ADR-120: Business identity enforcement.
ADR-133: Version registry integration.
ADR-135: Context snapshot capture.
ADR-136: Evaluation sequence assignment.

Transaction A ONLY:
1. Build context snapshot
2. Validate provenance
3. Validate quality threshold
4. Create CapabilityEvolution
5. Save evolution record
6. Update version registry
7. Save outbox events

Must NOT:
- update CapabilityHealthScore
- update projections
- rebuild history
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.events.capability_events import (
    CapabilityEvolutionDeferredEvent,
    CapabilityEvolutionRecordedEvent,
)
from karsa.capability_engine.domain.exceptions import (
    InvalidEvolutionError,
    InvalidEvolutionEvidenceError,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
    EvolutionStatus,
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
from karsa.capability_engine.application.ports.capability_evolution_port import (
    CapabilityEvolutionPort,
)
from karsa.capability_engine.application.ports.capability_outbox_port import (
    CapabilityOutboxPort,
    OutboxEvent,
)
from karsa.capability_engine.application.ports.capability_version_registry_port import (
    CapabilityVersionRegistryPort,
    VersionRegistryEntry,
)


# ADR-130: Quality gate threshold
DEFAULT_QUALITY_THRESHOLD = 0.3


@dataclass
class EvolutionCommand:
    """Input DTO for creating an evolution record."""

    capability_family_id: str
    evaluation_id: str
    trigger_type: str  # EvolutionTriggerType value
    capability_version_id: str
    capability_urn: str
    evolution_type: str  # EvolutionType value
    delta: EvolutionDelta
    evidence: EvolutionEvidence
    context_snapshot: EvolutionContextSnapshot
    evaluation_sequence: int
    attribution_id: Optional[str] = None
    review_id: Optional[str] = None
    findings: Optional[List] = None
    attribution_refs: Optional[List] = None
    quality_score: float = 1.0  # 0.0-1.0, used for quality gate
    reviewed_at: Optional[datetime] = None


@dataclass
class EvolutionResult:
    """Output DTO from evolution creation."""

    success: bool
    evolution_id: Optional[str] = None
    deferred: bool = False
    defer_reason: Optional[str] = None
    events: Optional[List] = None


class CapabilityEvolutionService:
    """Transaction A: Evolution record creation and outbox publishing.

    ADR-130: Strict transaction boundary -- does NOT touch health scores,
    projections, or history. Those belong to Transaction B
    (CapabilityScoringService).
    """

    def __init__(
        self,
        evolution_repo: CapabilityEvolutionPort,
        version_registry: CapabilityVersionRegistryPort,
        outbox_repo: CapabilityOutboxPort,
        quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
    ) -> None:
        self._evolution_repo = evolution_repo
        self._version_registry = version_registry
        self._outbox_repo = outbox_repo
        self._quality_threshold = quality_threshold

    def record_evolution(self, command: EvolutionCommand) -> EvolutionResult:
        """Execute Transaction A: record a capability evolution.

        Steps:
        1. Build context snapshot (already in command)
        2. Validate provenance (evidence must have sources)
        3. Validate quality threshold (gate check)
        4. Create CapabilityEvolution aggregate
        5. Save evolution record (write-once)
        6. Update version registry (canonical governance)
        7. Save outbox events (durable publish)
        """
        # Step 1: Context snapshot already validated by EvolutionContextSnapshot.__post_init__

        # Step 2: Validate provenance -- evidence must have at least one source
        self._validate_provenance(command.evidence)

        # Step 3: Quality gate -- defer if below threshold
        if command.quality_score < self._quality_threshold:
            return self._defer_evolution(command)

        # Step 4: Create aggregate
        evolution = self._create_evolution(command)

        # Step 5: Save evolution record (write-once, ON CONFLICT DO NOTHING)
        saved = self._evolution_repo.save(evolution)
        if not saved:
            return EvolutionResult(
                success=False,
                evolution_id=None,
                deferred=False,
                defer_reason="Duplicate evolution for this business identity",
            )

        # Step 6: Update version registry
        self._update_version_registry(evolution)

        # Step 7: Save outbox events
        events = self._publish_outbox_events(evolution)

        return EvolutionResult(
            success=True,
            evolution_id=evolution.evolution_id,
            deferred=False,
            events=events,
        )

    def _validate_provenance(self, evidence: EvolutionEvidence) -> None:
        """ADR-120: Evolution must have traceable provenance."""
        if not evidence.source_type or not evidence.source_id:
            raise InvalidEvolutionEvidenceError(
                "Evidence must have source_type and source_id"
            )
        if not evidence.finding_ids and not evidence.attribution_contribution_ids:
            raise InvalidEvolutionEvidenceError(
                "Evidence must reference at least one finding or attribution"
            )

    def _defer_evolution(self, command: EvolutionCommand) -> EvolutionResult:
        """Quality gate: defer evolution below threshold."""
        missing = []
        if not command.evidence.finding_ids:
            missing.append("finding_ids")
        if not command.evidence.attribution_contribution_ids:
            missing.append("attribution_contribution_ids")

        event = CapabilityEvolutionDeferredEvent(
            event_id=str(uuid.uuid4()),
            capability_family_id=command.capability_family_id,
            evaluation_id=command.evaluation_id,
            reason="Quality score below threshold",
            quality_score=command.quality_score,
            missing_data=missing,
            deferred_at=datetime.utcnow().isoformat(),
        )

        outbox_event = OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=json.dumps(event.to_dict()),
            aggregate_id=command.capability_family_id,
        )
        self._outbox_repo.save_event(outbox_event)

        return EvolutionResult(
            success=False,
            deferred=True,
            defer_reason="Quality score below threshold",
            events=[event],
        )

    def _create_evolution(self, command: EvolutionCommand) -> CapabilityEvolution:
        """Construct the immutable CapabilityEvolution aggregate."""
        evolution_id = f"urn:karsa:capability:evolution:{uuid.uuid4().hex}"
        return CapabilityEvolution(
            evolution_id=evolution_id,
            capability_family_id=command.capability_family_id,
            evaluation_id=command.evaluation_id,
            trigger_type=command.trigger_type,
            capability_version_id=command.capability_version_id,
            capability_urn=command.capability_urn,
            attribution_id=command.attribution_id,
            review_id=command.review_id,
            evolution_type=command.evolution_type,
            delta=command.delta,
            evidence=command.evidence,
            findings=command.findings or [],
            attribution_refs=command.attribution_refs or [],
            context_snapshot=command.context_snapshot,
            evaluation_sequence=command.evaluation_sequence,
            reviewed_at=command.reviewed_at or datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

    def _update_version_registry(self, evolution: CapabilityEvolution) -> None:
        """ADR-133: Register evolution in the version registry.

        First evolution for (family, eval, trigger) -> CANONICAL.
        Subsequent -> supersede previous via registry.
        """
        existing = self._version_registry.get_canonical(
            evolution.capability_family_id,
            evolution.evaluation_id,
            evolution.trigger_type,
        )

        if existing is None:
            # First canonical for this identity
            entry = VersionRegistryEntry(
                version_id=str(uuid.uuid4()),
                capability_family_id=evolution.capability_family_id,
                evaluation_id=evolution.evaluation_id,
                trigger_type=evolution.trigger_type,
                evolution_id=evolution.evolution_id,
                evolution_status=EvolutionStatus.CANONICAL.value,
            )
            self._version_registry.save(entry)
        else:
            # Supersede previous canonical
            self._version_registry.supersede_previous(
                evolution.capability_family_id,
                evolution.evaluation_id,
                evolution.trigger_type,
                evolution.evolution_id,
            )
            # Insert new canonical
            entry = VersionRegistryEntry(
                version_id=str(uuid.uuid4()),
                capability_family_id=evolution.capability_family_id,
                evaluation_id=evolution.evaluation_id,
                trigger_type=evolution.trigger_type,
                evolution_id=evolution.evolution_id,
                evolution_status=EvolutionStatus.CANONICAL.value,
            )
            self._version_registry.save(entry)

    def _publish_outbox_events(
        self, evolution: CapabilityEvolution
    ) -> List[CapabilityEvolutionRecordedEvent]:
        """Transaction A: publish events to outbox within same transaction."""
        event = CapabilityEvolutionRecordedEvent(
            event_id=str(uuid.uuid4()),
            evolution_id=evolution.evolution_id,
            capability_family_id=evolution.capability_family_id,
            capability_urn=evolution.capability_urn,
            evaluation_id=evolution.evaluation_id,
            evolution_type=evolution.evolution_type,
            trigger_type=evolution.trigger_type,
            delta=evolution.delta.to_dict() if hasattr(evolution.delta, "to_dict") else {
                "before_score": evolution.delta.before_score,
                "after_score": evolution.delta.after_score,
                "score_change_bps": evolution.delta.score_change_bps,
            },
            reviewed_at=evolution.reviewed_at.isoformat(),
        )

        outbox_event = OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=json.dumps(event.to_dict()),
            aggregate_id=evolution.capability_family_id,
        )
        self._outbox_repo.save_event(outbox_event)

        return [event]
