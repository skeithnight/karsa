"""HealthCommandTranslator -- Sprint-11. Wave-9R. TD-005.

Translates UpdateCapabilityHealthCommand (contract) into
ScoringCommand (application). Handles CapabilityScoreComponent
construction.
"""

from karsa.capability_engine.application.capability_scoring_service import (
    ScoringCommand,
)
from karsa.capability_engine.contracts.update_capability_health import (
    UpdateCapabilityHealthCommand,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)


class HealthCommandTranslator:
    """Translates health contract commands into application commands.

    Owns CapabilityScoreComponent construction.
    """

    def translate(
        self, command: UpdateCapabilityHealthCommand
    ) -> ScoringCommand:
        """Translate a contract command into an application command."""
        components = [
            CapabilityScoreComponent(
                component_name=c.get("component_name", ""),
                component_score=c.get("component_score", 0.0),
                weight=c.get("weight", 0.25),
                evaluation_count=c.get("evaluation_count", 1),
                confidence=c.get("confidence", 0.0),
            )
            for c in command.components
        ]

        return ScoringCommand(
            capability_family_id=command.capability_family_id,
            evaluation_id=command.evaluation_id,
            evaluation_sequence=command.evaluation_sequence,
            capability_version_id=command.capability_version_id,
            score=command.score,
            components=components,
            algorithm_version=command.algorithm_version,
            capability_urn=command.capability_urn,
        )
