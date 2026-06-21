"""AttributionACL -- Sprint-11. Wave-8.

Anti-corruption layer for Attribution Engine events.
Translates attribution domain events into capability engine commands.

Prevents Attribution Engine types (AttributionRecord, Contribution,
etc.) from leaking into the Capability Engine domain.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)


@dataclass(frozen=True)
class AttributionInsightPayload:
    """Normalized attribution insight for ACL translation.

    NOT an Attribution Engine type -- this is the ACL boundary.
    """

    attribution_id: str
    capability_family_id: str
    evaluation_id: str
    capability_version_id: str
    capability_urn: str
    score_before: float
    score_after: float
    lifecycle_state_before: str
    lifecycle_state_after: str
    source_type: str = "ATTRIBUTION"
    source_id: str = ""
    contribution_ids: List[str] = field(default_factory=list)
    attribution_refs: List[Dict[str, Any]] = field(default_factory=list)
    capability_snapshot: Dict[str, Any] = field(default_factory=dict)
    attribution_snapshot: Dict[str, Any] = field(default_factory=dict)
    evaluation_sequence: int = 0
    quality_score: float = 1.0


class AttributionACL:
    """Translates Attribution Engine events into Capability Engine commands.

    The ACL ensures:
    - No Attribution Engine types are referenced by Capability Engine
    - Attribution contributions are mapped to evolution evidence
    - The translation is deterministic and lossless
    """

    def translate_attribution_insight(
        self, payload: AttributionInsightPayload
    ) -> RecordCapabilityEvolutionCommand:
        """Translate an attribution insight into an evolution command."""
        bps = (payload.score_after - payload.score_before) * 10000

        return RecordCapabilityEvolutionCommand(
            capability_family_id=payload.capability_family_id,
            evaluation_id=payload.evaluation_id,
            trigger_type="ATTRIBUTION_INSIGHT",
            capability_version_id=payload.capability_version_id,
            capability_urn=payload.capability_urn,
            evolution_type="SCORE_ADJUSTMENT",
            # Delta
            before_score=payload.score_before,
            after_score=payload.score_after,
            score_change_bps=bps,
            before_lifecycle_state=payload.lifecycle_state_before,
            after_lifecycle_state=payload.lifecycle_state_after,
            # Evidence
            source_type=payload.source_type,
            source_id=payload.source_id or payload.attribution_id,
            attribution_contribution_ids=list(payload.contribution_ids),
            # Snapshot
            capability_snapshot=dict(payload.capability_snapshot),
            attribution_snapshot=dict(payload.attribution_snapshot),
            snapshot_source_versions={},
            # Ordering
            evaluation_sequence=payload.evaluation_sequence,
            quality_score=payload.quality_score,
            # References
            attribution_id=payload.attribution_id,
            # Child entities
            attribution_refs=list(payload.attribution_refs),
        )

    def translate_from_dict(
        self, event_payload: Dict[str, Any]
    ) -> RecordCapabilityEvolutionCommand:
        """Translate a raw attribution event dict into an evolution command."""
        payload = AttributionInsightPayload(
            attribution_id=event_payload.get("attribution_id", ""),
            capability_family_id=event_payload.get(
                "capability_family_id", ""
            ),
            evaluation_id=event_payload.get("evaluation_id", ""),
            capability_version_id=event_payload.get(
                "capability_version_id", ""
            ),
            capability_urn=event_payload.get("capability_urn", ""),
            score_before=event_payload.get("score_before", 0.0),
            score_after=event_payload.get("score_after", 0.0),
            lifecycle_state_before=event_payload.get(
                "lifecycle_state_before", "ACTIVE"
            ),
            lifecycle_state_after=event_payload.get(
                "lifecycle_state_after", "ACTIVE"
            ),
            source_id=event_payload.get("source_id", ""),
            contribution_ids=event_payload.get("contribution_ids", []),
            attribution_refs=event_payload.get("attribution_refs", []),
            capability_snapshot=event_payload.get(
                "capability_snapshot", {}
            ),
            attribution_snapshot=event_payload.get(
                "attribution_snapshot", {}
            ),
            evaluation_sequence=event_payload.get(
                "evaluation_sequence", 0
            ),
            quality_score=event_payload.get("quality_score", 1.0),
        )
        return self.translate_attribution_insight(payload)
