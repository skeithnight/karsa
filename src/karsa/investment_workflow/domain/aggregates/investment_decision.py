"""InvestmentDecision aggregate -- Sprint-13. ADR-140.

Write-once aggregate for investment decision lifecycle.
Same pattern as CapabilityEvolution (ImmutableLedgerEntry).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from karsa.investment_workflow.domain.entities.analyst_output import AnalystOutput
from karsa.investment_workflow.domain.entities.debate_round import DebateRound
from karsa.investment_workflow.domain.exceptions import (
    DuplicateAnalystError,
    InvalidDecisionError,
    InvalidTransitionError,
)
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)
from karsa.investment_workflow.domain.value_objects.decision_memo import DecisionMemo
from karsa.investment_workflow.domain.value_objects.enums import (
    DecisionState,
    VALID_TRANSITIONS,
)


class ImmutableLedgerEntry:
    """Write-once base class. Same pattern as capability_engine."""

    def __setattr__(self, name: str, value: object) -> None:
        if "_initialized" in self.__dict__ and self._initialized:
            raise AttributeError(
                f"Cannot set attribute '{name}' on immutable ledger entry"
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"Cannot delete attribute '{name}' on immutable ledger entry"
        )


@dataclass
class InvestmentDecision(ImmutableLedgerEntry):
    """Aggregate for investment decision lifecycle.

    ADR-140: States PROPOSED → ANALYZING → DEBATING → DECIDING →
    RISK_REVIEW → COMMITTEE_REVIEW → APPROVED/REJECTED.

    Business key: (capability_family_id, ticker, decision_date).
    """

    # Identity
    decision_id: str  # URN
    capability_family_id: str
    ticker: str
    decision_date: str  # ISO date string

    # State
    state: str = DecisionState.PROPOSED.value

    # Child entities
    analyst_outputs: List[AnalystOutput] = field(default_factory=list)
    debate_rounds: List[DebateRound] = field(default_factory=list)

    # Decision output
    memo: Optional[DecisionMemo] = None
    conviction: Optional[ConvictionScore] = None

    # Metadata
    proposed_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._initialized = True
        self._validate()

    def _validate(self) -> None:
        if not self.decision_id:
            raise InvalidDecisionError("decision_id is required")
        if not self.capability_family_id:
            raise InvalidDecisionError("capability_family_id is required")
        if not self.ticker:
            raise InvalidDecisionError("ticker is required")
        if not self.decision_date:
            raise InvalidDecisionError("decision_date is required")
        valid_states = {e.value for e in DecisionState}
        if self.state not in valid_states:
            raise InvalidDecisionError(
                f"state must be one of {valid_states}, got {self.state}"
            )
        # Validate child entities
        for output in self.analyst_outputs:
            output._validate()
        for round in self.debate_rounds:
            round._validate()

    def can_transition_to(self, new_state: str) -> bool:
        """Check if transition to new_state is allowed."""
        current = DecisionState(self.state)
        target = DecisionState(new_state)
        return target in VALID_TRANSITIONS.get(current, set())

    def transition_to(self, new_state: str) -> None:
        """Transition to new state. Raises InvalidTransitionError if not allowed."""
        if not self.can_transition_to(new_state):
            raise InvalidTransitionError(
                f"Cannot transition from {self.state} to {new_state}"
            )
        # Override __setattr__ for this mutation
        object.__setattr__(self, "state", new_state)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def record_analyst_output(self, output: AnalystOutput) -> None:
        """Record an analyst output. Rejects duplicates."""
        # Check for duplicate analyst type
        for existing in self.analyst_outputs:
            if existing.analyst_type == output.analyst_type:
                raise DuplicateAnalystError(
                    f"Analyst {output.analyst_type} already recorded"
                )
        output._validate()
        self.analyst_outputs.append(output)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def record_debate(self, debate: DebateRound) -> None:
        """Record a debate round."""
        debate._validate()
        self.debate_rounds.append(debate)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def set_memo(self, memo: DecisionMemo) -> None:
        """Set the investment memo."""
        object.__setattr__(self, "memo", memo)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def set_conviction(self, conviction: ConvictionScore) -> None:
        """Set the conviction score."""
        object.__setattr__(self, "conviction", conviction)
        object.__setattr__(self, "updated_at", datetime.utcnow())

    @property
    def analyst_scores(self) -> List[float]:
        """Get all analyst scores as a list."""
        return [o.score for o in self.analyst_outputs]

    @property
    def is_terminal(self) -> bool:
        """Check if decision is in a terminal state."""
        return self.state in {
            DecisionState.APPROVED.value,
            DecisionState.REJECTED.value,
        }

    @property
    def latest_debate(self) -> Optional[DebateRound]:
        """Get the most recent debate round."""
        return self.debate_rounds[-1] if self.debate_rounds else None
