from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from .value_objects import SignalConfidenceScore, RegimeClassification

class IllegalStateTransitionError(Exception):
    pass

class TerminalStateError(Exception):
    pass

@dataclass
class RegimeSession:
    session_urn: str
    state: str = "INITIATED"
    aggregate_version: int = 1

    def start_analyzing(self):
        if self.state != "INITIATED":
            raise IllegalStateTransitionError(f"Cannot transition to ANALYZING from {self.state}")
        self.state = "ANALYZING"
        self.aggregate_version += 1

    def complete_classification(self):
        if self.state != "ANALYZING":
            raise IllegalStateTransitionError(f"Cannot transition to CLASSIFIED from {self.state}")
        self.state = "CLASSIFIED"
        self.aggregate_version += 1

    def seal(self):
        if self.state != "CLASSIFIED":
            raise IllegalStateTransitionError(f"Cannot transition to SEALED from {self.state}")
        self.state = "SEALED"
        self.aggregate_version += 1

    def ensure_not_terminal(self):
        if self.state == "SEALED":
            raise TerminalStateError("Session is already SEALED")

@dataclass(frozen=True)
class RegimeSnapshot:
    snapshot_urn: str
    segment_urn: str
    horizon_urn: str
    snapshot_date: str
    regime_classification: RegimeClassification
    confidence_score: SignalConfidenceScore
    regime_manifest_hash: str
    evidence_manifest_hash: str
    methodology_metadata: dict
    
    # Internal uniqueness is defined by (segment_urn, horizon_urn, snapshot_date)
    @property
    def natural_key(self) -> tuple:
        return (self.segment_urn, self.horizon_urn, self.snapshot_date)

@dataclass
class RegimeTransition:
    transition_urn: str
    from_regime: RegimeClassification
    to_regime: RegimeClassification
    transition_manifest_hash: str
    supersedes_transition_urn: Optional[str] = None
    invalidates_transition_urn: Optional[str] = None
    aggregate_version: int = 1

    def supersede(self, new_transition_urn: str):
        self.supersedes_transition_urn = new_transition_urn
        self.aggregate_version += 1

    def invalidate(self, invalidating_urn: str):
        self.invalidates_transition_urn = invalidating_urn
        self.aggregate_version += 1
