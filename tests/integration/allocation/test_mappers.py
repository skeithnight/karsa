"""Tests for serialization mappers — Sprint-06 Wave-3."""
import pytest
import json

from karsa.allocation.domain.model.value_objects import (
    PolicySnapshot, PortfolioContext, ProposedWeight, RiskBudget
)
from karsa.allocation.infrastructure.persistence.mappers import (
    serialize_policy_snapshot, deserialize_policy_snapshot,
    serialize_portfolio_context, deserialize_portfolio_context,
    serialize_proposed_weight, deserialize_proposed_weight,
    serialize_proposed_weights, deserialize_proposed_weights,
)


class TestPolicySnapshotMapper:
    def test_roundtrip(self):
        original = PolicySnapshot(
            policy_id="policy-1",
            policy_version=2,
            policy_hash="abc123",
            active_rules=["DiversificationCap: max 40%", "ExplorationFloor: min 5%"],
        )
        serialized = serialize_policy_snapshot(original)
        # Verify JSON serializable
        json_str = json.dumps(serialized)
        deserialized = json.loads(json_str)
        result = deserialize_policy_snapshot(deserialized)

        assert result.policy_id == original.policy_id
        assert result.policy_version == original.policy_version
        assert result.policy_hash == original.policy_hash
        assert result.active_rules == original.active_rules

    def test_empty_rules(self):
        original = PolicySnapshot(
            policy_id="p1", policy_version=1, policy_hash="h", active_rules=[]
        )
        result = deserialize_policy_snapshot(serialize_policy_snapshot(original))
        assert result.active_rules == []


class TestPortfolioContextMapper:
    def test_roundtrip(self):
        original = PortfolioContext(
            current_gross_exposure=0.0,
            current_net_exposure=0.0,
            current_cash_ratio=1.0,
            current_concentration=0.0,
            projected_gross_exposure=0.60,
            projected_net_exposure=0.60,
            projected_cash_ratio=0.40,
            projected_concentration=0.30,
            cash_allocation_pct=0.40,
            concentration_impact="MEDIUM",
            alternatives_considered=["Equal weight", "Top-3 only"],
        )
        serialized = serialize_portfolio_context(original)
        json_str = json.dumps(serialized)
        deserialized = json.loads(json_str)
        result = deserialize_portfolio_context(deserialized)

        assert result.current_gross_exposure == original.current_gross_exposure
        assert result.projected_gross_exposure == original.projected_gross_exposure
        assert result.concentration_impact == original.concentration_impact
        assert result.alternatives_considered == original.alternatives_considered

    def test_defaults_on_missing_fields(self):
        result = deserialize_portfolio_context({})
        assert result.current_cash_ratio == 1.0
        assert result.concentration_impact == "LOW"


class TestProposedWeightMapper:
    def test_roundtrip_single(self):
        original = ProposedWeight(
            worker_urn="urn:karsa:worker:analyst-1",
            proposed_weight=0.35,
            ranking_score=0.66,
            eligibility_status="ALLOCATABLE",
            rationale="Top performer.",
            risk_budget=RiskBudget(max_volatility=0.15, max_drawdown=0.10, max_exposure=0.40),
        )
        serialized = serialize_proposed_weight(original)
        json_str = json.dumps(serialized)
        deserialized = json.loads(json_str)
        result = deserialize_proposed_weight(deserialized)

        assert result.worker_urn == original.worker_urn
        assert result.proposed_weight == original.proposed_weight
        assert result.ranking_score == original.ranking_score
        assert result.risk_budget.max_volatility == original.risk_budget.max_volatility

    def test_roundtrip_collection(self):
        weights = {
            "urn:karsa:worker:a1": ProposedWeight(
                worker_urn="urn:karsa:worker:a1",
                proposed_weight=0.50,
                ranking_score=0.80,
                eligibility_status="ALLOCATABLE",
                rationale="R1",
                risk_budget=RiskBudget(0.15, 0.10, 0.40),
            ),
            "urn:karsa:worker:a2": ProposedWeight(
                worker_urn="urn:karsa:worker:a2",
                proposed_weight=0.30,
                ranking_score=0.50,
                eligibility_status="ALLOCATABLE",
                rationale="R2",
                risk_budget=RiskBudget(0.10, 0.08, 0.30),
            ),
        }
        serialized = serialize_proposed_weights(weights)
        json_str = json.dumps(serialized)
        deserialized = json.loads(json_str)
        result = deserialize_proposed_weights(deserialized)

        assert len(result) == 2
        assert result["urn:karsa:worker:a1"].proposed_weight == 0.50
        assert result["urn:karsa:worker:a2"].risk_budget.max_drawdown == 0.08
