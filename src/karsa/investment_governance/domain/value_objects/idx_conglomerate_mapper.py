"""IDX Conglomerate Mapper -- Sprint-59.

Maps IDX tickers to their parent conglomerate groups as defined in
docs/investment_context/MANDATE.md (Conglomerate Exposure section).

Provides constant-time lookup for compliance checks and exposure aggregation.
"""

from typing import Dict, List, Optional, Tuple

# Conglomerate group definitions: (group_name, tickers, max_exposure_pct)
CONGLOMERATE_GROUPS: List[Tuple[str, List[str], float]] = [
    ("Djarum/BCA", ["BBCA", "BGTN"], 0.15),
    ("Astra", ["ASII", "AUTO", "SMSM"], 0.12),
    ("Sinar Mas", ["BMRI", "SMGR", "Djarum"], 0.10),
    ("Salim", ["ICBP", "INDF"], 0.08),
    ("Lippo", ["LPKR", "LPPF"], 0.05),
    ("Prajogo", ["MEDC", "MBSS"], 0.08),
    ("Bakrie", ["BKSL", "BIPI", "ANTM"], 0.05),
]

# Flat ticker -> (group_name, max_exposure_pct) lookup
CONGLOMERATE_MAP: Dict[str, Tuple[str, float]] = {}
for _group, _tickers, _limit in CONGLOMERATE_GROUPS:
    for _ticker in _tickers:
        CONGLOMERATE_MAP[_ticker.upper()] = (_group, _limit)

# Group name -> max exposure pct
CONGLOMERATE_LIMITS: Dict[str, float] = {
    group: limit for group, _, limit in CONGLOMERATE_GROUPS
}


def get_conglomerate_group(ticker: str) -> Optional[str]:
    """Return the conglomerate group name for a ticker, or None if not mapped.

    Args:
        ticker: IDX stock ticker (case-insensitive).

    Returns:
        Conglomerate group name or None.
    """
    entry = CONGLOMERATE_MAP.get(ticker.upper())
    return entry[0] if entry else None


def get_conglomerate_limit(ticker: str) -> Optional[float]:
    """Return the max group exposure limit for a ticker's conglomerate.

    Args:
        ticker: IDX stock ticker (case-insensitive).

    Returns:
        Max exposure as a decimal (e.g. 0.15 = 15%) or None.
    """
    entry = CONGLOMERATE_MAP.get(ticker.upper())
    return entry[1] if entry else None


def get_group_tickers(group_name: str) -> List[str]:
    """Return all tickers belonging to a conglomerate group.

    Args:
        group_name: Conglomerate group name (e.g. "Astra").

    Returns:
        List of tickers, or empty list if group not found.
    """
    for group, tickers, _ in CONGLOMERATE_GROUPS:
        if group == group_name:
            return list(tickers)
    return []


def is_conglomerate_ticker(ticker: str) -> bool:
    """Check whether a ticker belongs to any tracked conglomerate."""
    return ticker.upper() in CONGLOMERATE_MAP
