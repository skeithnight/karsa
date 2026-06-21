"""RecordCapabilityEvolutionRequest -- Sprint-12. Wave-2.

Pydantic request DTO for POST /capabilities/evolutions.
Transport-only validation. No domain imports.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Valid trigger types for evolution records."""

    REVIEW_FINDING = "REVIEW_FINDING"
    ATTRIBUTION_INSIGHT = "ATTRIBUTION_INSIGHT"
    EXECUTION_OUTCOME = "EXECUTION_OUTCOME"
    GOVERNANCE_ACTION = "GOVERNANCE_ACTION"


class EvolutionType(str, Enum):
    """Valid evolution types."""

    SCORE_ADJUSTMENT = "SCORE_ADJUSTMENT"
    LIFECYCLE_CHANGE = "LIFECYCLE_CHANGE"
    CONTRACT_UPDATE = "CONTRACT_UPDATE"
    DEPENDENCY_CHANGE = "DEPENDENCY_CHANGE"
    CAPABILITY_RETIREMENT = "CAPABILITY_RETIREMENT"


class RecordCapabilityEvolutionRequest(BaseModel):
    """Request to record a capability evolution.

    All fields are validated at the transport layer.
    No domain types are referenced.
    """

    capability_family_id: str = Field(
        ..., min_length=1, description="Capability family UUID"
    )
    evaluation_id: str = Field(
        ..., min_length=1, description="Evaluation cycle UUID"
    )
    trigger_type: TriggerType
    capability_version_id: str = Field(
        ..., min_length=1, description="Capability version UUID"
    )
    capability_urn: str = Field(
        ..., min_length=1, description="Capability URN"
    )
    evolution_type: EvolutionType

    # Delta
    before_score: float = Field(..., ge=0.0, le=1.0)
    after_score: float = Field(..., ge=0.0, le=1.0)
    score_change_bps: float
    before_lifecycle_state: str = Field(..., min_length=1)
    after_lifecycle_state: str = Field(..., min_length=1)

    # Evidence
    source_type: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    finding_ids: List[str] = Field(default_factory=list)
    attribution_contribution_ids: List[str] = Field(default_factory=list)

    # Context snapshot
    capability_snapshot: Dict[str, Any] = Field(default_factory=dict)
    review_snapshot: Optional[Dict[str, Any]] = None
    attribution_snapshot: Optional[Dict[str, Any]] = None
    execution_snapshot: Optional[Dict[str, Any]] = None
    snapshot_source_versions: Dict[str, int] = Field(default_factory=dict)

    # Ordering
    evaluation_sequence: int = Field(..., ge=0)

    # Quality gate
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)

    # Optional references
    attribution_id: Optional[str] = None
    review_id: Optional[str] = None

    # Child entities
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    attribution_refs: List[Dict[str, Any]] = Field(default_factory=list)
