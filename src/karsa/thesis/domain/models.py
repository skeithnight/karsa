from typing import List, Optional
from .value_objects import (
    LifecycleState, AssumptionLifecycleState, 
    ReviewReference, CalibrationReference, AssumptionOutcomeReference
)

class ThesisAssumptionIdentity:
    def __init__(self, assumption_urn: str):
        self.assumption_urn = assumption_urn

class ThesisAssumptionVersion:
    def __init__(self, assumption_urn: str, assumption_version: int,
                 assumption_statement: str, raw_confidence: float,
                 lifecycle_state: AssumptionLifecycleState,
                 assumption_manifest_hash: str,
                 calibrated_confidence_reference: Optional[CalibrationReference] = None):
        self.assumption_urn = assumption_urn
        self.assumption_version = assumption_version
        self.assumption_statement = assumption_statement
        self.raw_confidence = raw_confidence
        self.lifecycle_state = lifecycle_state
        self.assumption_manifest_hash = assumption_manifest_hash
        self.calibrated_confidence_reference = calibrated_confidence_reference

class ThesisDelta:
    def __init__(self, delta_urn: str, delta_manifest_hash: str,
                 added_assumptions: List[str], removed_assumptions: List[str]):
        self.delta_urn = delta_urn
        self.delta_manifest_hash = delta_manifest_hash
        self.added_assumptions = added_assumptions
        self.removed_assumptions = removed_assumptions

class ThesisTransition:
    def __init__(self, transition_urn: str, supersedes_transition_urn: Optional[str],
                 invalidates_transition_urn: Optional[str], delta: ThesisDelta):
        self.transition_urn = transition_urn
        self.supersedes_transition_urn = supersedes_transition_urn
        self.invalidates_transition_urn = invalidates_transition_urn
        self.delta = delta

class ThesisSnapshot:
    def __init__(self, snapshot_urn: str, snapshot_version: int,
                 lifecycle_state: LifecycleState,
                 origin_regime_snapshot_urn: str,
                 supersedes_snapshot_urn: Optional[str],
                 invalidates_snapshot_urn: Optional[str],
                 assumptions: List[ThesisAssumptionVersion]):
        self.snapshot_urn = snapshot_urn
        self.snapshot_version = snapshot_version
        self.lifecycle_state = lifecycle_state
        self.origin_regime_snapshot_urn = origin_regime_snapshot_urn
        self.supersedes_snapshot_urn = supersedes_snapshot_urn
        self.invalidates_snapshot_urn = invalidates_snapshot_urn
        self.assumptions = assumptions

from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.shared.domain.event import DomainEvent
from .events import ThesisProposedEvent, ThesisActivatedEvent

class Thesis(VersionedAggregate):
    def __init__(self, thesis_urn: str, current_snapshot_urn: str,
                 current_status: LifecycleState, aggregate_version: int = 1):
        super().__init__(aggregate_version)
        self.thesis_urn = thesis_urn
        self.aggregate_id = thesis_urn
        self.current_snapshot_urn = current_snapshot_urn
        self.current_status = current_status

    def apply(self, event: DomainEvent):
        if isinstance(event, ThesisProposedEvent):
            self.current_status = LifecycleState.PROPOSED
            self.current_snapshot_urn = event.payload.get("snapshot_urn", self.current_snapshot_urn)
        elif isinstance(event, ThesisActivatedEvent):
            self.current_status = LifecycleState.ACTIVE
            self.current_snapshot_urn = event.payload.get("snapshot_urn", self.current_snapshot_urn)

    def activate(self, new_snapshot_urn: str, causation_id: str, correlation_id: str):
        if self.current_status != LifecycleState.PROPOSED:
            from .exceptions import InvalidLifecycleTransitionError
            raise InvalidLifecycleTransitionError("Only PROPOSED theses can be activated.")
            
        event = ThesisActivatedEvent(
            correlation_id=correlation_id,
            causation_id=causation_id,
            stream_version=self.version + 1,
            payload={"snapshot_urn": new_snapshot_urn}
        )
        self.apply(event)
        self.record_event(event)
