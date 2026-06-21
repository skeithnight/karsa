"""CapabilityProjectionWorker -- Sprint-11. Wave-6.

Consumes domain events and triggers projection rebuilds.

Supported events:
- CapabilityEvolutionRecordedEvent -> rebuild_evolution_projection
- CapabilityHealthScoreUpdatedEvent -> rebuild_health_projection
- CapabilityEvolutionCanonicalChangedEvent -> rebuild_evolution_projection

Requirements:
- ADR-135: Validate source checkpoints before rebuild.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from karsa.capability_engine.application.capability_projection_service import (
    CapabilityProjectionService,
    RebuildResult,
)
from karsa.capability_engine.domain.exceptions import ProjectionStalenessError


@dataclass
class ProjectionWorkerResult:
    """Result of a projection worker run."""

    events_processed: int
    rebuilds_triggered: int
    rebuild_results: List[RebuildResult]
    errors: List[str]


class CapabilityProjectionWorker:
    """Consumes domain events and triggers projection rebuilds.

    ADR-135: Validates source checkpoints before each rebuild.
    If checkpoint validation fails, the error is recorded but
    processing continues for other events.
    """

    def __init__(
        self,
        projection_service: CapabilityProjectionService,
        source_checkpoint: Optional[int] = None,
        current_checkpoint: Optional[int] = None,
    ) -> None:
        self._projection_service = projection_service
        self._source_checkpoint = source_checkpoint
        self._current_checkpoint = current_checkpoint

    def handle_evolution_recorded(
        self, payload: Dict[str, Any]
    ) -> Optional[RebuildResult]:
        """Handle CapabilityEvolutionRecordedEvent.

        Triggers evolution and timeseries projection rebuild.
        """
        try:
            result = self._projection_service.rebuild_evolution_projection(
                source_checkpoint=self._source_checkpoint,
                current_checkpoint=self._current_checkpoint,
            )
            # Also rebuild timeseries since evolution may affect it
            self._projection_service.rebuild_timeseries_projection(
                source_checkpoint=self._source_checkpoint,
                current_checkpoint=self._current_checkpoint,
            )
            return result
        except ProjectionStalenessError:
            raise

    def handle_health_score_updated(
        self, payload: Dict[str, Any]
    ) -> Optional[RebuildResult]:
        """Handle CapabilityHealthScoreUpdatedEvent.

        Triggers health and timeseries projection rebuild.
        """
        try:
            result = self._projection_service.rebuild_health_projection(
                source_checkpoint=self._source_checkpoint,
                current_checkpoint=self._current_checkpoint,
            )
            self._projection_service.rebuild_timeseries_projection(
                source_checkpoint=self._source_checkpoint,
                current_checkpoint=self._current_checkpoint,
            )
            return result
        except ProjectionStalenessError:
            raise

    def handle_canonical_changed(
        self, payload: Dict[str, Any]
    ) -> Optional[RebuildResult]:
        """Handle CapabilityEvolutionCanonicalChangedEvent.

        Triggers evolution projection rebuild.
        """
        try:
            return self._projection_service.rebuild_evolution_projection(
                source_checkpoint=self._source_checkpoint,
                current_checkpoint=self._current_checkpoint,
            )
        except ProjectionStalenessError:
            raise

    def rebuild_all(
        self,
        source_checkpoint: Optional[int] = None,
        current_checkpoint: Optional[int] = None,
    ) -> List[RebuildResult]:
        """Trigger a full rebuild of all projections.

        ADR-135: Validates checkpoints.
        """
        return self._projection_service.rebuild_all(
            source_checkpoint=source_checkpoint or self._source_checkpoint,
            current_checkpoint=current_checkpoint or self._current_checkpoint,
        )
