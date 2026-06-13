from dataclasses import dataclass
from typing import List, Optional
from karsa.shared.domain.identity import OriginatorIdentity
from karsa.thesis.domain.model.value_objects import (
    HypothesisStructure, TimeHorizon, ResearchReference,
    ConfidenceModel, ThesisContributor, ThesisReviewRecord
)

@dataclass
class ProposeThesisCommand:
    thesis_id: str
    originator: OriginatorIdentity
    hypothesis: HypothesisStructure
    confidence: ConfidenceModel
    time_horizon: TimeHorizon
    research_lineage: List[ResearchReference]

@dataclass
class AddContributorCommand:
    thesis_id: str
    contributor: ThesisContributor

@dataclass
class UpdateConfidenceCommand:
    thesis_id: str
    confidence: ConfidenceModel

@dataclass
class InvalidateThesisCommand:
    thesis_id: str

@dataclass
class GovernanceDecisionPayload:
    thesis_id: str
    governance_decision: str  # APPROVED or REJECTED
    reviewer_id: str
    reviewed_at: str
    reason: str

@dataclass
class RecordReviewCommand:
    thesis_id: str
    review: ThesisReviewRecord
