"""ReconcileCapabilityStateCommand -- Sprint-11. Wave-8.

Command contract for triggering state reconciliation.
ADR-130: Recovery path for split Transaction A/B.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconcileCapabilityStateCommand:
    """Command to trigger capability state reconciliation.

    Detects orphaned evolutions, missing history, stale projections.
    ADR-130 recovery path.
    """

    dry_run: bool = False  # If True, only detect, don't repair
