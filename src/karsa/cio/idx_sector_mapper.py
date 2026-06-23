"""IDX Sector Mapper — maps Indonesia Stock Exchange tickers to sectors.

Sprint-60: Auto-classifies IDX positions into standard IDX industry sectors.
Applied during CIOProducer.on_fill() to populate the sector exposure grid.
"""

# IDX sector classification based on IDX-IC (Indonesia Stock Exchange Industrial Classification)
IDX_SECTOR_MAP = {
    # Financials
    "BBCA": "Financials", "BBRI": "Financials", "BMRI": "Financials", "BBNI": "Financials",
    "BRIS": "Financials", "BTPS": "Financials", "BGTG": "Financials", "BDMR": "Financials",
    "PNBN": "Financials", "NISP": "Financials", "MEGA": "Financials", "ARTO": "Financials",
    "BBYB": "Financials", "AGRO": "Financials", "BACA": "Financials", "BANK": "Financials",

    # Telecommunications
    "TLKM": "Telecommunications", "EXCL": "Telecommunications", "ISAT": "Telecommunications",
    "FREN": "Telecommunications", "TBIG": "Telecommunications", "TOWR": "Telecommunications",
    "MTEL": "Telecommunications", "SUPR": "Telecommunications",

    # Technology
    "GOTO": "Technology", "BUKA": "Technology", "EMTK": "Technology", "DCII": "Technology",
    "BALI": "Technology", "DNET": "Technology", "LUCK": "Technology",

    # Basic Materials / Mining
    "ANTM": "Basic Materials", "INCO": "Basic Materials", "MDKA": "Basic Materials",
    "TPIA": "Basic Materials", "BRPT": "Basic Materials", "AKRA": "Basic Materials",
    "INTP": "Basic Materials", "SMGR": "Basic Materials", "SMCB": "Basic Materials",
    "BSSR": "Basic Materials", "PTRO": "Basic Materials", "INDY": "Basic Materials",
    "HRUM": "Basic Materials", "ADRO": "Basic Materials", "PTBA": "Basic Materials",
    "ITMG": "Basic Materials", "PGAS": "Basic Materials", "AKPI": "Basic Materials",

    # Consumer Staples
    "UNVR": "Consumer Staples", "ICBP": "Consumer Staples", "INDF": "Consumer Staples",
    "MYOR": "Consumer Staples", "KLBF": "Consumer Staples", "SIDO": "Consumer Staples",
    "HMSP": "Consumer Staples", "GGRM": "Consumer Staples", "CPIN": "Consumer Staples",
    "CLEO": "Consumer Staples", "AISA": "Consumer Staples", "GOOD": "Consumer Staples",

    # Consumer Cyclical
    "ASII": "Consumer Cyclical", "AUTO": "Consumer Cyclical", "SMSM": "Consumer Cyclical",
    "GJTL": "Consumer Cyclical", "LPPF": "Consumer Cyclical", "MAPI": "Consumer Cyclical",
    "ACES": "Consumer Cyclical", "RALS": "Consumer Cyclical", "ERAA": "Consumer Cyclical",
    "MTEL": "Consumer Cyclical", "WOOD": "Consumer Cyclical", "SAFE": "Consumer Cyclical",

    # Energy
    "PGAS": "Energy", "MEDC": "Energy", "ELSA": "Energy", "AKR": "Energy",
    "RAJA": "Energy", "MKPI": "Energy",

    # Healthcare
    "HEAL": "Healthcare", "MIKA": "Healthcare", "SILO": "Healthcare", "PRDA": "Healthcare",

    # Industrials
    "ASGR": "Industrials", "SRTG": "Industrials", "SMBR": "Industrials",
    "BABP": "Industrials",

    # Real Estate
    "BSDE": "Real Estate", "CTRA": "Real Estate", "SMRA": "Real Estate",
    "PWON": "Real Estate", "DILD": "Real Estate", "LPKR": "Real Estate",
    "ASRI": "Real Estate", "PPRO": "Real Estate", "BKSL": "Real Estate",

    # Infrastructure
    "JSMR": "Infrastructure", "WIKA": "Infrastructure", "WSKT": "Infrastructure",
    "PTPP": "Infrastructure", "ADHI": "Infrastructure",

    # Transportation
    "GIAA": "Transportation", "BIRD": "Transportation", "SMDR": "Transportation",
    "ASSA": "Transportation", "SHIP": "Transportation",
}

DEFAULT_SECTOR = "Other"


def classify_idx_ticker(ticker: str) -> str:
    """Classify an IDX ticker to its sector.

    Args:
        ticker: IDX ticker symbol (e.g., "BBCA", "TLKM").

    Returns:
        Sector name string (e.g., "Financials", "Telecommunications").
    """
    return IDX_SECTOR_MAP.get(ticker.upper(), DEFAULT_SECTOR)


def get_all_sectors() -> list:
    """Get all unique sectors in the mapper."""
    return sorted(set(IDX_SECTOR_MAP.values()))
