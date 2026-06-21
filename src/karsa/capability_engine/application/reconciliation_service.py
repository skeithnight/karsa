"""ReconciliationService -- Sprint-11. Wave-9R. TD-007.

Application-layer service that wraps the ReconciliationWorker.
The facade calls this service instead of importing the worker directly.
"""

from dataclasses import dataclass
from typing import List

from karsa.capability_engine.workers.capability_reconciliation_worker import (
    CapabilityReconciliationWorker,
    ReconciliationResult,
)


@dataclass
class ReconciliationResponse:
    """Public response from reconciliation. No worker types exposed."""

    orphaned_evolutions: List[str]
    stale_projections: List[str]
    missing_history: List[str]
    rebuilds_triggered: int


class ReconciliationService:
    """Application-layer wrapper for ReconciliationWorker.

    The facade imports this service instead of the worker.
    Worker implementation details are hidden.
    """

    def __init__(
        self, worker: CapabilityReconciliationWorker
    ) -> None:
        self._worker = worker

    def reconcile(self) -> ReconciliationResponse:
        """Run reconciliation and return a clean response."""
        result = self._worker.reconcile()
        return ReconciliationResponse(
            orphaned_evolutions=result.orphaned_evolutions,
            stale_projections=result.stale_projections,
            missing_history=result.missing_history,
            rebuilds_triggered=len(result.rebuild_results),
        )

    def detect_orphaned_evolutions(self) -> List[str]:
        """Find families with evolutions but no health score."""
        return self._worker.detect_orphaned_evolutions()

    def detect_missing_history(self) -> List[str]:
        """Find families with health score but no history."""
        return self._worker.detect_missing_history()

    def detect_stale_projections(self) -> List[str]:
        """Find families with stale projections."""
        return self._worker.detect_stale_projections()
