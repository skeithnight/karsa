"""InvestmentWorkflowCommandFacade -- Sprint-13. ADR-140.

Public command interface for investment workflow.
External bounded contexts use this facade.
No domain types leak through the public API.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from karsa.investment_workflow.application.investment_decision_service import (
    AnalystCommand,
    DecisionCommand,
    DecisionResult,
    DebateCommand,
    InvestmentDecisionService,
    MemoCommand,
)
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)


@dataclass
class CommandResult:
    """Public result contract for command execution."""

    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class InvestmentWorkflowCommandFacade:
    """Public command interface for investment workflow.

    Translates contracts into internal service calls.
    External contexts see only this facade and CommandResult.
    """

    def __init__(
        self, decision_service: InvestmentDecisionService
    ) -> None:
        self._decision_service = decision_service

    def propose_decision(
        self,
        capability_family_id: str,
        ticker: str,
        decision_date: str,
        proposed_by: str = "",
    ) -> CommandResult:
        """Propose a new investment decision."""
        cmd = DecisionCommand(
            capability_family_id=capability_family_id,
            ticker=ticker,
            decision_date=decision_date,
            proposed_by=proposed_by,
        )
        result = self._decision_service.propose_decision(cmd)
        return self._to_response(result)

    def record_analyst(
        self,
        decision_id: str,
        analyst_type: str,
        score: float,
        confidence: float,
        output_text: str,
        tools_used: Optional[List[str]] = None,
        model_version: str = "",
    ) -> CommandResult:
        """Record an analyst output."""
        cmd = AnalystCommand(
            decision_id=decision_id,
            analyst_type=analyst_type,
            score=score,
            confidence=confidence,
            output_text=output_text,
            tools_used=tools_used,
            model_version=model_version,
        )
        result = self._decision_service.record_analyst_output(cmd)
        return self._to_response(result)

    def record_debate(
        self,
        decision_id: str,
        round_number: int,
        bull_memo: str,
        bear_memo: str,
        bull_level: str,
        bull_score: float,
        bull_agreement: int,
        bear_level: str,
        bear_score: float,
        bear_agreement: int,
    ) -> CommandResult:
        """Record a debate round."""
        cmd = DebateCommand(
            decision_id=decision_id,
            round_number=round_number,
            bull_memo=bull_memo,
            bear_memo=bear_memo,
            bull_conviction=ConvictionScore(
                level=bull_level,
                numeric_score=bull_score,
                analyst_agreement=bull_agreement,
            ),
            bear_conviction=ConvictionScore(
                level=bear_level,
                numeric_score=bear_score,
                analyst_agreement=bear_agreement,
            ),
        )
        result = self._decision_service.record_debate(cmd)
        return self._to_response(result)

    def create_memo(
        self,
        decision_id: str,
        ticker: str,
        decision: str,
        conviction_level: str,
        conviction_score: float,
        conviction_agreement: int,
        thesis: str,
        entry_price: Optional[float] = None,
        exit_target: Optional[float] = None,
        stop_loss: Optional[float] = None,
        position_size_pct: Optional[float] = None,
    ) -> CommandResult:
        """Create investment memo."""
        cmd = MemoCommand(
            decision_id=decision_id,
            ticker=ticker,
            decision=decision,
            conviction=ConvictionScore(
                level=conviction_level,
                numeric_score=conviction_score,
                analyst_agreement=conviction_agreement,
            ),
            thesis=thesis,
            entry_price=entry_price,
            exit_target=exit_target,
            stop_loss=stop_loss,
            position_size_pct=position_size_pct,
        )
        result = self._decision_service.create_memo(cmd)
        return self._to_response(result)

    def approve(
        self, decision_id: str, approved_by: str
    ) -> CommandResult:
        """Approve a decision."""
        result = self._decision_service.approve_decision(
            decision_id, approved_by
        )
        return self._to_response(result)

    def reject(
        self, decision_id: str, rejected_by: str, reason: str
    ) -> CommandResult:
        """Reject a decision."""
        result = self._decision_service.reject_decision(
            decision_id, rejected_by, reason
        )
        return self._to_response(result)

    def revise(
        self, decision_id: str, reason: str
    ) -> CommandResult:
        """Revise a decision."""
        result = self._decision_service.revise_decision(
            decision_id, reason
        )
        return self._to_response(result)

    def _to_response(self, result: DecisionResult) -> CommandResult:
        """Map internal result to public response."""
        return CommandResult(
            success=result.success,
            message=result.message,
            data={
                "decision_id": result.decision_id,
            }
            if result.decision_id
            else None,
        )
