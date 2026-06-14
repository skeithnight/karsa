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

_decision_service: Optional[CIODecisionService] = None
_orchestration_service: Optional[PortfolioOrchestrationService] = None

def get_decision_service() -> CIODecisionService:
    if _decision_service is None:
        raise RuntimeError("CIODecisionService not configured for API.")
    return _decision_service

def get_orchestration_service() -> PortfolioOrchestrationService:
    if _orchestration_service is None:
        raise RuntimeError("PortfolioOrchestrationService not configured for API.")
    return _orchestration_service

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
