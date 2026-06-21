"""Investment Governance enums -- Sprint-17."""

from enum import Enum


class ComplianceStatus(str, Enum):
    """Result of a compliance check."""

    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"  # Within 10% of limit
    VIOLATION = "VIOLATION"  # Exceeds limit


class MandateRuleType(str, Enum):
    """Types of mandate rules."""

    SECTOR_LIMIT = "SECTOR_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    CONGLOMERATE_LIMIT = "CONGLOMERATE_LIMIT"
    SINGLE_STOCK_LIMIT = "SINGLE_STOCK_LIMIT"
    BETA_RANGE = "BETA_RANGE"
    VOLATILITY_LIMIT = "VOLATILITY_LIMIT"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    LIQUIDITY_LIMIT = "LIQUIDITY_LIMIT"
