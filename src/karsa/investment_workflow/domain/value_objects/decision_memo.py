"""DecisionMemo value object -- Sprint-13. ADR-140."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from karsa.investment_workflow.domain.exceptions import InvalidMemoError
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)
from karsa.investment_workflow.domain.value_objects.enums import DecisionType


@dataclass(frozen=True)
class DecisionMemo:
    """Investment decision memo output.

    Structured output from Portfolio Manager synthesis.
    """

    ticker: str
    decision: str  # DecisionType value
    conviction: ConvictionScore
    thesis: str  # 3-4 sentences
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    entry_price: Optional[Decimal] = None
    exit_target: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    position_size_pct: Optional[float] = None
    next_review_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.ticker:
            raise InvalidMemoError("ticker is required")
        valid_decisions = {e.value for e in DecisionType}
        if self.decision not in valid_decisions:
            raise InvalidMemoError(
                f"decision must be one of {valid_decisions}, got {self.decision}"
            )
        if len(self.thesis) < 50:
            raise InvalidMemoError("thesis must be at least 50 characters")
        if self.position_size_pct is not None and not 0.0 < self.position_size_pct <= 100.0:
            raise InvalidMemoError(
                f"position_size_pct must be 0.0-100.0, got {self.position_size_pct}"
            )
