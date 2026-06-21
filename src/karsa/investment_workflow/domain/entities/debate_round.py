"""DebateRound child entity -- Sprint-13. ADR-140."""

from dataclasses import dataclass, field
from datetime import datetime

from karsa.investment_workflow.domain.exceptions import InvalidDebateError
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)


@dataclass(frozen=True)
class DebateRound:
    """Child entity of InvestmentDecision.

    Represents a single bull/bear debate round.
    Stored as JSONB within the parent aggregate.
    """

    round_number: int
    bull_memo: str
    bear_memo: str
    bull_conviction: ConvictionScore
    bear_conviction: ConvictionScore
    debated_at: datetime = field(default_factory=datetime.utcnow)

    def _validate(self) -> None:
        if self.round_number < 1:
            raise InvalidDebateError(
                f"round_number must be >= 1, got {self.round_number}"
            )
        if len(self.bull_memo) < 50:
            raise InvalidDebateError("bull_memo must be at least 50 characters")
        if len(self.bear_memo) < 50:
            raise InvalidDebateError("bear_memo must be at least 50 characters")
