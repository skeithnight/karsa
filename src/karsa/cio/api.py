from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from karsa.cio.services import CIODecisionService, PortfolioOrchestrationService
from karsa.cio.value_objects import CommitteeVote, OverrideReason
from karsa.cio.exceptions import (
    CIODecisionException, QuorumNotMetException, DecisionNotFoundException,
    DuplicateJournalRefException, InvalidDecisionSignatureException
)

router = APIRouter(prefix="/cio", tags=["CIO Engine"])

def get_decision_service() -> CIODecisionService:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")

def get_orchestration_service() -> PortfolioOrchestrationService:
    raise NotImplementedError("Dependency must be overridden in app bootstrap")

class VoteSchema(BaseModel):
    voter_id: str
    vote_type: str  # "APPROVE", "REJECT"

class OverrideReasonSchema(BaseModel):
    justification: str
    referenced_incident_urn: Optional[str] = None

class DecisionCreateRequest(BaseModel):
    decision_id: str
    calculation_id: Optional[str] = None
    governance_exception_id: Optional[str] = None
    decision_journal_ref: str
    portfolio_snapshot_hash: str
    action_type: str  # "APPROVE_ALLOCATION", "REJECT_ALLOCATION", "OVERRIDE"
    target_node_type: str  # "PORTFOLIO", "STRATEGY", "THESIS", "WORKER"
    target_node_id: str
    allocated_weights: Dict[str, float]
    votes: List[VoteSchema] = []
    override_reason: Optional[OverrideReasonSchema] = None

class PortfolioStateRequest(BaseModel):
    state_id: str
    decision_id: str
    portfolio_tree: Dict[str, Any]


# --- Sprint-06 Proposal Workflow DTOs ---

class ExpectedOutcomeSchema(BaseModel):
    expected_return_bps: float
    expected_drawdown_pct: float = Field(ge=0)
    expected_sharpe_ratio: float
    expected_horizon_days: int = Field(gt=0)
    confidence_level: float = Field(ge=0, le=1)
    benchmark_urn: Optional[str] = None
    regime_at_decision: Optional[str] = None
    key_assumptions: List[Dict[str, Any]] = []
    attribution_expectations: Dict[str, float] = {}


class RiskAssessmentSchema(BaseModel):
    worst_case_loss_pct: float = Field(ge=0)
    concentration_risk: str
    liquidity_risk: str
    regime_sensitivity: str


class ReviewHorizonSchema(BaseModel):
    review_date: str
    review_criteria: str = Field(min_length=1)
    auto_expire: bool = False


class ProposalDecisionRequest(BaseModel):
    """Request for proposal-based CIO decisions (approve/reject/modify)."""
    proposal_id: str
    decision_id: str
    action_type: str  # "APPROVE_ALLOCATION", "REJECT_ALLOCATION", "OVERRIDE"
    votes: List[VoteSchema] = []
    # For APPROVE_ALLOCATION
    expected_outcome: Optional[ExpectedOutcomeSchema] = None
    risk_assessment: Optional[RiskAssessmentSchema] = None
    review_horizon: Optional[ReviewHorizonSchema] = None
    # For REJECT_ALLOCATION
    rejection_reason: Optional[str] = None
    # For OVERRIDE (modify)
    modified_weights: Optional[Dict[str, float]] = None
    modification_reason: Optional[str] = None

@router.post("/decisions", status_code=status.HTTP_201_CREATED)
def create_decision(
    request: DecisionCreateRequest,
    service: CIODecisionService = Depends(get_decision_service)
):
    votes = [
        CommitteeVote(
            voter_id=v.voter_id,
            vote_type=v.vote_type,
            timestamp=datetime.utcnow()
        ) for v in request.votes
    ]
    override_reason = None
    if request.override_reason:
        override_reason = OverrideReason(
            justification=request.override_reason.justification,
            referenced_incident_urn=request.override_reason.referenced_incident_urn
        )

    try:
        decision = service.create_decision(
            decision_id=request.decision_id,
            calculation_id=request.calculation_id,
            governance_exception_id=request.governance_exception_id,
            decision_journal_ref=request.decision_journal_ref,
            portfolio_snapshot_hash=request.portfolio_snapshot_hash,
            action_type=request.action_type,
            target_node_type=request.target_node_type,
            target_node_id=request.target_node_id,
            allocated_weights=request.allocated_weights,
            votes=votes,
            override_reason=override_reason
        )
        return {
            "decision_id": decision.decision_id,
            "decision_journal_ref": decision.decision_journal_ref,
            "signature": decision.cryptographic_signature,
            "status": "SEALED"
        }
    except QuorumNotMetException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateJournalRefException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidDecisionSignatureException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/decisions")
def list_decisions(
    page: int = 1,
    size: int = 50,
    service: CIODecisionService = Depends(get_decision_service)
):
    offset = (page - 1) * size
    decisions = service.list_decisions(limit=size, offset=offset)
    
    data = []
    for d in decisions:
        data.append({
            "decision_id": d.decision_id,
            "target_node_id": d.target_node_id,
            "action_type": d.action_type,
            "cryptographic_signature": d.cryptographic_signature,
            "created_at": d.created_at.isoformat()
        })
    
    return {
        "data": data,
        "pagination": {
            "page": page,
            "size": size,
            "total_items": len(data)  # Exact total requires count query, simplified for now
        }
    }

@router.get("/decisions/{decision_id}")
def get_decision(
    decision_id: str,
    service: CIODecisionService = Depends(get_decision_service)
):
    try:
        decision = service.get_decision(decision_id)
        return {
            "decision_id": decision.decision_id,
            "calculation_id": decision.calculation_id,
            "governance_exception_id": decision.governance_exception_id,
            "decision_journal_ref": decision.decision_journal_ref,
            "portfolio_snapshot_hash": decision.portfolio_snapshot_hash,
            "action_type": decision.action_type,
            "target_node_type": decision.target_node_type,
            "target_node_id": decision.target_node_id,
            "decision_payload": decision.decision_payload,
            "cryptographic_signature": decision.cryptographic_signature,
            "created_at": decision.created_at.isoformat()
        }
    except DecisionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/decisions/{decision_id}/authorization")
def get_authorization_state(
    decision_id: str,
    service: CIODecisionService = Depends(get_decision_service)
):
    try:
        decision = service.get_decision(decision_id)
        return {
            "decision_id": decision.decision_id,
            "signature": decision.cryptographic_signature,
            "portfolio_snapshot_hash": decision.portfolio_snapshot_hash,
            "governance_exception_id": decision.governance_exception_id
        }
    except DecisionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/decisions/{decision_id}/votes")
def get_committee_votes(
    decision_id: str,
    service: CIODecisionService = Depends(get_decision_service)
):
    try:
        decision = service.get_decision(decision_id)
        return {
            "decision_id": decision.decision_id,
            "votes": [
                {
                    "voter_id": v.voter_id,
                    "vote_type": v.vote_type,
                    "timestamp": v.timestamp.isoformat()
                } for v in decision.votes
            ]
        }
    except DecisionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/projections", status_code=status.HTTP_201_CREATED)
def create_projection(
    request: PortfolioStateRequest,
    service: PortfolioOrchestrationService = Depends(get_orchestration_service)
):
    try:
        state = service.project_state(
            state_id=request.state_id,
            decision_id=request.decision_id,
            portfolio_tree=request.portfolio_tree
        )
        return {
            "state_id": state.state_id,
            "decision_id": state.decision_id,
            "created_at": state.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/projections/latest")
def get_latest_projection(
    service: PortfolioOrchestrationService = Depends(get_orchestration_service)
):
    state = service.get_latest_state()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No portfolio state projections found.")
    return {
        "state_id": state.state_id,
        "decision_id": state.decision_id,
        "portfolio_tree": state.portfolio_tree,
        "created_at": state.created_at.isoformat()
    }


# --- Sprint-06 Proposal Decision Endpoint ---

@router.post("/decisions/proposal", status_code=status.HTTP_201_CREATED)
def create_proposal_decision(
    request: ProposalDecisionRequest,
    service: CIODecisionService = Depends(get_decision_service),
):
    """Creates a CIO decision from a proposal (approve/reject/modify)."""
    votes = [
        CommitteeVote(voter_id=v.voter_id, vote_type=v.vote_type, timestamp=datetime.utcnow())
        for v in request.votes
    ]

    try:
        if request.action_type == "APPROVE_ALLOCATION":
            if not request.expected_outcome:
                raise HTTPException(status_code=400, detail="expected_outcome required for APPROVE_ALLOCATION.")
            if not request.risk_assessment:
                raise HTTPException(status_code=400, detail="risk_assessment required for APPROVE_ALLOCATION.")
            if not request.review_horizon:
                raise HTTPException(status_code=400, detail="review_horizon required for APPROVE_ALLOCATION.")

            from karsa.allocation.domain.model.value_objects import (
                ExpectedOutcome, RiskAssessment, ReviewHorizon, StructuredAssumption
            )

            eo = request.expected_outcome
            assumptions = [
                StructuredAssumption(**a) for a in eo.key_assumptions
            ] if eo.key_assumptions else []

            decision = service.approve_proposal(
                proposal_id=request.proposal_id,
                decision_id=request.decision_id,
                expected_outcome=ExpectedOutcome(
                    expected_return_bps=eo.expected_return_bps,
                    expected_drawdown_pct=eo.expected_drawdown_pct,
                    expected_sharpe_ratio=eo.expected_sharpe_ratio,
                    expected_horizon_days=eo.expected_horizon_days,
                    confidence_level=eo.confidence_level,
                    benchmark_urn=eo.benchmark_urn,
                    regime_at_decision=eo.regime_at_decision,
                    key_assumptions=assumptions,
                    attribution_expectations=eo.attribution_expectations,
                ),
                risk_assessment=RiskAssessment(
                    worst_case_loss_pct=request.risk_assessment.worst_case_loss_pct,
                    concentration_risk=request.risk_assessment.concentration_risk,
                    liquidity_risk=request.risk_assessment.liquidity_risk,
                    regime_sensitivity=request.risk_assessment.regime_sensitivity,
                ),
                review_horizon=ReviewHorizon(
                    review_date=request.review_horizon.review_date,
                    review_criteria=request.review_horizon.review_criteria,
                    auto_expire=request.review_horizon.auto_expire,
                ),
                votes=votes,
            )

        elif request.action_type == "REJECT_ALLOCATION":
            if not request.rejection_reason:
                raise HTTPException(status_code=400, detail="rejection_reason required for REJECT_ALLOCATION.")

            decision = service.reject_proposal(
                proposal_id=request.proposal_id,
                decision_id=request.decision_id,
                rejection_reason=request.rejection_reason,
                votes=votes,
            )

        elif request.action_type == "OVERRIDE":
            if not request.modified_weights:
                raise HTTPException(status_code=400, detail="modified_weights required for OVERRIDE.")
            if not request.modification_reason:
                raise HTTPException(status_code=400, detail="modification_reason required for OVERRIDE.")
            if not request.expected_outcome:
                raise HTTPException(status_code=400, detail="expected_outcome required for OVERRIDE.")
            if not request.risk_assessment:
                raise HTTPException(status_code=400, detail="risk_assessment required for OVERRIDE.")
            if not request.review_horizon:
                raise HTTPException(status_code=400, detail="review_horizon required for OVERRIDE.")

            from karsa.allocation.domain.model.value_objects import (
                ExpectedOutcome, RiskAssessment, ReviewHorizon, StructuredAssumption
            )

            eo = request.expected_outcome
            assumptions = [
                StructuredAssumption(**a) for a in eo.key_assumptions
            ] if eo.key_assumptions else []

            decision = service.modify_proposal(
                proposal_id=request.proposal_id,
                decision_id=request.decision_id,
                modified_weights=request.modified_weights,
                modification_reason=request.modification_reason,
                expected_outcome=ExpectedOutcome(
                    expected_return_bps=eo.expected_return_bps,
                    expected_drawdown_pct=eo.expected_drawdown_pct,
                    expected_sharpe_ratio=eo.expected_sharpe_ratio,
                    expected_horizon_days=eo.expected_horizon_days,
                    confidence_level=eo.confidence_level,
                    benchmark_urn=eo.benchmark_urn,
                    regime_at_decision=eo.regime_at_decision,
                    key_assumptions=assumptions,
                    attribution_expectations=eo.attribution_expectations,
                ),
                risk_assessment=RiskAssessment(
                    worst_case_loss_pct=request.risk_assessment.worst_case_loss_pct,
                    concentration_risk=request.risk_assessment.concentration_risk,
                    liquidity_risk=request.risk_assessment.liquidity_risk,
                    regime_sensitivity=request.risk_assessment.regime_sensitivity,
                ),
                review_horizon=ReviewHorizon(
                    review_date=request.review_horizon.review_date,
                    review_criteria=request.review_horizon.review_criteria,
                    auto_expire=request.review_horizon.auto_expire,
                ),
                votes=votes,
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action_type: {request.action_type}")

        return {
            "decision_id": decision.decision_id,
            "decision_journal_ref": decision.decision_journal_ref,
            "cryptographic_signature": decision.cryptographic_signature,
            "status": "SEALED",
        }

    except QuorumNotMetException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateJournalRefException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if "not PENDING" in detail:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
