"""ReconcileCapabilityStateRequest -- Sprint-12. Wave-2.

Pydantic request DTO for POST /capabilities/reconcile.
"""

from pydantic import BaseModel, Field


class ReconcileCapabilityStateRequest(BaseModel):
    """Request to trigger state reconciliation. ADR-130."""

    dry_run: bool = Field(
        default=False,
        description="If True, only detect inconsistencies without repair",
    )
