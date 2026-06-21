"""AnalystOutput child entity -- Sprint-13. ADR-140."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from karsa.investment_workflow.domain.exceptions import InvalidAnalystOutputError


@dataclass(frozen=True)
class AnalystOutput:
    """Child entity of InvestmentDecision.

    Represents a single analyst's output for a decision.
    Stored as JSONB within the parent aggregate.
    No independent lifecycle.
    """

    analyst_type: str  # AnalystType value
    score: float  # 0.0-10.0
    confidence: float  # 0.0-1.0
    output_text: str
    tools_used: List[str] = field(default_factory=list)
    model_version: str = ""
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    def _validate(self) -> None:
        if not self.analyst_type:
            raise InvalidAnalystOutputError("analyst_type is required")
        if not 0.0 <= self.score <= 10.0:
            raise InvalidAnalystOutputError(
                f"score must be 0.0-10.0, got {self.score}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidAnalystOutputError(
                f"confidence must be 0.0-1.0, got {self.confidence}"
            )
        if not self.output_text:
            raise InvalidAnalystOutputError("output_text is required")
