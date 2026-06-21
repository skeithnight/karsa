"""Capability Engine enums -- Sprint-11."""

from enum import Enum


class EvolutionTriggerType(str, Enum):
    """What initiated this capability evolution. ADR-120."""

    REVIEW_FINDING = "REVIEW_FINDING"
    ATTRIBUTION_INSIGHT = "ATTRIBUTION_INSIGHT"
    EXECUTION_OUTCOME = "EXECUTION_OUTCOME"
    GOVERNANCE_ACTION = "GOVERNANCE_ACTION"


class EvolutionType(str, Enum):
    """Nature of the capability change. ADR-120."""

    SCORE_ADJUSTMENT = "SCORE_ADJUSTMENT"
    LIFECYCLE_CHANGE = "LIFECYCLE_CHANGE"
    CONTRACT_UPDATE = "CONTRACT_UPDATE"
    DEPENDENCY_CHANGE = "DEPENDENCY_CHANGE"
    CAPABILITY_RETIREMENT = "CAPABILITY_RETIREMENT"


class EvolutionStatus(str, Enum):
    """Canonical governance status for evolution records. ADR-133."""

    CANONICAL = "CANONICAL"
    SUPERSEDED = "SUPERSEDED"
    EXPERIMENTAL = "EXPERIMENTAL"


class ScoreComponentName(str, Enum):
    """Component names for the 4-factor health score. ADR-132."""

    EXECUTION_QUALITY = "EXECUTION_QUALITY"
    ATTRIBUTION_ALIGNMENT = "ATTRIBUTION_ALIGNMENT"
    REVIEW_SENTIMENT = "REVIEW_SENTIMENT"
    REGIME_FITNESS = "REGIME_FITNESS"


class ScoreTrend(str, Enum):
    """Direction of score movement over recent evaluations. ADR-136."""

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    UNKNOWN = "UNKNOWN"
