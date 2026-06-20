"""Allocation API mappers — Sprint-06 Wave-7.

Maps domain objects to API response DTOs.
"""
from typing import Dict, Any, Optional

from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.api.dtos import (
    ProposalResponse, ProposalListItemResponse, ProposalDetailResponse,
    ProposedWeightResponse, RiskBudgetResponse, PortfolioContextResponse,
    PolicySnapshotResponse,
)


def map_proposal_to_response(proposal: AllocationProposal, status: Optional[str] = None) -> ProposalResponse:
    """Maps an AllocationProposal to a ProposalResponse DTO."""
    weights = {}
    for urn, w in proposal.proposed_weights.items():
        weights[urn] = ProposedWeightResponse(
            worker_urn=w.worker_urn,
            proposed_weight=w.proposed_weight,
            ranking_score=w.ranking_score,
            eligibility_status=w.eligibility_status,
            rationale=w.rationale,
            risk_budget=RiskBudgetResponse(
                max_volatility=w.risk_budget.max_volatility,
                max_drawdown=w.risk_budget.max_drawdown,
                max_exposure=w.risk_budget.max_exposure,
            ),
        )

    return ProposalResponse(
        proposal_id=proposal.proposal_id,
        policy_id=proposal.policy_id,
        journal_ref=proposal.journal_ref,
        proposed_weights=weights,
        total_capital=proposal.total_capital,
        proposal_rationale=proposal.proposal_rationale,
        portfolio_context=_map_portfolio_context(proposal.portfolio_context),
        policy_snapshot=_map_policy_snapshot(proposal.policy_snapshot),
        context_hash=proposal.context_hash,
        generated_at=proposal.generated_at.isoformat(),
        status=status,
    )


def map_proposal_to_list_item(
    proposal: AllocationProposal,
    status: Optional[str] = None,
) -> ProposalListItemResponse:
    """Maps an AllocationProposal to a list item DTO."""
    return ProposalListItemResponse(
        proposal_id=proposal.proposal_id,
        policy_id=proposal.policy_id,
        total_capital=proposal.total_capital,
        worker_count=len(proposal.proposed_weights),
        status=status,
        generated_at=proposal.generated_at.isoformat(),
    )


def map_proposal_to_detail(
    proposal: AllocationProposal,
    projection: Optional[ProposalStatusProjection] = None,
) -> ProposalDetailResponse:
    """Maps an AllocationProposal + projection to a detail DTO."""
    weights = {}
    for urn, w in proposal.proposed_weights.items():
        weights[urn] = ProposedWeightResponse(
            worker_urn=w.worker_urn,
            proposed_weight=w.proposed_weight,
            ranking_score=w.ranking_score,
            eligibility_status=w.eligibility_status,
            rationale=w.rationale,
            risk_budget=RiskBudgetResponse(
                max_volatility=w.risk_budget.max_volatility,
                max_drawdown=w.risk_budget.max_drawdown,
                max_exposure=w.risk_budget.max_exposure,
            ),
        )

    status = None
    decision_id = None
    decided_at = None
    decided_by = None
    if projection:
        status = projection.status
        decision_id = projection.decision_id
        decided_at = projection.decided_at.isoformat() if projection.decided_at else None
        decided_by = projection.decided_by

    return ProposalDetailResponse(
        proposal_id=proposal.proposal_id,
        policy_id=proposal.policy_id,
        journal_ref=proposal.journal_ref,
        proposed_weights=weights,
        total_capital=proposal.total_capital,
        proposal_rationale=proposal.proposal_rationale,
        portfolio_context=_map_portfolio_context(proposal.portfolio_context),
        policy_snapshot=_map_policy_snapshot(proposal.policy_snapshot),
        context_hash=proposal.context_hash,
        generated_at=proposal.generated_at.isoformat(),
        status=status,
        decision_id=decision_id,
        decided_at=decided_at,
        decided_by=decided_by,
    )


def _map_portfolio_context(ctx) -> PortfolioContextResponse:
    return PortfolioContextResponse(
        current_gross_exposure=ctx.current_gross_exposure,
        current_net_exposure=ctx.current_net_exposure,
        current_cash_ratio=ctx.current_cash_ratio,
        current_concentration=ctx.current_concentration,
        projected_gross_exposure=ctx.projected_gross_exposure,
        projected_net_exposure=ctx.projected_net_exposure,
        projected_cash_ratio=ctx.projected_cash_ratio,
        projected_concentration=ctx.projected_concentration,
        cash_allocation_pct=ctx.cash_allocation_pct,
        concentration_impact=ctx.concentration_impact,
        alternatives_considered=ctx.alternatives_considered,
    )


def _map_policy_snapshot(ps) -> PolicySnapshotResponse:
    return PolicySnapshotResponse(
        policy_id=ps.policy_id,
        policy_version=ps.policy_version,
        policy_hash=ps.policy_hash,
        active_rules=ps.active_rules,
    )
