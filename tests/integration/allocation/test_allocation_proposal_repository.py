"""Tests for AllocationProposalRepository — Sprint-06 Wave-3.

Uses in-memory implementation for unit-level repository tests.
Postgres integration tests require a running database.
"""
import pytest
from datetime import datetime
from typing import Optional, List, Dict

from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, PolicySnapshot, PortfolioContext, RiskBudget
)
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.cio.exceptions import ImmutabilityViolationException


class InMemoryAllocationProposalRepository(AllocationProposalRepository):
    """In-memory implementation for testing."""
    def __init__(self):
        self._proposals: Dict[str, AllocationProposal] = {}

    def save_proposal(self, proposal: AllocationProposal) -> None:
        if proposal.proposal_id in self._proposals:
            raise ImmutabilityViolationException("Cannot overwrite existing proposal.")
        self._proposals[proposal.proposal_id] = proposal

    def get_proposal_by_id(self, proposal_id: str) -> Optional[AllocationProposal]:
        return self._proposals.get(proposal_id)

    def list_proposals(self, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        proposals = sorted(self._proposals.values(), key=lambda p: p.generated_at, reverse=True)
        return proposals[offset:offset + limit]

    def list_proposals_by_policy(self, policy_id: str, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        filtered = [p for p in self._proposals.values() if p.policy_id == policy_id]
        filtered.sort(key=lambda p: p.generated_at, reverse=True)
        return filtered[offset:offset + limit]

    def exists(self, proposal_id: str) -> bool:
        return proposal_id in self._proposals


def _make_risk_budget():
    return RiskBudget(max_volatility=0.15, max_drawdown=0.10, max_exposure=0.40)


def _make_proposal(proposal_id="urn:karsa:proposal:test-1", policy_id="policy-1"):
    return AllocationProposal(
        proposal_id=proposal_id,
        policy_id=policy_id,
        policy_snapshot=PolicySnapshot(
            policy_id=policy_id,
            policy_version=1,
            policy_hash="hash123",
            active_rules=["DiversificationCap: max 40%"],
        ),
        journal_ref=f"urn:karsa:journal:{proposal_id}",
        proposed_weights={
            "urn:karsa:worker:a1": ProposedWeight(
                worker_urn="urn:karsa:worker:a1",
                proposed_weight=0.50,
                ranking_score=0.80,
                eligibility_status="ALLOCATABLE",
                rationale="Top performer.",
                risk_budget=_make_risk_budget(),
            ),
        },
        total_capital=100000.0,
        proposal_rationale="Test proposal.",
        portfolio_context=PortfolioContext(
            current_gross_exposure=0.0,
            current_net_exposure=0.0,
            current_cash_ratio=1.0,
            current_concentration=0.0,
            projected_gross_exposure=0.50,
            projected_net_exposure=0.50,
            projected_cash_ratio=0.50,
            projected_concentration=0.50,
            cash_allocation_pct=0.50,
            concentration_impact="LOW",
            alternatives_considered=[],
        ),
        context_hash="hash123",
        generated_at=datetime.utcnow(),
    )


class TestAllocationProposalRepository:
    def test_save_and_retrieve(self):
        repo = InMemoryAllocationProposalRepository()
        proposal = _make_proposal()
        repo.save_proposal(proposal)

        result = repo.get_proposal_by_id("urn:karsa:proposal:test-1")
        assert result is not None
        assert result.proposal_id == "urn:karsa:proposal:test-1"
        assert result.total_capital == 100000.0

    def test_get_nonexistent_returns_none(self):
        repo = InMemoryAllocationProposalRepository()
        assert repo.get_proposal_by_id("nonexistent") is None

    def test_exists_true(self):
        repo = InMemoryAllocationProposalRepository()
        repo.save_proposal(_make_proposal())
        assert repo.exists("urn:karsa:proposal:test-1") is True

    def test_exists_false(self):
        repo = InMemoryAllocationProposalRepository()
        assert repo.exists("nonexistent") is False

    def test_immutability_on_overwrite(self):
        repo = InMemoryAllocationProposalRepository()
        repo.save_proposal(_make_proposal())
        with pytest.raises(ImmutabilityViolationException):
            repo.save_proposal(_make_proposal())

    def test_list_proposals_pagination(self):
        repo = InMemoryAllocationProposalRepository()
        for i in range(5):
            repo.save_proposal(_make_proposal(
                proposal_id=f"urn:karsa:proposal:test-{i}",
                policy_id="policy-1",
            ))

        page1 = repo.list_proposals(limit=2, offset=0)
        assert len(page1) == 2

        page2 = repo.list_proposals(limit=2, offset=2)
        assert len(page2) == 2

        page3 = repo.list_proposals(limit=2, offset=4)
        assert len(page3) == 1

    def test_list_proposals_by_policy(self):
        repo = InMemoryAllocationProposalRepository()
        repo.save_proposal(_make_proposal(proposal_id="p1", policy_id="policy-A"))
        repo.save_proposal(_make_proposal(proposal_id="p2", policy_id="policy-B"))
        repo.save_proposal(_make_proposal(proposal_id="p3", policy_id="policy-A"))

        results = repo.list_proposals_by_policy("policy-A")
        assert len(results) == 2
        assert all(p.policy_id == "policy-A" for p in results)

    def test_list_proposals_empty(self):
        repo = InMemoryAllocationProposalRepository()
        assert repo.list_proposals() == []

    def test_proposal_fields_preserved(self):
        repo = InMemoryAllocationProposalRepository()
        proposal = _make_proposal()
        repo.save_proposal(proposal)

        result = repo.get_proposal_by_id("urn:karsa:proposal:test-1")
        assert result.policy_snapshot.policy_id == "policy-1"
        assert result.portfolio_context.concentration_impact == "LOW"
        assert len(result.proposed_weights) == 1
        assert "urn:karsa:worker:a1" in result.proposed_weights
        assert result.proposed_weights["urn:karsa:worker:a1"].proposed_weight == 0.50
