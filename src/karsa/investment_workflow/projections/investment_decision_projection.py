"""InvestmentDecisionProjection DTO -- Sprint-13. ADR-140.

Read model for investment decision queries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class InvestmentDecisionProjection:
    """Read model for investment decision lifecycle.

    Rebuilt from investment_decision repository.
    Exposes decision state, analyst scores, debate summary, and memo.
    """

    decision_id: str
    capability_family_id: str
    ticker: str
    decision_date: str
    state: str

    # Analyst summary
    analyst_count: int = 0
    analyst_scores: Dict[str, float] = field(default_factory=dict)

    # Debate summary
    debate_count: int = 0
    latest_bull_conviction: Optional[str] = None
    latest_bear_conviction: Optional[str] = None

    # Memo summary
    has_memo: bool = False
    memo_decision: Optional[str] = None
    conviction_level: Optional[str] = None
    conviction_score: Optional[float] = None
    entry_price: Optional[str] = None
    exit_target: Optional[str] = None
    stop_loss: Optional[str] = None
    position_size_pct: Optional[float] = None
    thesis_summary: Optional[str] = None

    # Metadata
    proposed_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.capability_family_id:
            raise ValueError("capability_family_id is required")
        if not self.ticker:
            raise ValueError("ticker is required")
