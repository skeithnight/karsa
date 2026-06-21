"""ReviewACL -- Sprint-11. Wave-8.

Anti-corruption layer for Review Engine events.
Translates review domain events into capability engine commands.

Prevents Review Engine types (ReviewAssessment, CalibrationGrade,
etc.) from leaking into the Capability Engine domain.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)


@dataclass(frozen=True)
class ReviewFindingPayload:
    """Normalized review finding for ACL translation.

    This is the ACL's internal representation -- NOT a Review Engine type.
    """

    review_id: str
    capability_family_id: str
    evaluation_id: str
    capability_version_id: str
    capability_urn: str
    score_before: float
    score_after: float
    lifecycle_state_before: str
    lifecycle_state_after: str
    source_type: str = "REVIEW"
    source_id: str = ""
    finding_ids: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    capability_snapshot: Dict[str, Any] = field(default_factory=dict)
    review_snapshot: Dict[str, Any] = field(default_factory=dict)
    evaluation_sequence: int = 0
    quality_score: float = 1.0


class ReviewACL:
    """Translates Review Engine events into Capability Engine commands.

    The ACL ensures:
    - No Review Engine types are referenced by Capability Engine
    - Review domain concepts are mapped to capability evolution concepts
    - The translation is deterministic and lossless
    """

    def translate_review_finding(
        self, payload: ReviewFindingPayload
    ) -> RecordCapabilityEvolutionCommand:
        """Translate a review finding into an evolution command.

        Maps:
        - Review assessment -> EvolutionEvidence
        - Review score change -> EvolutionDelta
        - Review context -> EvolutionContextSnapshot
        """
        bps = (payload.score_after - payload.score_before) * 10000

        return RecordCapabilityEvolutionCommand(
            capability_family_id=payload.capability_family_id,
            evaluation_id=payload.evaluation_id,
            trigger_type="REVIEW_FINDING",
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
            source_id=payload.source_id or payload.review_id,
            finding_ids=list(payload.finding_ids),
            # Snapshot
            capability_snapshot=dict(payload.capability_snapshot),
            review_snapshot=dict(payload.review_snapshot),
            snapshot_source_versions={},
            # Ordering
            evaluation_sequence=payload.evaluation_sequence,
            quality_score=payload.quality_score,
            # References
            review_id=payload.review_id,
            # Child entities
            findings=list(payload.findings),
        )

    def translate_from_dict(
        self, event_payload: Dict[str, Any]
    ) -> RecordCapabilityEvolutionCommand:
        """Translate a raw review event dict into an evolution command.

        For use when the event arrives as a generic dict from the
        event bus (no Review Engine types imported).
        """
        payload = ReviewFindingPayload(
            review_id=event_payload.get("review_id", ""),
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
            finding_ids=event_payload.get("finding_ids", []),
            findings=event_payload.get("findings", []),
            capability_snapshot=event_payload.get(
                "capability_snapshot", {}
            ),
            review_snapshot=event_payload.get("review_snapshot", {}),
            evaluation_sequence=event_payload.get(
                "evaluation_sequence", 0
            ),
            quality_score=event_payload.get("quality_score", 1.0),
        )
        return self.translate_review_finding(payload)
