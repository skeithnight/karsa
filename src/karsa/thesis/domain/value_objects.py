from dataclasses import dataclass
from enum import Enum

class LifecycleState(Enum):
    PROPOSED = "PROPOSED"
    REVIEWED = "REVIEWED"
    ACTIVE = "ACTIVE"
    CHALLENGED = "CHALLENGED"
    REFINING = "REFINING"
    INVALIDATED = "INVALIDATED"
    RETIRED = "RETIRED"

class AssumptionLifecycleState(Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"

@dataclass(frozen=True)
class ReviewReference:
    review_urn: str
    review_manifest_hash: str

@dataclass(frozen=True)
class CalibrationReference:
    calibration_urn: str
    calibration_manifest_hash: str

@dataclass(frozen=True)
class AssumptionOutcomeReference:
    outcome_reference_urn: str
    performance_window: str
    evaluation_horizon: str
    outcome_source: str
    outcome_manifest_hash: str
