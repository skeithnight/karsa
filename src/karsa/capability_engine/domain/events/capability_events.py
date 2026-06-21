"""Capability Engine domain events -- Sprint-11.

All events are frozen dataclasses following the review_engine /
attribution_engine convention: standalone, no base class, trailing
metadata fields with defaults.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CapabilityEvolutionRecordedEvent:
    """Published when an evolution record is saved successfully."""

    # Required domain fields
    event_id: str
    evolution_id: str  # URN of the evolution record
    capability_family_id: str  # UUID
    capability_urn: str  # URN of the capability
    evaluation_id: str  # UUID
    evolution_type: str  # EvolutionType enum value
    trigger_type: str  # EvolutionTriggerType enum value
    delta: Dict[str, Any] = field(default_factory=dict)  # EvolutionDelta as dict
    reviewed_at: str = ""  # ISO datetime string

    # Trailing metadata (ADR convention)
    event_sequence: int = 0
    event_type: str = "CapabilityEvolutionRecordedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization for outbox and replay."""
        return {
            "event_id": self.event_id,
            "evolution_id": self.evolution_id,
            "capability_family_id": self.capability_family_id,
            "capability_urn": self.capability_urn,
            "evaluation_id": self.evaluation_id,
            "evolution_type": self.evolution_type,
            "trigger_type": self.trigger_type,
            "delta": self.delta,
            "reviewed_at": self.reviewed_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class CapabilityHealthScoreUpdatedEvent:
    """Published when a health score aggregate is updated."""

    # Required domain fields
    event_id: str
    health_score_id: str  # UUID of the health score aggregate
    capability_family_id: str  # UUID
    previous_score: float  # 0.0-1.0
    new_score: float  # 0.0-1.0
    score_components: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_id: str = ""  # UUID
    algorithm_version: str = "v1.0"  # ADR-134
    updated_at: str = ""  # ISO datetime string

    # Trailing metadata
    event_sequence: int = 0
    event_type: str = "CapabilityHealthScoreUpdatedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "health_score_id": self.health_score_id,
            "capability_family_id": self.capability_family_id,
            "previous_score": self.previous_score,
            "new_score": self.new_score,
            "score_components": self.score_components,
            "evaluation_id": self.evaluation_id,
            "algorithm_version": self.algorithm_version,
            "updated_at": self.updated_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class CapabilityEvolutionCanonicalChangedEvent:
    """Published when the canonical evolution version changes."""

    # Required domain fields
    event_id: str
    capability_family_id: str  # UUID
    evaluation_id: str  # UUID
    trigger_type: str  # EvolutionTriggerType enum value
    previous_evolution_id: Optional[str] = None  # URN, None if first
    new_evolution_id: str = ""  # URN
    changed_at: str = ""  # ISO datetime string
    changed_by: str = ""  # actor identifier

    # Trailing metadata
    event_sequence: int = 0
    event_type: str = "CapabilityEvolutionCanonicalChangedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "capability_family_id": self.capability_family_id,
            "evaluation_id": self.evaluation_id,
            "trigger_type": self.trigger_type,
            "previous_evolution_id": self.previous_evolution_id,
            "new_evolution_id": self.new_evolution_id,
            "changed_at": self.changed_at,
            "changed_by": self.changed_by,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class CapabilityEvolutionDeferredEvent:
    """Published when evolution processing is deferred due to low quality."""

    # Required domain fields
    event_id: str
    capability_family_id: str  # UUID
    evaluation_id: str  # UUID
    reason: str = ""
    quality_score: float = 0.0  # 0.0-1.0
    missing_data: List[str] = field(default_factory=list)
    deferred_at: str = ""  # ISO datetime string

    # Trailing metadata
    event_sequence: int = 0
    event_type: str = "CapabilityEvolutionDeferredEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "capability_family_id": self.capability_family_id,
            "evaluation_id": self.evaluation_id,
            "reason": self.reason,
            "quality_score": self.quality_score,
            "missing_data": self.missing_data,
            "deferred_at": self.deferred_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ScoringAlgorithmChangedEvent:
    """Published when scoring algorithm weights change. ADR-134."""

    # Required domain fields
    event_id: str
    previous_algorithm_version: str
    new_algorithm_version: str
    previous_weights: Dict[str, float] = field(default_factory=dict)
    new_weights: Dict[str, float] = field(default_factory=dict)
    changed_at: str = ""  # ISO datetime string
    changed_by: str = ""

    # Trailing metadata
    event_sequence: int = 0
    event_type: str = "ScoringAlgorithmChangedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "previous_algorithm_version": self.previous_algorithm_version,
            "new_algorithm_version": self.new_algorithm_version,
            "previous_weights": self.previous_weights,
            "new_weights": self.new_weights,
            "changed_at": self.changed_at,
            "changed_by": self.changed_by,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class GovernanceCapabilitySuspendedEvent:
    """Published when governance auto-suspends a capability. ADR-138."""

    # Required domain fields
    event_id: str
    capability_family_id: str  # UUID
    capability_urn: str  # URN
    consecutive_low_scores: int = 0
    threshold: int = 3  # auto-suspend threshold
    reason: str = ""
    suspended_at: str = ""  # ISO datetime string

    # Trailing metadata
    event_sequence: int = 0
    event_type: str = "GovernanceCapabilitySuspendedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "capability_family_id": self.capability_family_id,
            "capability_urn": self.capability_urn,
            "consecutive_low_scores": self.consecutive_low_scores,
            "threshold": self.threshold,
            "reason": self.reason,
            "suspended_at": self.suspended_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class GovernanceCapabilityUnsuspendedEvent:
    """Published when governance auto-unsuspends a capability. ADR-138."""

    # Required domain fields
    event_id: str
    capability_family_id: str  # UUID
    capability_urn: str  # URN
    consecutive_high_scores: int = 0
    threshold: int = 2  # auto-unsuspend threshold
    reason: str = ""
    unsuspended_at: str = ""  # ISO datetime string

    # Trailing metadata
    event_sequence: int = 0
    event_type: str = "GovernanceCapabilityUnsuspendedEvent"
    event_version: int = 1
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "capability_family_id": self.capability_family_id,
            "capability_urn": self.capability_urn,
            "consecutive_high_scores": self.consecutive_high_scores,
            "threshold": self.threshold,
            "reason": self.reason,
            "unsuspended_at": self.unsuspended_at,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
        }
