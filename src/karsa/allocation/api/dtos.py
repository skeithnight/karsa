"""Allocation API DTOs — Sprint-06 Wave-7.

Pydantic models for request validation and response serialization.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


# --- Request DTOs ---

class ProposalCreateRequest(BaseModel):
    """Request to generate an allocation proposal."""
    total_capital: float = Field(..., gt=0, description="Total capital to allocate. Must be positive.")
    policy_id: Optional[str] = Field(None, description="Optional policy ID. Uses default if not provided.")


class ExpectedOutcomeRequest(BaseModel):
    """Expected outcome for proposal approval."""
    expected_return_bps: float = Field(..., description="Expected return in basis points.")
    expected_drawdown_pct: float = Field(..., ge=0, description="Expected drawdown percentage.")
    expected_sharpe_ratio: float = Field(..., description="Expected Sharpe ratio.")
    expected_horizon_days: int = Field(..., gt=0, description="Evaluation horizon in days.")
    confidence_level: float = Field(..., ge=0, le=1, description="Confidence level (0.0 to 1.0).")
    benchmark_urn: Optional[str] = Field(None, description="Benchmark URN for comparison.")
    regime_at_decision: Optional[str] = Field(None, description="Market regime at decision time.")
    key_assumptions: List[Dict[str, Any]] = Field(default_factory=list, description="Structured assumptions.")
    attribution_expectations: Dict[str, float] = Field(default_factory=dict, description="Factor attribution expectations.")


class RiskAssessmentRequest(BaseModel):
    """Risk assessment for proposal approval."""
    worst_case_loss_pct: float = Field(..., ge=0, description="Worst case loss percentage.")
    concentration_risk: str = Field(..., description="Concentration risk level: LOW, MEDIUM, HIGH.")
    liquidity_risk: str = Field(..., description="Liquidity risk level: LOW, MEDIUM, HIGH.")
    regime_sensitivity: str = Field(..., description="Regime sensitivity: LOW, MEDIUM, HIGH.")


class ReviewHorizonRequest(BaseModel):
    """Review horizon for proposal approval."""
    review_date: str = Field(..., description="ISO datetime for review.")
    review_criteria: str = Field(..., min_length=1, description="Criteria for evaluating outcome.")
    auto_expire: bool = Field(False, description="Whether to auto-expire if not reviewed.")


class ProposalApproveRequest(BaseModel):
    """Request to approve an allocation proposal."""
    proposal_id: str = Field(..., description="ID of the proposal to approve.")
    decision_id: str = Field(..., description="Unique ID for the new decision.")
    expected_outcome: ExpectedOutcomeRequest
    risk_assessment: RiskAssessmentRequest
    review_horizon: ReviewHorizonRequest
    votes: List[Dict[str, Any]] = Field(..., min_length=1, description="Committee votes.")


class ProposalRejectRequest(BaseModel):
    """Request to reject an allocation proposal."""
    proposal_id: str = Field(..., description="ID of the proposal to reject.")
    decision_id: str = Field(..., description="Unique ID for the new decision.")
    rejection_reason: str = Field(..., min_length=1, description="Reason for rejection.")
    votes: List[Dict[str, Any]] = Field(..., min_length=1, description="Committee votes.")


class ProposalModifyRequest(BaseModel):
    """Request to modify an allocation proposal."""
    proposal_id: str = Field(..., description="ID of the proposal to modify.")
    decision_id: str = Field(..., description="Unique ID for the new decision.")
    modified_weights: Dict[str, float] = Field(..., description="Modified allocation weights.")
    modification_reason: str = Field(..., min_length=1, description="Reason for modification.")
    expected_outcome: ExpectedOutcomeRequest
    risk_assessment: RiskAssessmentRequest
    review_horizon: ReviewHorizonRequest
    votes: List[Dict[str, Any]] = Field(..., min_length=1, description="Committee votes.")


# --- Response DTOs ---

class RiskBudgetResponse(BaseModel):
    """Risk budget for a proposed weight."""
    max_volatility: float
    max_drawdown: float
    max_exposure: float


class ProposedWeightResponse(BaseModel):
    """A single proposed weight in a proposal."""
    worker_urn: str
    proposed_weight: float
    ranking_score: float
    eligibility_status: str
    rationale: str
    risk_budget: RiskBudgetResponse


class PolicySnapshotResponse(BaseModel):
    """Policy snapshot at proposal time."""
    policy_id: str
    policy_version: int
    policy_hash: str
    active_rules: List[str]


class PortfolioContextResponse(BaseModel):
    """Portfolio context at proposal time."""
    current_gross_exposure: float
    current_net_exposure: float
    current_cash_ratio: float
    current_concentration: float
    projected_gross_exposure: float
    projected_net_exposure: float
    projected_cash_ratio: float
    projected_concentration: float
    cash_allocation_pct: float
    concentration_impact: str
    alternatives_considered: List[str]


class ProposalResponse(BaseModel):
    """Response for a single proposal."""
    proposal_id: str
    policy_id: str
    journal_ref: str
    proposed_weights: Dict[str, ProposedWeightResponse]
    total_capital: float
    proposal_rationale: str
    portfolio_context: PortfolioContextResponse
    policy_snapshot: PolicySnapshotResponse
    context_hash: str
    generated_at: str
    status: Optional[str] = None


class ProposalListItemResponse(BaseModel):
    """A proposal in a list response."""
    proposal_id: str
    policy_id: str
    total_capital: float
    worker_count: int
    status: Optional[str] = None
    generated_at: str


class ProposalListResponse(BaseModel):
    """Paginated list of proposals."""
    data: List[ProposalListItemResponse]
    pagination: Dict[str, int]


class ProposalDetailResponse(BaseModel):
    """Full proposal detail with status."""
    proposal_id: str
    policy_id: str
    journal_ref: str
    proposed_weights: Dict[str, ProposedWeightResponse]
    total_capital: float
    proposal_rationale: str
    portfolio_context: PortfolioContextResponse
    policy_snapshot: PolicySnapshotResponse
    context_hash: str
    generated_at: str
    status: Optional[str] = None
    decision_id: Optional[str] = None
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None


class DecisionResponse(BaseModel):
    """Response for a CIO decision."""
    decision_id: str
    decision_journal_ref: str
    cryptographic_signature: str
    status: str
