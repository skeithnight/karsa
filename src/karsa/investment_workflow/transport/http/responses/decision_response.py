"""DecisionResponse -- Sprint-13. Wave-1G."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DecisionResponse(BaseModel):
    """Response for investment decision queries."""

    decision_id: str
    capability_family_id: str
    ticker: str
    decision_date: str
    state: str
    analyst_count: int = 0
    debate_count: int = 0
    has_memo: bool = False
    conviction_level: Optional[str] = None
    memo_decision: Optional[str] = None
    entry_price: Optional[str] = None
    exit_target: Optional[str] = None
    proposed_by: str = ""
    created_at: Optional[datetime] = None
