"""Serialization/deserialization mappers for allocation domain objects.

All mappers are deterministic and JSON-safe. They produce dicts that can be
passed directly to json.dumps() and reconstructed from json.loads() output.
"""
from typing import Dict, Any, List

from karsa.allocation.domain.model.value_objects import (
    PolicySnapshot, PortfolioContext, ProposedWeight, RiskBudget
)


def serialize_policy_snapshot(ps: PolicySnapshot) -> Dict[str, Any]:
    return {
        "policy_id": ps.policy_id,
        "policy_version": ps.policy_version,
        "policy_hash": ps.policy_hash,
        "active_rules": list(ps.active_rules),
    }


def deserialize_policy_snapshot(data: Dict[str, Any]) -> PolicySnapshot:
    return PolicySnapshot(
        policy_id=data["policy_id"],
        policy_version=data["policy_version"],
        policy_hash=data["policy_hash"],
        active_rules=data["active_rules"],
    )


def serialize_portfolio_context(pc: PortfolioContext) -> Dict[str, Any]:
    return {
        "current_gross_exposure": pc.current_gross_exposure,
        "current_net_exposure": pc.current_net_exposure,
        "current_cash_ratio": pc.current_cash_ratio,
        "current_concentration": pc.current_concentration,
        "projected_gross_exposure": pc.projected_gross_exposure,
        "projected_net_exposure": pc.projected_net_exposure,
        "projected_cash_ratio": pc.projected_cash_ratio,
        "projected_concentration": pc.projected_concentration,
        "cash_allocation_pct": pc.cash_allocation_pct,
        "concentration_impact": pc.concentration_impact,
        "alternatives_considered": list(pc.alternatives_considered),
    }


def deserialize_portfolio_context(data: Dict[str, Any]) -> PortfolioContext:
    return PortfolioContext(
        current_gross_exposure=data.get("current_gross_exposure", 0.0),
        current_net_exposure=data.get("current_net_exposure", 0.0),
        current_cash_ratio=data.get("current_cash_ratio", 1.0),
        current_concentration=data.get("current_concentration", 0.0),
        projected_gross_exposure=data.get("projected_gross_exposure", 0.0),
        projected_net_exposure=data.get("projected_net_exposure", 0.0),
        projected_cash_ratio=data.get("projected_cash_ratio", 1.0),
        projected_concentration=data.get("projected_concentration", 0.0),
        cash_allocation_pct=data.get("cash_allocation_pct", 0.0),
        concentration_impact=data.get("concentration_impact", "LOW"),
        alternatives_considered=data.get("alternatives_considered", []),
    )


def serialize_proposed_weight(pw: ProposedWeight) -> Dict[str, Any]:
    return {
        "worker_urn": pw.worker_urn,
        "proposed_weight": pw.proposed_weight,
        "ranking_score": pw.ranking_score,
        "eligibility_status": pw.eligibility_status,
        "rationale": pw.rationale,
        "risk_budget": {
            "max_volatility": pw.risk_budget.max_volatility,
            "max_drawdown": pw.risk_budget.max_drawdown,
            "max_exposure": pw.risk_budget.max_exposure,
        },
    }


def deserialize_proposed_weight(data: Dict[str, Any]) -> ProposedWeight:
    rb = data.get("risk_budget", {})
    return ProposedWeight(
        worker_urn=data["worker_urn"],
        proposed_weight=data["proposed_weight"],
        ranking_score=data["ranking_score"],
        eligibility_status=data["eligibility_status"],
        rationale=data["rationale"],
        risk_budget=RiskBudget(
            max_volatility=rb.get("max_volatility", 0.0),
            max_drawdown=rb.get("max_drawdown", 0.0),
            max_exposure=rb.get("max_exposure", 0.0),
        ),
    )


def serialize_proposed_weights(weights: Dict[str, ProposedWeight]) -> Dict[str, Any]:
    return {urn: serialize_proposed_weight(pw) for urn, pw in weights.items()}


def deserialize_proposed_weights(data: Dict[str, Any]) -> Dict[str, ProposedWeight]:
    return {urn: deserialize_proposed_weight(w) for urn, w in data.items()}
