"""Tests for CIO proposal decision workflow — Sprint-06 Wave-4."""
import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519

from karsa.cio.services import CIODecisionService
from karsa.cio.models import CIODecisionAggregate
from karsa.cio.value_objects import CommitteeVote, OverrideReason
from karsa.cio.repositories import InMemoryCIODecisionRepository
from karsa.cio.exceptions import QuorumNotMetException, DuplicateJournalRefException
from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, RiskBudget, PolicySnapshot, PortfolioContext,
    ExpectedOutcome, RiskAssessment, ReviewHorizon
)
from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository


# --- In-memory test doubles ---

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
        return [p for p in self._proposals.values() if p.policy_id == policy_id][offset:offset + limit]

    def exists(self, proposal_id):
        return proposal_id in self._proposals


class InMemoryProjectionRepo(ProposalStatusProjectionRepository):
    def __init__(self):
        self._projections = {}

    def get_status(self, proposal_id):
        return self._projections.get(proposal_id)

    def list_by_status(self, status, limit=50, offset=0):
        return [p for p in self._projections.values() if p.status == status][offset:offset + limit]

    def list_all(self, limit=100, offset=0):
        return list(self._projections.values())[offset:offset + limit]

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
    def __init__(self, existing_journals=None):
        self._existing = existing_journals or set()

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


# --- Fixtures ---

def _make_proposal(proposal_id="urn:karsa:proposal:p1", journal_ref="urn:karsa:journal:j1"):
    return AllocationProposal(
        proposal_id=proposal_id,
        policy_id="policy-1",
        policy_snapshot=PolicySnapshot(policy_id="policy-1", policy_version=1, policy_hash="h", active_rules=[]),
        journal_ref=journal_ref,
        proposed_weights={
            "w1": ProposedWeight(
                worker_urn="w1", proposed_weight=0.6, ranking_score=0.8,
                eligibility_status="ALLOCATABLE", rationale="Top",
                risk_budget=RiskBudget(0.15, 0.10, 0.40),
            ),
            "w2": ProposedWeight(
                worker_urn="w2", proposed_weight=0.4, ranking_score=0.5,
                eligibility_status="ALLOCATABLE", rationale="Second",
                risk_budget=RiskBudget(0.15, 0.10, 0.40),
            ),
        },
        total_capital=100000.0,
        proposal_rationale="Test proposal.",
        portfolio_context=PortfolioContext(
            current_gross_exposure=0.0, current_net_exposure=0.0,
            current_cash_ratio=1.0, current_concentration=0.0,
            projected_gross_exposure=1.0, projected_net_exposure=1.0,
            projected_cash_ratio=0.0, projected_concentration=0.6,
            cash_allocation_pct=0.0, concentration_impact="MEDIUM",
            alternatives_considered=[],
        ),
        context_hash="hash123",
        generated_at=datetime.utcnow(),
    )


def _make_expected_outcome():
    return ExpectedOutcome(
        expected_return_bps=50.0, expected_drawdown_pct=5.0,
        expected_sharpe_ratio=1.5, expected_horizon_days=30,
        confidence_level=0.7, benchmark_urn=None, regime_at_decision=None,
        key_assumptions=[], attribution_expectations={},
    )


def _make_risk_assessment():
    return RiskAssessment(
        worst_case_loss_pct=8.0, concentration_risk="LOW",
        liquidity_risk="LOW", regime_sensitivity="MEDIUM",
    )


def _make_review_horizon():
    return ReviewHorizon(
        review_date="2026-07-20T00:00:00Z",
        review_criteria="Evaluate performance.",
    )


def _approve_votes():
    return [CommitteeVote(voter_id="cio-1", vote_type="APPROVE", timestamp=datetime.utcnow())]


def _reject_votes():
    return [CommitteeVote(voter_id="cio-1", vote_type="REJECT", timestamp=datetime.utcnow())]


def _setup_service(journals=None):
    private_key = ed25519.Ed25519PrivateKey.generate()
    decision_repo = InMemoryCIODecisionRepository()
    proposal_repo = InMemoryProposalRepo()
    projection_repo = InMemoryProjectionRepo()
    journal_port = FakeJournalPort(journals or set())
    governance_port = FakeGovernancePort()
    publisher = InMemoryEventPublisher()

    service = CIODecisionService(
        decision_repo=decision_repo,
        journal_port=journal_port,
        governance_port=governance_port,
        event_publisher=publisher,
        private_key=private_key,
        proposal_repo=proposal_repo,
        projection_repo=projection_repo,
    )
    return service, decision_repo, proposal_repo, projection_repo, publisher


class TestApproveProposal:
    def test_approve_success(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, publisher = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        decision = service.approve_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            expected_outcome=_make_expected_outcome(),
            risk_assessment=_make_risk_assessment(),
            review_horizon=_make_review_horizon(),
            votes=_approve_votes(),
        )

        assert decision.action_type == "APPROVE_ALLOCATION"
        assert decision.proposal_id == proposal.proposal_id
        assert decision.expected_outcome is not None
        assert decision.risk_assessment is not None
        assert decision.review_horizon is not None
        assert len(decision.cryptographic_signature) > 0

    def test_approve_emits_two_events(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, publisher = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        service.approve_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            expected_outcome=_make_expected_outcome(),
            risk_assessment=_make_risk_assessment(),
            review_horizon=_make_review_horizon(),
            votes=_approve_votes(),
        )

        assert len(publisher.events) == 2
        event_types = [e.event_type for e in publisher.events]
        assert "AllocationProposalApprovedEvent" in event_types
        assert "PortfolioDecisionMadeEvent" in event_types

    def test_approve_nonexistent_proposal_raises(self):
        service, _, _, _, _ = _setup_service()
        with pytest.raises(ValueError, match="not found"):
            service.approve_proposal(
                proposal_id="nonexistent",
                decision_id="dec-1",
                expected_outcome=_make_expected_outcome(),
                risk_assessment=_make_risk_assessment(),
                review_horizon=_make_review_horizon(),
                votes=_approve_votes(),
            )

    def test_approve_already_decided_raises(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, _ = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.mark_approved(proposal.proposal_id, "dec-0", "cio", "2026-06-20T00:00:00", event_sequence=10)

        with pytest.raises(ValueError, match="not PENDING"):
            service.approve_proposal(
                proposal_id=proposal.proposal_id,
                decision_id="dec-1",
                expected_outcome=_make_expected_outcome(),
                risk_assessment=_make_risk_assessment(),
                review_horizon=_make_review_horizon(),
                votes=_approve_votes(),
            )

    def test_approve_journal_reuse_blocked(self):
        journal_ref = "urn:karsa:journal:j1"
        service, decision_repo, proposal_repo, projection_repo, _ = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        # First approval succeeds
        service.approve_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            expected_outcome=_make_expected_outcome(),
            risk_assessment=_make_risk_assessment(),
            review_horizon=_make_review_horizon(),
            votes=_approve_votes(),
        )

        # Second approval with same journal blocked
        proposal2 = _make_proposal(proposal_id="urn:karsa:proposal:p2", journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal2)
        projection_repo.upsert_pending(proposal2.proposal_id, event_sequence=2)

        with pytest.raises(DuplicateJournalRefException):
            service.approve_proposal(
                proposal_id=proposal2.proposal_id,
                decision_id="dec-2",
                expected_outcome=_make_expected_outcome(),
                risk_assessment=_make_risk_assessment(),
                review_horizon=_make_review_horizon(),
                votes=_approve_votes(),
            )

    def test_approve_quorum_failure_raises(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, _ = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        with pytest.raises(QuorumNotMetException):
            service.approve_proposal(
                proposal_id=proposal.proposal_id,
                decision_id="dec-1",
                expected_outcome=_make_expected_outcome(),
                risk_assessment=_make_risk_assessment(),
                review_horizon=_make_review_horizon(),
                votes=[],  # no votes
            )


class TestRejectProposal:
    def test_reject_success(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, publisher = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        decision = service.reject_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            rejection_reason="Insufficient conviction.",
            votes=_reject_votes(),
        )

        assert decision.action_type == "REJECT_ALLOCATION"
        assert decision.override_reason is not None
        assert decision.override_reason.justification == "Insufficient conviction."

    def test_reject_emits_two_events(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, publisher = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        service.reject_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            rejection_reason="Low confidence.",
            votes=_reject_votes(),
        )

        assert len(publisher.events) == 2
        event_types = [e.event_type for e in publisher.events]
        assert "AllocationProposalRejectedEvent" in event_types
        assert "PortfolioDecisionMadeEvent" in event_types

    def test_reject_quorum_failure_raises(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, _ = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        with pytest.raises(QuorumNotMetException):
            service.reject_proposal(
                proposal_id=proposal.proposal_id,
                decision_id="dec-1",
                rejection_reason="reason",
                votes=_approve_votes(),  # approvals, not rejections
            )


class TestModifyProposal:
    def test_modify_success(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, publisher = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        decision = service.modify_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            modified_weights={"w1": 0.7, "w2": 0.3},
            modification_reason="Risk adjustment.",
            expected_outcome=_make_expected_outcome(),
            risk_assessment=_make_risk_assessment(),
            review_horizon=_make_review_horizon(),
            votes=_approve_votes(),
        )

        assert decision.action_type == "OVERRIDE"
        assert decision.override_reason.justification == "Risk adjustment."
        assert decision.decision_payload["allocated_weights"] == {"w1": 0.7, "w2": 0.3}

    def test_modify_weight_sum_exceeds_one_raises(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, _ = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        with pytest.raises(ValueError, match="exceeds 1.0"):
            service.modify_proposal(
                proposal_id=proposal.proposal_id,
                decision_id="dec-1",
                modified_weights={"w1": 0.6, "w2": 0.5},  # sum = 1.1
                modification_reason="test",
                expected_outcome=_make_expected_outcome(),
                risk_assessment=_make_risk_assessment(),
                review_horizon=_make_review_horizon(),
                votes=_approve_votes(),
            )

    def test_modify_negative_weight_raises(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, _ = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        with pytest.raises(ValueError, match="cannot be negative"):
            service.modify_proposal(
                proposal_id=proposal.proposal_id,
                decision_id="dec-1",
                modified_weights={"w1": -0.1, "w2": 0.5},
                modification_reason="test",
                expected_outcome=_make_expected_outcome(),
                risk_assessment=_make_risk_assessment(),
                review_horizon=_make_review_horizon(),
                votes=_approve_votes(),
            )

    def test_modify_emits_two_events(self):
        journal_ref = "urn:karsa:journal:j1"
        service, _, proposal_repo, projection_repo, publisher = _setup_service({journal_ref})

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.upsert_pending(proposal.proposal_id, event_sequence=1)

        service.modify_proposal(
            proposal_id=proposal.proposal_id,
            decision_id="dec-1",
            modified_weights={"w1": 0.7, "w2": 0.3},
            modification_reason="Adjust.",
            expected_outcome=_make_expected_outcome(),
            risk_assessment=_make_risk_assessment(),
            review_horizon=_make_review_horizon(),
            votes=_approve_votes(),
        )

        assert len(publisher.events) == 2
        event_types = [e.event_type for e in publisher.events]
        assert "AllocationProposalModifiedEvent" in event_types
        assert "PortfolioDecisionMadeEvent" in event_types
