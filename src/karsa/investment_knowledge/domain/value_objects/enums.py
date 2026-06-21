"""Investment Knowledge enums -- Sprint-14."""

from enum import Enum


class DocumentType(str, Enum):
    """Types of research documents."""

    SECTOR_ANALYSIS = "SECTOR_ANALYSIS"
    COMPANY_PROFILE = "COMPANY_PROFILE"
    MARKET_THESIS = "MARKET_THESIS"
    MACRO_VIEW = "MACRO_VIEW"
    DIVIDEND_CALENDAR = "DIVIDEND_CALENDAR"
    CONGLOMERATE_MAP = "CONGLOMERATE_MAP"


class DocumentStatus(str, Enum):
    """Document lifecycle status."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SUPERSEDED = "SUPERSEDED"
