"""Investment Attribution enums -- Sprint-18."""

from enum import Enum


class AttributionDimension(str, Enum):
    """Dimensions of performance attribution."""

    SELECTION = "SELECTION"  # Stock picking
    ALLOCATION = "ALLOCATION"  # Position sizing
    BETA = "BETA"  # Market exposure
    RESIDUAL = "RESIDUAL"  # Fees, friction, unexplained


class PerformancePeriod(str, Enum):
    """Time periods for performance measurement."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MTD = "MTD"
    QTD = "QTD"
    YTD = "YTD"
    ONE_YEAR = "1Y"
    INCEPTION = "INCEPTION"


class WinRateCategory(str, Enum):
    """Categories for win rate analysis."""

    FUNDAMENTAL = "FUNDAMENTAL"
    TECHNICAL = "TECHNICAL"
    SENTIMENT = "SENTIMENT"
    MACRO = "MACRO"
    OVERALL = "OVERALL"
