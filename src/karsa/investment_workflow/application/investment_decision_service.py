"""InvestmentDecisionService -- Sprint-13. ADR-140.

Command handler for investment decision lifecycle.

Note: Aggregate save and outbox event publish are not fully atomic
in this in-memory implementation. In production (Postgres), both
would be in the same database transaction.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from karsa.investment_workflow.domain.aggregates.investment_decision import (
    InvestmentDecision,
)
from karsa.investment_workflow.domain.entities.analyst_output import AnalystOutput
from karsa.investment_workflow.domain.entities.debate_round import DebateRound
from karsa.investment_workflow.domain.events.investment_workflow_events import (
    AnalystOutputRecordedEvent,
    DecisionApprovedEvent,
    DecisionMemoCreatedEvent,
    DecisionRejectedEvent,
    DecisionRevisedEvent,
    DebateCompletedEvent,
    InvestmentDecisionProposedEvent,
)
from karsa.investment_workflow.domain.exceptions import (
    DuplicateAnalystError,
    InvalidTransitionError,
)
from karsa.investment_workflow.domain.value_objects.conviction_score import (
    ConvictionScore,
)
from karsa.investment_workflow.domain.value_objects.decision_memo import (
    DecisionMemo,
)
from karsa.investment_workflow.domain.value_objects.enums import DecisionState
from karsa.investment_workflow.application.ports.investment_outbox_port import (
    InvestmentOutboxEvent,
    InvestmentOutboxPort,
)
from karsa.investment_workflow.infrastructure.repositories.investment_decision_repository import (
    InvestmentDecisionRepository,
)


@dataclass
class DecisionCommand:
    """Input DTO for decision operations."""

    capability_family_id: str
    ticker: str
    decision_date: str
    proposed_by: str = ""


@dataclass
class AnalystCommand:
    """Input DTO for recording analyst output."""

    decision_id: str
    analyst_type: str
    score: float
    confidence: float
    output_text: str
    tools_used: Optional[List[str]] = None
    model_version: str = ""


@dataclass
class DebateCommand:
    """Input DTO for recording debate."""

    decision_id: str
    round_number: int
    bull_memo: str
    bear_memo: str
    bull_conviction: ConvictionScore
    bear_conviction: ConvictionScore


@dataclass
class MemoCommand:
    """Input DTO for creating memo."""

    decision_id: str
    ticker: str
    decision: str
    conviction: ConvictionScore
    thesis: str
    entry_price: Optional[float] = None
    exit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size_pct: Optional[float] = None


@dataclass
class DecisionResult:
    """Output DTO from decision operations."""

    success: bool
    message: str
    decision_id: Optional[str] = None
    events: Optional[List] = None


class InvestmentDecisionService:
    """Command handler for investment decision lifecycle."""

    def __init__(
        self,
        decision_repo: InvestmentDecisionRepository,
        outbox_repo: InvestmentOutboxPort,
    ) -> None:
        self._decision_repo = decision_repo
        self._outbox_repo = outbox_repo

    def propose_decision(self, command: DecisionCommand) -> DecisionResult:
        """Create a new investment decision."""
        decision_id = f"urn:karsa:investment:decision:{uuid.uuid4().hex}"

        decision = InvestmentDecision(
            decision_id=decision_id,
            capability_family_id=command.capability_family_id,
            ticker=command.ticker,
            decision_date=command.decision_date,
            proposed_by=command.proposed_by,
        )

        saved = self._decision_repo.save(decision)
        if not saved:
            return DecisionResult(
                success=False,
                message="Duplicate decision for this family/ticker/date",
            )

        event = InvestmentDecisionProposedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=decision_id,
            capability_family_id=command.capability_family_id,
            ticker=command.ticker,
            proposed_by=command.proposed_by,
            proposed_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, command.capability_family_id)

        return DecisionResult(
            success=True,
            message="Decision proposed",
            decision_id=decision_id,
            events=[event],
        )

    def record_analyst_output(self, command: AnalystCommand) -> DecisionResult:
        """Record an analyst output on a decision.

        Requires decision to be in ANALYZING state.
        """
        decision = self._decision_repo.get_by_id(command.decision_id)
        if decision is None:
            return DecisionResult(
                success=False, message="Decision not found"
            )

        # State guard: must be in ANALYZING to record analyst output
        if decision.state != DecisionState.ANALYZING.value:
            return DecisionResult(
                success=False,
                message=f"Cannot record analyst in state {decision.state}, must be ANALYZING",
            )

        output = AnalystOutput(
            analyst_type=command.analyst_type,
            score=command.score,
            confidence=command.confidence,
            output_text=command.output_text,
            tools_used=command.tools_used or [],
            model_version=command.model_version,
        )

        try:
            decision.record_analyst_output(output)
        except DuplicateAnalystError as e:
            return DecisionResult(success=False, message=str(e))

        self._decision_repo.save(decision)

        event = AnalystOutputRecordedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=command.decision_id,
            analyst_type=command.analyst_type,
            score=command.score,
            confidence=command.confidence,
            recorded_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, decision.capability_family_id)

        return DecisionResult(
            success=True,
            message=f"Analyst {command.analyst_type} recorded",
            decision_id=command.decision_id,
            events=[event],
        )

    def record_debate(self, command: DebateCommand) -> DecisionResult:
        """Record a debate round on a decision."""
        decision = self._decision_repo.get_by_id(command.decision_id)
        if decision is None:
            return DecisionResult(
                success=False, message="Decision not found"
            )

        debate = DebateRound(
            round_number=command.round_number,
            bull_memo=command.bull_memo,
            bear_memo=command.bear_memo,
            bull_conviction=command.bull_conviction,
            bear_conviction=command.bear_conviction,
        )

        decision.record_debate(debate)
        self._decision_repo.save(decision)

        event = DebateCompletedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=command.decision_id,
            round_count=command.round_number,
            bull_conviction_level=command.bull_conviction.level,
            bear_conviction_level=command.bear_conviction.level,
            completed_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, decision.capability_family_id)

        return DecisionResult(
            success=True,
            message="Debate recorded",
            decision_id=command.decision_id,
            events=[event],
        )

    def create_memo(self, command: MemoCommand) -> DecisionResult:
        """Create investment memo and transition to RISK_REVIEW.

        Requires decision to be in DECIDING state.
        """
        decision = self._decision_repo.get_by_id(command.decision_id)
        if decision is None:
            return DecisionResult(
                success=False, message="Decision not found"
            )

        # State guard: must be in DECIDING to create memo
        if decision.state != DecisionState.DECIDING.value:
            return DecisionResult(
                success=False,
                message=f"Cannot create memo in state {decision.state}, must be DECIDING",
            )

        memo = DecisionMemo(
            ticker=command.ticker,
            decision=command.decision,
            conviction=command.conviction,
            thesis=command.thesis,
            entry_price=Decimal(str(command.entry_price)) if command.entry_price else None,
            exit_target=Decimal(str(command.exit_target)) if command.exit_target else None,
            stop_loss=Decimal(str(command.stop_loss)) if command.stop_loss else None,
            position_size_pct=command.position_size_pct,
        )

        decision.set_memo(memo)
        decision.set_conviction(command.conviction)

        try:
            decision.transition_to("RISK_REVIEW")
        except InvalidTransitionError as e:
            return DecisionResult(success=False, message=str(e))

        self._decision_repo.save(decision)

        event = DecisionMemoCreatedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=command.decision_id,
            ticker=command.ticker,
            decision=command.decision,
            conviction_level=command.conviction.level,
            entry_price=str(command.entry_price) if command.entry_price else None,
            exit_target=str(command.exit_target) if command.exit_target else None,
            created_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, decision.capability_family_id)

        return DecisionResult(
            success=True,
            message="Memo created, moved to risk review",
            decision_id=command.decision_id,
            events=[event],
        )

    def approve_decision(
        self, decision_id: str, approved_by: str
    ) -> DecisionResult:
        """Approve a decision (COMMITTEE_REVIEW → APPROVED)."""
        decision = self._decision_repo.get_by_id(decision_id)
        if decision is None:
            return DecisionResult(
                success=False, message="Decision not found"
            )

        try:
            decision.transition_to("APPROVED")
        except InvalidTransitionError as e:
            return DecisionResult(success=False, message=str(e))

        self._decision_repo.save(decision)

        event = DecisionApprovedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=decision_id,
            approved_by=approved_by,
            approved_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, decision.capability_family_id)

        return DecisionResult(
            success=True,
            message="Decision approved",
            decision_id=decision_id,
            events=[event],
        )

    def reject_decision(
        self, decision_id: str, rejected_by: str, reason: str
    ) -> DecisionResult:
        """Reject a decision."""
        decision = self._decision_repo.get_by_id(decision_id)
        if decision is None:
            return DecisionResult(
                success=False, message="Decision not found"
            )

        try:
            decision.transition_to("REJECTED")
        except InvalidTransitionError as e:
            return DecisionResult(success=False, message=str(e))

        self._decision_repo.save(decision)

        event = DecisionRejectedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=decision_id,
            rejected_by=rejected_by,
            rejection_reason=reason,
            rejected_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, decision.capability_family_id)

        return DecisionResult(
            success=True,
            message="Decision rejected",
            decision_id=decision_id,
            events=[event],
        )

    def revise_decision(
        self, decision_id: str, reason: str
    ) -> DecisionResult:
        """Revise a decision (send back for re-analysis)."""
        decision = self._decision_repo.get_by_id(decision_id)
        if decision is None:
            return DecisionResult(
                success=False, message="Decision not found"
            )

        try:
            decision.transition_to("REVISED")
        except InvalidTransitionError as e:
            return DecisionResult(success=False, message=str(e))

        self._decision_repo.save(decision)

        event = DecisionRevisedEvent(
            event_id=str(uuid.uuid4()),
            decision_id=decision_id,
            revision_reason=reason,
            revised_at=datetime.utcnow().isoformat(),
        )
        self._publish_event(event, decision.capability_family_id)

        return DecisionResult(
            success=True,
            message="Decision revised",
            decision_id=decision_id,
            events=[event],
        )

    def _publish_event(self, event, aggregate_id: str) -> None:
        """Publish event to outbox."""
        outbox_event = InvestmentOutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=json.dumps(event.to_dict()),
            aggregate_id=aggregate_id,
        )
        self._outbox_repo.save_event(outbox_event)
