from typing import List, Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.shared.domain.identity import OriginatorIdentity
from karsa.thesis.domain.model.value_objects import (
    ThesisIdentity, ThesisState, ThesisContributor, HypothesisStructure,
    ConfidenceModel, TimeHorizon, ResearchReference
)
from karsa.thesis.domain.model.exceptions import (
    InvalidThesisStateTransitionError, MissingOriginatorError,
    DuplicateContributorError, InvalidConfidenceError
)

class Thesis(VersionedAggregate):
    """The canonical hypothesis structure."""
    
    def __init__(self, 
                 thesis_id: str,
                 originator: OriginatorIdentity,
                 hypothesis: HypothesisStructure,
                 confidence: ConfidenceModel,
                 time_horizon: TimeHorizon,
                 research_lineage: List[ResearchReference],
                 contributors: Optional[List[ThesisContributor]] = None,
                 state: ThesisState = ThesisState.DRAFT,
                 aggregate_version: int = 1):
        super().__init__(aggregate_version=aggregate_version)
        self.identity = ThesisIdentity(thesis_id)
        if not originator:
            raise MissingOriginatorError("Thesis must have an originator.")
        self.originator = originator
        self.hypothesis = hypothesis
        
        self._validate_confidence(confidence)
        self.confidence = confidence
        
        self.time_horizon = time_horizon
        self.research_lineage = research_lineage or []
        self.contributors = contributors or []
        self.state = state
        
    def _validate_confidence(self, confidence: ConfidenceModel):
        if not (0.0 <= confidence.raw_confidence <= 1.0):
            raise InvalidConfidenceError("raw_confidence must be between 0.0 and 1.0")
        if confidence.calibrated_confidence is not None:
            if not (0.0 <= confidence.calibrated_confidence <= 1.0):
                raise InvalidConfidenceError("calibrated_confidence must be between 0.0 and 1.0")
                
    def propose(self):
        if self.state != ThesisState.DRAFT:
            raise InvalidThesisStateTransitionError(f"Cannot propose thesis from state {self.state}")
        self.state = ThesisState.PROPOSED
        self.increment_version()
        
    def activate(self):
        if self.state != ThesisState.PROPOSED:
            raise InvalidThesisStateTransitionError(f"Cannot activate thesis from state {self.state}")
        self.state = ThesisState.ACTIVE
        self.increment_version()
        
    def reject(self):
        if self.state != ThesisState.PROPOSED:
            raise InvalidThesisStateTransitionError(f"Cannot reject thesis from state {self.state}")
        self.state = ThesisState.REJECTED
        self.increment_version()
        
    def update_confidence(self, new_confidence: ConfidenceModel):
        self._validate_confidence(new_confidence)
        self.confidence = new_confidence
        self.increment_version()
        
    def invalidate(self):
        if self.state != ThesisState.ACTIVE:
            raise InvalidThesisStateTransitionError(f"Cannot invalidate thesis from state {self.state}")
        self.state = ThesisState.INVALIDATED
        self.increment_version()
        
    def realize(self):
        if self.state != ThesisState.ACTIVE:
            raise InvalidThesisStateTransitionError(f"Cannot realize thesis from state {self.state}")
        self.state = ThesisState.REALIZED
        self.increment_version()
        
    def add_contributor(self, contributor: ThesisContributor):
        if contributor.contribution_role == "AUTHOR":
            raise ValueError("Role AUTHOR is reserved for the Originator.")
        if any(c.contributor_id == contributor.contributor_id for c in self.contributors):
            raise DuplicateContributorError("Contributor already exists.")
        self.contributors.append(contributor)
        self.increment_version()
