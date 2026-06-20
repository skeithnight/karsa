"""Tests for AllocationRecommendationService — Sprint-06 Wave-4."""
import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any

from karsa.allocation.application.service.allocation_recommendation_service import AllocationRecommendationService
from karsa.allocation.application.service.proportional_weighting_strategy import ProportionalWeightingStrategy
from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import ProposedWeight, RiskBudget
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.cio.exceptions import ImmutabilityViolationException


class InMemoryProposalRepo(AllocationProposalRepository):
    def __init__(self):
        self._proposals = {}

    def save_proposal(self, proposal):
        if proposal.proposal_id in self._proposals:
            raise ImmutabilityViolationException()
        self._proposals[proposal.proposal_id] = proposal

    def get_proposal_by_id(self, proposal_id):
        return self._proposals.get(proposal_id)

    def list_proposals(self, limit=50, offset=0):
        items = sorted(self._proposals.values(), key=lambda p: p.generated_at, reverse=True)
        return items[offset:offset + limit]

    def list_proposals_by_policy(self, policy_id, limit=50, offset=0):
        filtered = [p for p in self._proposals.values() if p.policy_id == policy_id]
        return filtered[offset:offset + limit]

    def exists(self, proposal_id):
        return proposal_id in self._proposals


class InMemoryEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _make_worker(urn, score, eligibility="ALLOCATABLE"):
    return {
        "worker_urn": urn,
        "eligibility_status": eligibility,
        "cumulative_alpha": score * 0.8,
        "max_drawdown": 0.0,
        "observation_count": 10,
        "ranking_explanation": {
            "final_score": score,
            "reward_factor": score * 0.8,
            "risk_penalty": 0.0,
        },
    }


class TestAllocationRecommendationService:
    def setup_method(self):
        self.repo = InMemoryProposalRepo()
        self.strategy = ProportionalWeightingStrategy()
        self.publisher = InMemoryEventPublisher()
        self.service = AllocationRecommendationService(
            proposal_repo=self.repo,
            weighting_strategy=self.strategy,
            event_publisher=self.publisher,
        )

    def test_generate_proposal_success(self):
        workers = [
            _make_worker("w1", 0.80),
            _make_worker("w2", 0.60),
        ]
        proposal = self.service.generate_proposal(
            total_capital=100000,
            ranked_workers=workers,
        )

        assert proposal is not None
        assert proposal.total_capital == 100000
        assert len(proposal.proposed_weights) == 2
        assert proposal.proposal_id.startswith("urn:karsa:proposal:")
        assert proposal.journal_ref.startswith("urn:karsa:journal:")
        assert proposal.context_hash is not None
        assert len(proposal.context_hash) == 64

    def test_generate_proposal_persists(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(100000, workers)

        retrieved = self.repo.get_proposal_by_id(proposal.proposal_id)
        assert retrieved is not None
        assert retrieved.proposal_id == proposal.proposal_id

    def test_generate_proposal_publishes_event(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(100000, workers)

        assert len(self.publisher.events) == 1
        event = self.publisher.events[0]
        assert event.proposal_id == proposal.proposal_id
        assert event.event_type == "AllocationProposalGeneratedEvent"

    def test_no_allocatable_workers_raises(self):
        workers = [_make_worker("w1", 0.80, eligibility="BLOCKED")]
        with pytest.raises(ValueError, match="No allocatable workers"):
            self.service.generate_proposal(100000, workers)

    def test_empty_workers_raises(self):
        with pytest.raises(ValueError, match="No allocatable workers"):
            self.service.generate_proposal(100000, [])

    def test_journal_ref_auto_generated(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(100000, workers)

        assert proposal.journal_ref is not None
        assert len(proposal.journal_ref) > 0

    def test_journal_ref_custom(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(
            100000, workers, journal_ref="urn:karsa:journal:custom"
        )

        assert proposal.journal_ref == "urn:karsa:journal:custom"

    def test_get_proposal(self):
        workers = [_make_worker("w1", 0.80)]
        created = self.service.generate_proposal(100000, workers)

        result = self.service.get_proposal(created.proposal_id)
        assert result is not None
        assert result.proposal_id == created.proposal_id

    def test_get_proposal_not_found(self):
        result = self.service.get_proposal("nonexistent")
        assert result is None

    def test_list_proposals(self):
        workers = [_make_worker("w1", 0.80)]
        self.service.generate_proposal(100000, workers)
        self.service.generate_proposal(200000, workers)

        result = self.service.list_proposals()
        assert len(result) == 2

    def test_policy_snapshot_populated(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(100000, workers, policy_id="test-policy")

        assert proposal.policy_snapshot.policy_id == "test-policy"
        assert proposal.policy_snapshot.policy_version == 1

    def test_portfolio_context_populated(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(100000, workers)

        assert proposal.portfolio_context is not None
        assert proposal.portfolio_context.concentration_impact in ("LOW", "MEDIUM", "HIGH")

    def test_proposal_rationale_populated(self):
        workers = [_make_worker("w1", 0.80)]
        proposal = self.service.generate_proposal(100000, workers)

        assert len(proposal.proposal_rationale) > 0
        assert "w1" in proposal.proposal_rationale or "analyst" in proposal.proposal_rationale.lower() or "Proportional" in proposal.proposal_rationale
