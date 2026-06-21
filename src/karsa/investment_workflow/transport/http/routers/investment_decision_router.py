"""Investment decision router -- Sprint-13. Wave-1G.

POST + GET endpoints for investment workflow.
Delegates to facades only. No business logic.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from karsa.investment_workflow.integration.investment_workflow_command_facade import (
    InvestmentWorkflowCommandFacade,
)
from karsa.investment_workflow.integration.investment_workflow_query_facade import (
    InvestmentWorkflowQueryFacade,
)
from karsa.investment_workflow.transport.http.requests.propose_decision_request import (
    ProposeDecisionRequest,
)
from karsa.investment_workflow.transport.http.requests.record_analyst_request import (
    RecordAnalystRequest,
)
from karsa.investment_workflow.transport.http.requests.record_debate_request import (
    RecordDebateRequest,
)
from karsa.investment_workflow.transport.http.requests.create_memo_request import (
    CreateMemoRequest,
)
from karsa.investment_workflow.transport.http.responses.command_result_response import (
    CommandResultResponse,
)
from karsa.investment_workflow.transport.http.responses.decision_response import (
    DecisionResponse,
)

router = APIRouter(prefix="/investments", tags=["Investment Decisions"])


def _get_command_facade() -> InvestmentWorkflowCommandFacade:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def _get_query_facade() -> InvestmentWorkflowQueryFacade:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")


def _to_response(result, request_id: str = None) -> CommandResultResponse:
    return CommandResultResponse(
        success=result.success,
        message=result.message,
        request_id=request_id,
        data=result.data,
    )


# --- Command Endpoints ---


@router.post(
    "/decisions",
    response_model=CommandResultResponse,
    status_code=201,
    summary="Propose an investment decision",
)
def propose_decision(
    request: ProposeDecisionRequest,
    facade: InvestmentWorkflowCommandFacade = Depends(_get_command_facade),
) -> CommandResultResponse:
    request_id = str(uuid.uuid4())
    result = facade.propose_decision(
        capability_family_id=request.capability_family_id,
        ticker=request.ticker,
        decision_date=request.decision_date,
        proposed_by=request.proposed_by,
    )
    return _to_response(result, request_id)


@router.post(
    "/decisions/{decision_id}/analysts",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Record analyst output",
)
def record_analyst(
    decision_id: str,
    request: RecordAnalystRequest,
    facade: InvestmentWorkflowCommandFacade = Depends(_get_command_facade),
) -> CommandResultResponse:
    request_id = str(uuid.uuid4())
    result = facade.record_analyst(
        decision_id=decision_id,
        analyst_type=request.analyst_type,
        score=request.score,
        confidence=request.confidence,
        output_text=request.output_text,
        tools_used=request.tools_used,
        model_version=request.model_version,
    )
    return _to_response(result, request_id)


@router.post(
    "/decisions/{decision_id}/debate",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Record debate round",
)
def record_debate(
    decision_id: str,
    request: RecordDebateRequest,
    facade: InvestmentWorkflowCommandFacade = Depends(_get_command_facade),
) -> CommandResultResponse:
    request_id = str(uuid.uuid4())
    result = facade.record_debate(
        decision_id=decision_id,
        round_number=request.round_number,
        bull_memo=request.bull_memo,
        bear_memo=request.bear_memo,
        bull_level=request.bull_conviction.level,
        bull_score=request.bull_conviction.numeric_score,
        bull_agreement=request.bull_conviction.analyst_agreement,
        bear_level=request.bear_conviction.level,
        bear_score=request.bear_conviction.numeric_score,
        bear_agreement=request.bear_conviction.analyst_agreement,
    )
    return _to_response(result, request_id)


@router.post(
    "/decisions/{decision_id}/memo",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Create investment memo",
)
def create_memo(
    decision_id: str,
    request: CreateMemoRequest,
    facade: InvestmentWorkflowCommandFacade = Depends(_get_command_facade),
) -> CommandResultResponse:
    request_id = str(uuid.uuid4())
    result = facade.create_memo(
        decision_id=decision_id,
        ticker=request.ticker,
        decision=request.decision,
        conviction_level=request.conviction_level,
        conviction_score=request.conviction_score,
        conviction_agreement=request.conviction_agreement,
        thesis=request.thesis,
        entry_price=request.entry_price,
        exit_target=request.exit_target,
        stop_loss=request.stop_loss,
        position_size_pct=request.position_size_pct,
    )
    return _to_response(result, request_id)


@router.post(
    "/decisions/{decision_id}/approve",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Approve decision",
)
def approve_decision(
    decision_id: str,
    facade: InvestmentWorkflowCommandFacade = Depends(_get_command_facade),
) -> CommandResultResponse:
    request_id = str(uuid.uuid4())
    result = facade.approve(decision_id, "committee-chair")
    return _to_response(result, request_id)


@router.post(
    "/decisions/{decision_id}/reject",
    response_model=CommandResultResponse,
    status_code=200,
    summary="Reject decision",
)
def reject_decision(
    decision_id: str,
    facade: InvestmentWorkflowCommandFacade = Depends(_get_command_facade),
) -> CommandResultResponse:
    request_id = str(uuid.uuid4())
    result = facade.reject(decision_id, "risk-officer", "Mandate violation")
    return _to_response(result, request_id)


# --- Query Endpoints ---


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
    summary="Get decision by ID",
)
def get_decision(
    decision_id: str,
    facade: InvestmentWorkflowQueryFacade = Depends(_get_query_facade),
) -> DecisionResponse:
    result = facade.get_decision(decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return DecisionResponse(
        decision_id=result.decision_id,
        capability_family_id=result.capability_family_id,
        ticker=result.ticker,
        decision_date=result.decision_date,
        state=result.state,
        analyst_count=result.analyst_count,
        debate_count=result.debate_count,
        has_memo=result.has_memo,
        conviction_level=result.conviction_level,
        memo_decision=result.memo_decision,
        entry_price=result.entry_price,
        exit_target=result.exit_target,
        proposed_by=result.proposed_by,
        created_at=result.created_at,
    )


@router.get(
    "/decisions",
    response_model=list[DecisionResponse],
    summary="List decisions by ticker",
)
def list_decisions(
    ticker: str = None,
    capability_family_id: str = None,
    facade: InvestmentWorkflowQueryFacade = Depends(_get_query_facade),
) -> list[DecisionResponse]:
    if ticker:
        results = facade.get_decisions_by_ticker(ticker)
    elif capability_family_id:
        results = facade.get_decisions_by_family(capability_family_id)
    else:
        results = []

    return [
        DecisionResponse(
            decision_id=r.decision_id,
            capability_family_id=r.capability_family_id,
            ticker=r.ticker,
            decision_date=r.decision_date,
            state=r.state,
            analyst_count=r.analyst_count,
            debate_count=r.debate_count,
            has_memo=r.has_memo,
            conviction_level=r.conviction_level,
            memo_decision=r.memo_decision,
            entry_price=r.entry_price,
            exit_target=r.exit_target,
            proposed_by=r.proposed_by,
            created_at=r.created_at,
        )
        for r in results
    ]
