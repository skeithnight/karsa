"""Tests for AllocationProposal aggregate — Sprint-06 Wave-2."""
import pytest
from datetime import datetime

from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, PolicySnapshot, PortfolioContext, RiskBudget
)
from karsa.cio.exceptions import ImmutabilityViolationException


def _make_risk_budget():
    return RiskBudget(max_volatility=0.15, max_drawdown=0.10, max_exposure=0.40)


def _make_proposed_weight(worker_urn="urn:karsa:worker:analyst-1", weight=0.30):
    return ProposedWeight(
        worker_urn=worker_urn,
        proposed_weight=weight,
        ranking_score=0.66,
        eligibility_status="ALLOCATABLE",
        rationale="Top performer with highest cumulative alpha.",
        risk_budget=_make_risk_budget(),
    )


def _make_policy_snapshot():
    return PolicySnapshot(
        policy_id="policy-1",
        policy_version=1,
        policy_hash="abc123",
        active_rules=["DiversificationCap: max 40%", "ExplorationFloor: min 5%"],
    )


def _make_portfolio_context():
    return PortfolioContext(
        current_gross_exposure=0.0,
        current_net_exposure=0.0,
        current_cash_ratio=1.0,
        current_concentration=0.0,
        projected_gross_exposure=0.60,
        projected_net_exposure=0.60,
        projected_cash_ratio=0.40,
        projected_concentration=0.30,
        cash_allocation_pct=0.40,
        concentration_impact="LOW",
        alternatives_considered=["Equal weight", "Top-3 only"],
    )


def _make_proposal(**overrides):
    defaults = dict(
        proposal_id="urn:karsa:proposal:test-1",
        policy_id="policy-1",
        policy_snapshot=_make_policy_snapshot(),
        journal_ref="urn:karsa:journal:proposal:test-1",
        proposed_weights={
            "urn:karsa:worker:analyst-1": _make_proposed_weight("urn:karsa:worker:analyst-1", 0.30),
            "urn:karsa:worker:analyst-2": _make_proposed_weight("urn:karsa:worker:analyst-2", 0.30),
        },
        total_capital=100000.0,
        proposal_rationale="Proportional allocation across 2 workers.",
        portfolio_context=_make_portfolio_context(),
        context_hash="hash123",
        generated_at=datetime.utcnow(),
    )
    defaults.update(overrides)
    return AllocationProposal(**defaults)


class TestAllocationProposalCreation:
    def test_valid_proposal_creation(self):
        proposal = _make_proposal()
        assert proposal.proposal_id == "urn:karsa:proposal:test-1"
        assert proposal.total_capital == 100000.0
        assert len(proposal.proposed_weights) == 2

    def test_missing_proposal_id_raises(self):
        with pytest.raises(ValueError, match="proposal_id cannot be empty"):
            _make_proposal(proposal_id="")

    def test_missing_journal_ref_raises(self):
        with pytest.raises(ValueError, match="journal_ref cannot be empty"):
            _make_proposal(journal_ref="")

    def test_negative_total_capital_raises(self):
        with pytest.raises(ValueError, match="total_capital cannot be negative"):
            _make_proposal(total_capital=-1.0)

    def test_empty_proposed_weights_raises(self):
        with pytest.raises(ValueError, match="proposed_weights cannot be empty"):
            _make_proposal(proposed_weights={})

    def test_weight_sum_exceeds_one_raises(self):
        with pytest.raises(ValueError, match="exceeds 1.0"):
            _make_proposal(proposed_weights={
                "w1": _make_proposed_weight("w1", 0.60),
                "w2": _make_proposed_weight("w2", 0.50),
            })

    def test_weight_sum_exactly_one_succeeds(self):
        proposal = _make_proposal(proposed_weights={
            "w1": _make_proposed_weight("w1", 0.50),
            "w2": _make_proposed_weight("w2", 0.50),
        })
        assert len(proposal.proposed_weights) == 2

    def test_missing_policy_id_raises(self):
        with pytest.raises(ValueError, match="policy_id cannot be empty"):
            _make_proposal(policy_id="")

    def test_missing_proposal_rationale_raises(self):
        with pytest.raises(ValueError, match="proposal_rationale cannot be empty"):
            _make_proposal(proposal_rationale="")

    def test_missing_context_hash_raises(self):
        with pytest.raises(ValueError, match="context_hash cannot be empty"):
            _make_proposal(context_hash="")


class TestAllocationProposalImmutability:
    def test_cannot_modify_proposal_id(self):
        proposal = _make_proposal()
        with pytest.raises(ImmutabilityViolationException):
            proposal.proposal_id = "changed"

    def test_cannot_modify_total_capital(self):
        proposal = _make_proposal()
        with pytest.raises(ImmutabilityViolationException):
            proposal.total_capital = 999999.0

    def test_cannot_modify_proposed_weights(self):
        proposal = _make_proposal()
        with pytest.raises(ImmutabilityViolationException):
            proposal.proposed_weights = {}

    def test_cannot_modify_proposal_rationale(self):
        proposal = _make_proposal()
        with pytest.raises(ImmutabilityViolationException):
            proposal.proposal_rationale = "changed"

    def test_cannot_delete_field(self):
        proposal = _make_proposal()
        with pytest.raises(ImmutabilityViolationException):
            del proposal.proposal_id
