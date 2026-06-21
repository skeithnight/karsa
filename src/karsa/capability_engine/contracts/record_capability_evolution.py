"""RecordCapabilityEvolutionCommand -- Sprint-11. Wave-8.

Command contract for recording a capability evolution.
External contexts use this to submit evolution data
without referencing domain aggregates or value objects.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RecordCapabilityEvolutionCommand:
    """Command to record a capability evolution.

    Transport-agnostic. No domain types leak through this contract.
    All value objects are represented as primitive types.
    """

    capability_family_id: str
    evaluation_id: str
    trigger_type: str  # EvolutionTriggerType value
    capability_version_id: str
    capability_urn: str
    evolution_type: str  # EvolutionType value

    # Delta as primitives (not EvolutionDelta VO)
    before_score: float
    after_score: float
    score_change_bps: float
    before_lifecycle_state: str
    after_lifecycle_state: str

    # Evidence as primitives (not EvolutionEvidence VO)
    source_type: str
    source_id: str
    finding_ids: List[str] = field(default_factory=list)
    attribution_contribution_ids: List[str] = field(default_factory=list)

    # Context snapshot as raw dict (not EvolutionContextSnapshot VO)
    capability_snapshot: Dict[str, Any] = field(default_factory=dict)
    review_snapshot: Optional[Dict[str, Any]] = None
    attribution_snapshot: Optional[Dict[str, Any]] = None
    execution_snapshot: Optional[Dict[str, Any]] = None
    snapshot_source_versions: Dict[str, int] = field(default_factory=dict)

    # Evaluation ordering
    evaluation_sequence: int = 0

    # Quality gate
    quality_score: float = 1.0

    # Optional references
    attribution_id: Optional[str] = None
    review_id: Optional[str] = None

    # Child entities as primitives
    findings: List[Dict[str, Any]] = field(default_factory=list)
    attribution_refs: List[Dict[str, Any]] = field(default_factory=list)
