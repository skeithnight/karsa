"""UpdateCapabilityHealthRequest -- Sprint-12. Wave-2.

Pydantic request DTO for POST /capabilities/health.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ScoreComponentRequest(BaseModel):
    """Individual score component within the health update."""

    component_name: str = Field(..., min_length=1)
    component_score: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., gt=0.0, le=1.0)
    evaluation_count: int = Field(..., ge=0)
    confidence: float = Field(..., ge=0.0, le=1.0)


class UpdateCapabilityHealthRequest(BaseModel):
    """Request to update a capability health score.

    All fields validated at transport layer.
    """

    capability_family_id: str = Field(
        ..., min_length=1, description="Capability family UUID"
    )
    evaluation_id: str = Field(
        ..., min_length=1, description="Evaluation cycle UUID"
    )
    evaluation_sequence: int = Field(..., ge=0)
    capability_version_id: str = Field(
        ..., min_length=1, description="Capability version UUID"
    )
    score: float = Field(..., ge=0.0, le=1.0)
    components: List[ScoreComponentRequest] = Field(..., min_length=1)
    algorithm_version: str = Field(default="v1.0", min_length=1)
    capability_urn: str = Field(default="", description="Capability URN for governance events")
