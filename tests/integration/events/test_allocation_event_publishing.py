"""Tests for allocation event publishing — Sprint-06 Wave-5.

Verifies that services publish the correct events.
"""
import pytest
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519

from karsa.allocation.application.service.allocation_recommendation_service import AllocationRecommendationService
from karsa.allocation.application.service.proportional_weighting_strategy import ProportionalWeightingStrategy
from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, RiskBudget, PolicySnapshot, PortfolioContext,
    ExpectedOutcome, RiskAssessment, ReviewHorizon
)
from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository
from karsa.cio.services import CIODecisionService
from karsa.cio.repositories import InMemoryCIODecisionRepository
from karsa.cio.value_objects import CommitteeVote


# --- Test doubles ---

class InMemoryProposalRepo(AllocationProposalRepository):
    def __init__(self):
        self._proposals = {}

    def save_proposal(self, proposal):
        self._proposals[proposal.proposal_id] = proposal

    def get_proposal_by_id(self, proposal_id):
        return self._proposals.get(proposal_id)

    def list_proposals(self, limit=50, offset=0):
        return list(self._proposals.values())[offset:offset + limit]

    def list_proposals_by_policy(self, policy_id, limit=50, offset=0):
        return [p for p in self._proposals.values() if p.policy_id == policy_id]

    def exists(self, proposal_id):
        return proposal_id in self._proposals


class InMemoryProjectionRepo(ProposalStatusProjectionRepository):
    def __init__(self):
        self._projections = {}

    def get_status(self, proposal_id):
        return self._projections.get(proposal_id)

    def list_by_status(self, status, limit=50, offset=0):
        return [p for p in self._projections.values() if p.status == status]

    def list_all(self, limit=100, offset=0):
        return list(self._projections.values())

    def upsert_pending(self, proposal_id, event_sequence):
        if proposal_id not in self._projections:
            self._projections[proposal_id] = ProposalStatusProjection(
                proposal_id=proposal_id, status="PENDING", event_sequence=event_sequence,
            )

    def mark_approved(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
        self._projections[proposal_id] = ProposalStatusProjection(
            proposal_id=proposal_id, status="APPROVED", decision_id=decision_id,
            decided_by=decided_by, decided_at=datetime.fromisoformat(decided_at),
            event_sequence=event_sequence,
        )

    def mark_rejected(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
        self._projections[proposal_id] = ProposalStatusProjection(
            proposal_id=proposal_id, status="REJECTED", decision_id=decision_id,
            decided_by=decided_by, decided_at=datetime.fromisoformat(decided_at),
            event_sequence=event_sequence,
        )

    def mark_modified(self, proposal_id, decision_id, decided_by, decided_at, event_sequence):
        self._projections[proposal_id] = ProposalStatusProjection(
            proposal_id=proposal_id, status="MODIFIED", decision_id=decision_id,
            decided_by=decided_by, decided_at=datetime.fromisoformat(decided_at),
            event_sequence=event_sequence,
        )

    def mark_expired(self, proposal_id, decided_at, event_sequence):
        self._projections[proposal_id] = ProposalStatusProjection(
            proposal_id=proposal_id, status="EXPIRED",
            decided_at=datetime.fromisoformat(decided_at),
            event_sequence=event_sequence,
        )


class FakeJournalPort:
    def __init__(self, journals=None):
        self._existing = journals or set()

    def verify_journal_exists(self, journal_ref):
        return journal_ref in self._existing

    def get_journal_expectations(self, journal_ref):
        return {}


class FakeGovernancePort:
    def verify_exception_token(self, exception_id, signature, payload):
        return True


class InMemoryEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _make_worker(urn, score):
    return {
        "worker_urn": urn,
        "eligibility_status": "ALLOCATABLE",
        "cumulative_alpha": score * 0.8,
        "max_drawdown": 0.0,
        "observation_count": 10,
        "ranking_explanation": {"final_score": score, "reward_factor": score * 0.8, "risk_penalty": 0.0},
    }


def _make_proposal(proposal_id="urn:karsa:proposal:p1", journal_ref="urn:karsa:journal:j1"):
    return AllocationProposal(
        proposal_id=proposal_id,
        policy_id="policy-1",
        policy_snapshot=PolicySnapshot(policy_id="policy-1", policy_version=1, policy_hash="h", active_rules=[]),
        journal_ref=journal_ref,
        proposed_weights={
            "w1": ProposedWeight(worker_urn="w1", proposed_weight=0.6, ranking_score=0.8,
                                 eligibility_status="ALLOCATABLE", rationale="Top",
                                 risk_budget=RiskBudget(0.15, 0.10, 0.40)),
        },
        total_capital=100000.0,
        proposal_rationale="Test.",
        portfolio_context=PortfolioContext(
            current_gross_exposure=0.0, current_net_exposure=0.0,
            current_cash_ratio=1.0, current_concentration=0.0,
            projected_gross_exposure=0.6, projected_net_exposure=0.6,
            projected_cash_ratio=0.4, projected_concentration=0.6,
            cash_allocation_pct=0.4, concentration_impact="MEDIUM",
            alternatives_considered=[],
        ),
        context_hash="hash123",
        generated_at=datetime.utcnow(),
    )


class TestProposalGenerationPublishesEvent:
    def test_publishes_generated_event(self):
        repo = InMemoryProposalRepo()
        publisher = InMemoryEventPublisher()
        service = AllocationRecommendationService(
            proposal_repo=repo,
            weighting_strategy=ProportionalWeightingStrategy(),
            event_publisher=publisher,
        )

        service.generate_proposal(100000, [_make_worker("w1", 0.80)])

        assert len(publisher.events) == 1
        event = publisher.events[0]
        assert event.event_type == "AllocationProposalGeneratedEvent"
        assert event.proposal_id.startswith("urn:karsa:proposal:")
        assert event.total_capital == 100000.0


class TestProposalApprovalPublishesEvents:
    def test_publishes_approved_and_portfolio_events(self):
        journal_ref = "urn:karsa:journal:j1"
        decision_repo = InMemoryCIODecisionRepository()
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        service = CIODecisionService(
            decision_repo=decision_repo,
            journal_port=FakeJournalPort({journal_ref}),
            governance_port=FakeGovernancePort(),
            event_publisher=publisher,
            private_key=ed25519.Ed25519PrivateKey.generate(),
            proposal_repo=proposal_repo,
            projection_repo=projection_repo,
        )

        service.approve_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            expected_outcome=ExpectedOutcome(
                expected_return_bps=50, expected_drawdown_pct=5, expected_sharpe_ratio=1.5,
                expected_horizon_days=30, confidence_level=0.7, benchmark_urn=None,
                regime_at_decision=None, key_assumptions=[], attribution_expectations={},
            ),
            risk_assessment=RiskAssessment(worst_case_loss_pct=8, concentration_risk="LOW",
                                            liquidity_risk="LOW", regime_sensitivity="MEDIUM"),
            review_horizon=ReviewHorizon(review_date="2026-07-20", review_criteria="Test."),
            votes=[CommitteeVote(voter_id="cio-1", vote_type="APPROVE", timestamp=datetime.utcnow())],
        )

        assert len(publisher.events) == 2
        event_types = [e.event_type for e in publisher.events]
        assert "AllocationProposalApprovedEvent" in event_types
        assert "PortfolioDecisionMadeEvent" in event_types


class TestProposalRejectionPublishesEvents:
    def test_publishes_rejected_and_portfolio_events(self):
        journal_ref = "urn:karsa:journal:j1"
        decision_repo = InMemoryCIODecisionRepository()
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        service = CIODecisionService(
            decision_repo=decision_repo,
            journal_port=FakeJournalPort({journal_ref}),
            governance_port=FakeGovernancePort(),
            event_publisher=publisher,
            private_key=ed25519.Ed25519PrivateKey.generate(),
            proposal_repo=proposal_repo,
            projection_repo=projection_repo,
        )

        service.reject_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            rejection_reason="Low confidence.",
            votes=[CommitteeVote(voter_id="cio-1", vote_type="REJECT", timestamp=datetime.utcnow())],
        )

        assert len(publisher.events) == 2
        event_types = [e.event_type for e in publisher.events]
        assert "AllocationProposalRejectedEvent" in event_types
        assert "PortfolioDecisionMadeEvent" in event_types


class TestProposalModificationPublishesEvents:
    def test_publishes_modified_and_portfolio_events(self):
        journal_ref = "urn:karsa:journal:j1"
        decision_repo = InMemoryCIODecisionRepository()
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        service = CIODecisionService(
            decision_repo=decision_repo,
            journal_port=FakeJournalPort({journal_ref}),
            governance_port=FakeGovernancePort(),
            event_publisher=publisher,
            private_key=ed25519.Ed25519PrivateKey.generate(),
            proposal_repo=proposal_repo,
            projection_repo=projection_repo,
        )

        service.modify_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            modified_weights={"w1": 0.7, "w2": 0.3},
            modification_reason="Risk adjustment.",
            expected_outcome=ExpectedOutcome(
                expected_return_bps=50, expected_drawdown_pct=5, expected_sharpe_ratio=1.5,
                expected_horizon_days=30, confidence_level=0.7, benchmark_urn=None,
                regime_at_decision=None, key_assumptions=[], attribution_expectations={},
            ),
            risk_assessment=RiskAssessment(worst_case_loss_pct=8, concentration_risk="LOW",
                                            liquidity_risk="LOW", regime_sensitivity="MEDIUM"),
            review_horizon=ReviewHorizon(review_date="2026-07-20", review_criteria="Test."),
            votes=[CommitteeVote(voter_id="cio-1", vote_type="APPROVE", timestamp=datetime.utcnow())],
        )

        assert len(publisher.events) == 2
        event_types = [e.event_type for e in publisher.events]
        assert "AllocationProposalModifiedEvent" in event_types
        assert "PortfolioDecisionMadeEvent" in event_types
