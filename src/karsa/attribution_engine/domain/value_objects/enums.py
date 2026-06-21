"""Attribution Engine enums — Sprint-09."""
from enum import Enum


class AttributionDimension(str, Enum):
    THESIS = "THESIS"
    EXECUTION = "EXECUTION"
    ALLOCATION = "ALLOCATION"
    REGIME = "REGIME"
    RESIDUAL = "RESIDUAL"


class AttributionStatus(str, Enum):
    CANONICAL = "CANONICAL"
    SUPERSEDED = "SUPERSEDED"
    EXPERIMENTAL = "EXPERIMENTAL"


class QualitySource(str, Enum):
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    THESIS_ENGINE = "THESIS_ENGINE"
    EXECUTION_ENGINE = "EXECUTION_ENGINE"
    CAPITAL_ALLOCATION_ENGINE = "CAPITAL_ALLOCATION_ENGINE"
