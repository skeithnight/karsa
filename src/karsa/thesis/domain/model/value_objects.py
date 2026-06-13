from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class ThesisState(str, Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    INVALIDATED = "INVALIDATED"
    REALIZED = "REALIZED"
    EXPIRED = "EXPIRED"

class TimeClassification(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    MID_TERM = "MID_TERM"
    LONG_TERM = "LONG_TERM"

class ContributionRole(str, Enum):
    REVIEWER = "REVIEWER"
    APPROVER = "APPROVER"
    REFINER = "REFINER"

class ConfidenceSource(str, Enum):
    MANUAL = "MANUAL"
    MODEL = "MODEL"
    CALIBRATION = "CALIBRATION"
    GOVERNANCE = "GOVERNANCE"

@dataclass(frozen=True)
class ThesisIdentity:
    thesis_id: str

@dataclass(frozen=True)
class HypothesisStructure:
    hypothesis_statement: str
    bull_case: str
    bear_case: str
    assumptions: List[str]
    expected_outcome: str
    invalidation_criteria: List[str]
    success_criteria: List[str]

@dataclass(frozen=True)
class TimeHorizon:
    start_date: str
    target_date: str
    classification: TimeClassification

@dataclass(frozen=True)
class ResearchReference:
    research_id: str
    research_version: str
    research_type: str

@dataclass(frozen=True)
class ThesisContributor:
    contributor_id: str
    contributor_type: str
    contribution_role: ContributionRole

@dataclass(frozen=True)
class ConfidenceModel:
    raw_confidence: float
    calibrated_confidence: Optional[float]
    confidence_source: ConfidenceSource
    confidence_updated_at: str

@dataclass(frozen=True)
class ThesisReviewRecord:
    review_reason: str
    review_type: str
    reviewer_id: str
    reviewed_at: str

@dataclass(frozen=True)
class ThesisContextSnapshot:
    """Frozen snapshot of the Thesis state at a point in time."""
    thesis_id: str
    state: str
    originator: dict
    contributors: list[dict]
    hypothesis: dict
    confidence: dict
    time_horizon: dict
    research_lineage: list[dict]
    aggregate_version: int
