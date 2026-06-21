"""EvolutionCommandTranslator -- Sprint-11. Wave-9R. TD-005.

Translates RecordCapabilityEvolutionCommand (contract) into
EvolutionCommand (application). Handles all domain VO construction
and hash computation. Facade delegates to this translator instead
of importing domain types directly.
"""

import hashlib
import json
from typing import Any, Dict

from karsa.capability_engine.application.capability_evolution_service import (
    EvolutionCommand,
)
from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
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


def _compute_snapshot_hash(data: Dict) -> str:
    """Compute SHA-256 hash of serialized snapshot data."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class EvolutionCommandTranslator:
    """Translates contract commands into application commands.

    Owns all domain VO construction and hash computation.
    The facade delegates to this translator, keeping domain
    imports out of the integration layer.
    """

    def translate(
        self, command: RecordCapabilityEvolutionCommand
    ) -> EvolutionCommand:
        """Translate a contract command into an application command."""
        # Build snapshot hash
        snapshot_data = {
            "capability": command.capability_snapshot,
            "review": command.review_snapshot,
            "attribution": command.attribution_snapshot,
            "execution": command.execution_snapshot,
            "source_versions": command.snapshot_source_versions,
        }
        snapshot_hash = _compute_snapshot_hash(snapshot_data)

        return EvolutionCommand(
            capability_family_id=command.capability_family_id,
            evaluation_id=command.evaluation_id,
            trigger_type=command.trigger_type,
            capability_version_id=command.capability_version_id,
            capability_urn=command.capability_urn,
            evolution_type=command.evolution_type,
            delta=EvolutionDelta(
                before_score=command.before_score,
                after_score=command.after_score,
                score_change_bps=command.score_change_bps,
                before_lifecycle_state=command.before_lifecycle_state,
                after_lifecycle_state=command.after_lifecycle_state,
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            ),
            evidence=EvolutionEvidence(
                source_type=command.source_type,
                source_id=command.source_id,
                finding_ids=command.finding_ids,
                attribution_contribution_ids=command.attribution_contribution_ids,
            ),
            context_snapshot=EvolutionContextSnapshot(
                capability_snapshot=command.capability_snapshot,
                review_snapshot=command.review_snapshot,
                attribution_snapshot=command.attribution_snapshot,
                execution_snapshot=command.execution_snapshot,
                snapshot_hash=snapshot_hash,
                snapshot_source_versions=command.snapshot_source_versions,
            ),
            evaluation_sequence=command.evaluation_sequence,
            attribution_id=command.attribution_id,
            review_id=command.review_id,
            quality_score=command.quality_score,
        )
