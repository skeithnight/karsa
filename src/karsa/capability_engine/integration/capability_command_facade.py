"""CapabilityCommandFacade -- Sprint-11. Wave-8.

Public command interface for the Capability Engine.
External bounded contexts use this facade to submit commands
without referencing internal application services, domain
aggregates, or infrastructure repositories.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from karsa.capability_engine.application.capability_evolution_service import (
    CapabilityEvolutionService,
)
from karsa.capability_engine.application.capability_scoring_service import (
    CapabilityScoringService,
)
from karsa.capability_engine.application.capability_projection_service import (
    CapabilityProjectionService,
)
from karsa.capability_engine.application.command_translators import (
    EvolutionCommandTranslator,
    HealthCommandTranslator,
)
from karsa.capability_engine.application.reconciliation_service import (
    ReconciliationService,
)
from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)
from karsa.capability_engine.contracts.update_capability_health import (
    UpdateCapabilityHealthCommand,
)
from karsa.capability_engine.contracts.rebuild_capability_projections import (
    RebuildCapabilityProjectionsCommand,
)
from karsa.capability_engine.contracts.reconcile_capability_state import (
    ReconcileCapabilityStateCommand,
)


@dataclass
class CommandResult:
    """Public result contract for command execution."""

    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class CapabilityCommandFacade:
    """Public command interface for the Capability Engine.

    Translates contracts into internal application service calls.
    External contexts see only contracts/* types.
    """

    def __init__(
        self,
        evolution_service: CapabilityEvolutionService,
        scoring_service: CapabilityScoringService,
        projection_service: CapabilityProjectionService,
        reconciliation_service: ReconciliationService,
    ) -> None:
        self._evolution_service = evolution_service
        self._scoring_service = scoring_service
        self._projection_service = projection_service
        self._reconciliation_service = reconciliation_service
        self._evolution_translator = EvolutionCommandTranslator()
        self._health_translator = HealthCommandTranslator()

    def record_evolution(
        self, command: RecordCapabilityEvolutionCommand
    ) -> CommandResult:
        """Record a capability evolution from contract."""
        try:
            internal = self._evolution_translator.translate(command)
            result = self._evolution_service.record_evolution(internal)

            if result.success:
                return CommandResult(
                    success=True,
                    message="Evolution recorded",
                    data={"evolution_id": result.evolution_id},
                )
            elif result.deferred:
                return CommandResult(
                    success=False,
                    message=f"Deferred: {result.defer_reason}",
                )
            else:
                return CommandResult(
                    success=False,
                    message="Duplicate or failed",
                )
        except Exception as e:
            return CommandResult(
                success=False, message=f"Error: {e}"
            )

    def update_health(
        self, command: UpdateCapabilityHealthCommand
    ) -> CommandResult:
        """Update capability health score from contract."""
        try:
            internal = self._health_translator.translate(command)
            result = self._scoring_service.record_evaluation(internal)

            return CommandResult(
                success=result.success,
                message="Health updated" if result.success else "Failed",
                data={
                    "health_score_id": result.health_score_id,
                    "occ_retries": result.occ_retries,
                },
            )
        except Exception as e:
            return CommandResult(
                success=False, message=f"Error: {e}"
            )

    def rebuild_projections(
        self, command: RebuildCapabilityProjectionsCommand
    ) -> CommandResult:
        """Trigger projection rebuild from contract."""
        try:
            results = self._projection_service.rebuild_all(
                source_checkpoint=command.source_checkpoint,
                current_checkpoint=command.current_checkpoint,
            )
            return CommandResult(
                success=True,
                message=f"Rebuilt {len(results)} projections",
                data={
                    "projections": [
                        {
                            "name": r.projection_name,
                            "rows": r.rows_written,
                        }
                        for r in results
                    ]
                },
            )
        except Exception as e:
            return CommandResult(
                success=False, message=f"Error: {e}"
            )

    def reconcile(
        self, command: ReconcileCapabilityStateCommand
    ) -> CommandResult:
        """Trigger state reconciliation from contract. ADR-130."""
        try:
            result = self._reconciliation_service.reconcile()
            return CommandResult(
                success=True,
                message="Reconciliation complete",
                data={
                    "orphaned": result.orphaned_evolutions,
                    "stale": result.stale_projections,
                    "missing_history": result.missing_history,
                    "rebuilds": result.rebuilds_triggered,
                },
            )
        except Exception as e:
            return CommandResult(
                success=False, message=f"Error: {e}"
            )
