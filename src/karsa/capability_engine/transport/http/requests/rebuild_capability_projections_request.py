"""RebuildCapabilityProjectionsRequest -- Sprint-12. Wave-2.

Pydantic request DTO for POST /capabilities/projections/rebuild.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RebuildCapabilityProjectionsRequest(BaseModel):
    """Request to trigger projection rebuilds.

    ADR-135: Optional checkpoint fields for staleness validation.
    """

    projection_name: Optional[str] = Field(
        default=None,
        description="Specific projection to rebuild. None = rebuild all.",
    )
    source_checkpoint: Optional[int] = Field(
        default=None, ge=0,
        description="Source checkpoint for ADR-135 staleness validation",
    )
    current_checkpoint: Optional[int] = Field(
        default=None, ge=0,
        description="Current checkpoint for ADR-135 staleness validation",
    )
