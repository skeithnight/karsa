"""Tests for CIO decision API (proposal workflow) — Sprint-06 Wave-7."""
import pytest
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi.testclient import TestClient
from fastapi import FastAPI

from karsa.cio.api import router, get_decision_service
from karsa.cio.services import CIODecisionService
from karsa.cio.repositories import InMemoryCIODecisionRepository
from karsa.cio.exceptions import QuorumNotMetException, DuplicateJournalRefException
from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, RiskBudget, PolicySnapshot, PortfolioContext
)
from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository


# --- Test doubles ---

class InMemoryProposalRepo(AllocationProposalRepository):
    def __init__(self):
        self._proposals = {}

    def save_proposal(self, proposal):
        self._proposals[proposal.proposal_id] = proposal

    def get_proposal_by_id(self, proposal_id):
        return self._proposals.get(proposal_id)

    def list_proposals(self, limit=50, offset=0):
        return list(self._proposals.values())

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


def _approve_request(proposal_id="urn:karsa:proposal:p1", decision_id="dec-1"):
    return {
        "proposal_id": proposal_id,
        "decision_id": decision_id,
        "action_type": "APPROVE_ALLOCATION",
        "votes": [{"voter_id": "cio-1", "vote_type": "APPROVE"}],
        "expected_outcome": {
            "expected_return_bps": 50,
            "expected_drawdown_pct": 5,
            "expected_sharpe_ratio": 1.5,
            "expected_horizon_days": 30,
            "confidence_level": 0.7,
        },
        "risk_assessment": {
            "worst_case_loss_pct": 8,
            "concentration_risk": "LOW",
            "liquidity_risk": "LOW",
            "regime_sensitivity": "MEDIUM",
        },
        "review_horizon": {
            "review_date": "2026-07-20T00:00:00Z",
            "review_criteria": "Evaluate performance.",
        },
    }


def _reject_request(proposal_id="urn:karsa:proposal:p1", decision_id="dec-1"):
    return {
        "proposal_id": proposal_id,
        "decision_id": decision_id,
        "action_type": "REJECT_ALLOCATION",
        "rejection_reason": "Insufficient conviction.",
        "votes": [{"voter_id": "cio-1", "vote_type": "REJECT"}],
    }


def _modify_request(proposal_id="urn:karsa:proposal:p1", decision_id="dec-1"):
    return {
        "proposal_id": proposal_id,
        "decision_id": decision_id,
        "action_type": "OVERRIDE",
        "modified_weights": {"w1": 0.7, "w2": 0.3},
        "modification_reason": "Risk adjustment.",
        "votes": [{"voter_id": "cio-1", "vote_type": "APPROVE"}],
        "expected_outcome": {
            "expected_return_bps": 50,
            "expected_drawdown_pct": 5,
            "expected_sharpe_ratio": 1.5,
            "expected_horizon_days": 30,
            "confidence_level": 0.7,
        },
        "risk_assessment": {
            "worst_case_loss_pct": 8,
            "concentration_risk": "LOW",
            "liquidity_risk": "LOW",
            "regime_sensitivity": "MEDIUM",
        },
        "review_horizon": {
            "review_date": "2026-07-20T00:00:00Z",
            "review_criteria": "Evaluate performance.",
        },
    }


def _create_app(service):
    app = FastAPI()
    app.dependency_overrides[get_decision_service] = lambda: service
    app.include_router(router)
    return app


class TestApproveProposal:
    def test_success(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
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

        app = _create_app(service)
        client = TestClient(app)

        response = client.post("/cio/decisions/proposal", json=_approve_request())
        assert response.status_code == 201
        data = response.json()
        assert data["decision_id"] == "dec-1"
        assert data["status"] == "SEALED"
        assert "cryptographic_signature" in data

    def test_missing_expected_outcome(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
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

        app = _create_app(service)
        client = TestClient(app)

        request = _approve_request()
        del request["expected_outcome"]
        response = client.post("/cio/decisions/proposal", json=request)
        assert response.status_code == 400

    def test_proposal_not_found(self):
        service = CIODecisionService(
            decision_repo=InMemoryCIODecisionRepository(),
            journal_port=FakeJournalPort(),
            governance_port=FakeGovernancePort(),
            event_publisher=InMemoryEventPublisher(),
            private_key=ed25519.Ed25519PrivateKey.generate(),
            proposal_repo=InMemoryProposalRepo(),
            projection_repo=InMemoryProjectionRepo(),
        )

        app = _create_app(service)
        client = TestClient(app)

        response = client.post("/cio/decisions/proposal", json=_approve_request("nonexistent"))
        assert response.status_code == 404

    def test_already_decided(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
        publisher = InMemoryEventPublisher()

        proposal = _make_proposal(journal_ref=journal_ref)
        proposal_repo.save_proposal(proposal)
        projection_repo.mark_approved(proposal.proposal_id, "dec-0", "cio", "2026-06-20T00:00:00", 10)

        service = CIODecisionService(
            decision_repo=decision_repo,
            journal_port=FakeJournalPort({journal_ref}),
            governance_port=FakeGovernancePort(),
            event_publisher=publisher,
            private_key=ed25519.Ed25519PrivateKey.generate(),
            proposal_repo=proposal_repo,
            projection_repo=projection_repo,
        )

        app = _create_app(service)
        client = TestClient(app)

        response = client.post("/cio/decisions/proposal", json=_approve_request())
        assert response.status_code == 409


class TestRejectProposal:
    def test_success(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
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

        app = _create_app(service)
        client = TestClient(app)

        response = client.post("/cio/decisions/proposal", json=_reject_request())
        assert response.status_code == 201

    def test_missing_rejection_reason(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
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

        app = _create_app(service)
        client = TestClient(app)

        request = _reject_request()
        del request["rejection_reason"]
        response = client.post("/cio/decisions/proposal", json=request)
        assert response.status_code == 400


class TestModifyProposal:
    def test_success(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
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

        app = _create_app(service)
        client = TestClient(app)

        response = client.post("/cio/decisions/proposal", json=_modify_request())
        assert response.status_code == 201

    def test_invalid_weight_sum(self):
        journal_ref = "urn:karsa:journal:j1"
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        decision_repo = InMemoryCIODecisionRepository()
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

        app = _create_app(service)
        client = TestClient(app)

        request = _modify_request()
        request["modified_weights"] = {"w1": 0.6, "w2": 0.5}  # sum = 1.1
        response = client.post("/cio/decisions/proposal", json=request)
        assert response.status_code == 400
