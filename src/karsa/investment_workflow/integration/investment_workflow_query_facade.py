"""InvestmentWorkflowQueryFacade -- Sprint-13. ADR-140.

Public query interface for investment workflow.
External bounded contexts use this facade to read decision data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from karsa.investment_workflow.infrastructure.repositories.investment_decision_repository import (
    InvestmentDecisionRepository,
)


@dataclass(frozen=True)
class DecisionDTO:
    """Public contract for decision data."""

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


class InvestmentWorkflowQueryFacade:
    """Public query interface for investment workflow.

    Returns only DTOs. Never exposes domain internals.
    """

    def __init__(
        self, decision_repo: InvestmentDecisionRepository
    ) -> None:
        self._decision_repo = decision_repo

    def get_decision(
        self, decision_id: str
    ) -> Optional[DecisionDTO]:
        """Get a decision by ID."""
        decision = self._decision_repo.get_by_id(decision_id)
        if decision is None:
            return None
        return self._to_dto(decision)

    def get_decisions_by_ticker(
        self, ticker: str
    ) -> List[DecisionDTO]:
        """Get all decisions for a ticker across all families."""
        all_decisions = self._decision_repo.list_decisions(
            page=1, size=10000
        )
        return [
            self._to_dto(d)
            for d in all_decisions
            if d.ticker == ticker
        ]

    def get_decisions_by_family(
        self, capability_family_id: str
    ) -> List[DecisionDTO]:
        """Get all decisions for a capability family."""
        all_decisions = self._decision_repo.list_decisions(
            page=1, size=10000
        )
        return [
            self._to_dto(d)
            for d in all_decisions
            if d.capability_family_id == capability_family_id
        ]

    def _to_dto(self, decision) -> DecisionDTO:
        """Map domain aggregate to public DTO."""
        conviction_level = None
        memo_decision = None
        entry_price = None
        exit_target = None

        if decision.conviction:
            conviction_level = decision.conviction.level

        if decision.memo:
            memo_decision = decision.memo.decision
            entry_price = (
                str(decision.memo.entry_price)
                if decision.memo.entry_price
                else None
            )
            exit_target = (
                str(decision.memo.exit_target)
                if decision.memo.exit_target
                else None
            )

        return DecisionDTO(
            decision_id=decision.decision_id,
            capability_family_id=decision.capability_family_id,
            ticker=decision.ticker,
            decision_date=decision.decision_date,
            state=decision.state,
            analyst_count=len(decision.analyst_outputs),
            debate_count=len(decision.debate_rounds),
            has_memo=decision.memo is not None,
            conviction_level=conviction_level,
            memo_decision=memo_decision,
            entry_price=entry_price,
            exit_target=exit_target,
            proposed_by=decision.proposed_by,
            created_at=decision.created_at,
        )
