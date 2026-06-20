from typing import List, Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.shared.domain.event import DomainEvent
from .events import (
    ThesisProposedEvent, ThesisActivatedEvent, ThesisChallengedEvent, 
    ThesisRefinedEvent, ThesisInvalidatedEvent, ThesisRetiredEvent
)
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

class ThesisAssumption:
    def __init__(self, assumption_urn: str, statement: str):
        self.assumption_urn = assumption_urn
        self.statement = statement
        self.is_valid = True

class Thesis(VersionedAggregate):
    def __init__(self, thesis_urn: str, author_urn: str, regime_urn: str):
        super().__init__(1)
        self.thesis_urn = thesis_urn
        self.aggregate_id = thesis_urn
        self.title = ""
        self.summary = ""
        self.rationale = ""
        self.confidence = 0.0
        self.author_urn = author_urn
        self.regime_urn = regime_urn
        self.current_status = LifecycleState.PROPOSED
        self.assumptions: List[ThesisAssumption] = []
        self.governance_trail = []

    def apply(self, event: DomainEvent):
        if isinstance(event, ThesisProposedEvent):
            self.title = event.payload.get("title", "")
            self.summary = event.payload.get("summary", "")
            self.rationale = event.payload.get("rationale", "")
            self.confidence = event.payload.get("confidence", 0.0)
            for a_data in event.payload.get("assumptions", []):
                self.assumptions.append(ThesisAssumption(a_data["urn"], a_data["statement"]))
            self.current_status = LifecycleState.PROPOSED
        elif isinstance(event, ThesisActivatedEvent):
            self.current_status = LifecycleState.ACTIVE
            self.governance_trail.append({
                "action": "ACTIVATED",
                "actor": event.payload.get("activator_urn"),
                "rationale": event.payload.get("activation_rationale")
            })
        elif isinstance(event, ThesisChallengedEvent):
            self.current_status = LifecycleState.CHALLENGED
        elif isinstance(event, ThesisRefinedEvent):
            self.confidence = event.payload.get("new_confidence", self.confidence)
            self.rationale = event.payload.get("new_rationale", self.rationale)
            self.current_status = LifecycleState.ACTIVE
        elif isinstance(event, ThesisInvalidatedEvent):
            self.current_status = LifecycleState.INVALIDATED
            invalidated_urns = event.payload.get("invalidated_assumption_urns", [])
            for a in self.assumptions:
                if a.assumption_urn in invalidated_urns:
                    a.is_valid = False
            self.governance_trail.append({
                "action": "INVALIDATED",
                "actor": event.payload.get("invalidator_urn"),
                "rationale": event.payload.get("invalidation_rationale")
            })
        elif isinstance(event, ThesisRetiredEvent):
            self.current_status = LifecycleState.RETIRED
            self.governance_trail.append({
                "action": "RETIRED",
                "actor": event.payload.get("retirer_urn"),
                "rationale": event.payload.get("retirement_rationale")
            })
