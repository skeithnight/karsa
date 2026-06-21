"""Review Engine enums — Sprint-10."""
from enum import Enum


class ReviewType(str, Enum):
    WORKER = "WORKER"
    THESIS = "THESIS"
    ALLOCATION = "ALLOCATION"
    REGIME = "REGIME"
    PORTFOLIO = "PORTFOLIO"


class FindingType(str, Enum):
    OBSERVATION = "OBSERVATION"
    CONCERN = "CONCERN"
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"


class FindingSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationType(str, Enum):
    ADJUST_ALLOCATION = "ADJUST_ALLOCATION"
    PAUSE_WORKER = "PAUSE_WORKER"
    ESCALATE = "ESCALATE"
    NO_ACTION = "NO_ACTION"


class RecommendationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ReviewStatus(str, Enum):
    CANONICAL = "CANONICAL"
    SUPERSEDED = "SUPERSEDED"
    EXPERIMENTAL = "EXPERIMENTAL"


class QualitySource(str, Enum):
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PERFORMANCE_ENGINE = "PERFORMANCE_ENGINE"
    ATTRIBUTION_ENGINE = "ATTRIBUTION_ENGINE"
