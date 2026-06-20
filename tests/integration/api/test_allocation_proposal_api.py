"""Tests for allocation proposal API — Sprint-06 Wave-7.

Uses FastAPI TestClient with mocked services.
"""
import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi.testclient import TestClient

from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, RiskBudget, PolicySnapshot, PortfolioContext
)
from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository
from karsa.allocation.application.service.allocation_recommendation_service import AllocationRecommendationService
from karsa.allocation.application.service.proportional_weighting_strategy import ProportionalWeightingStrategy


# --- In-memory test doubles ---

class InMemoryProposalRepo(AllocationProposalRepository):
    def __init__(self):
        self._proposals = {}

    def save_proposal(self, proposal):
        self._proposals[proposal.proposal_id] = proposal

    def get_proposal_by_id(self, proposal_id):
        return self._proposals.get(proposal_id)

    def list_proposals(self, limit=50, offset=0):
        items = sorted(self._proposals.values(), key=lambda p: p.generated_at, reverse=True)
        return items[offset:offset + limit]

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


class InMemoryEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class FakeIntelligenceService:
    def __init__(self, workers=None):
        self._workers = workers or []

    def query_allocation_readiness(self):
        class Response:
            def __init__(self, data):
                self.data = data
        return Response(self._workers)


def _make_worker(urn, score):
    return {
        "worker_urn": urn,
        "eligibility_status": "ALLOCATABLE",
        "cumulative_alpha": score * 0.8,
        "max_drawdown": 0.0,
        "observation_count": 10,
        "ranking_explanation": {"final_score": score, "reward_factor": score * 0.8, "risk_penalty": 0.0},
    }


# --- App fixture ---

def _create_app(proposal_repo, projection_repo, intelligence_service, event_publisher):
    from fastapi import FastAPI
    from karsa.allocation.api.routes import router, get_recommendation_service, get_projection_repo

    app = FastAPI()

    service = AllocationRecommendationService(
        proposal_repo=proposal_repo,
        weighting_strategy=ProportionalWeightingStrategy(),
        intelligence_query_service=intelligence_service,
        event_publisher=event_publisher,
    )

    app.dependency_overrides[get_recommendation_service] = lambda: service
    app.dependency_overrides[get_projection_repo] = lambda: projection_repo
    app.include_router(router)

    return app


class TestGenerateProposal:
    def test_success(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80), _make_worker("w2", 0.60)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.post("/allocation/proposals", json={"total_capital": 100000})

        assert response.status_code == 201
        data = response.json()
        assert data["proposal_id"].startswith("urn:karsa:proposal:")
        assert data["total_capital"] == 100000
        assert data["status"] == "PENDING"
        assert len(data["proposed_weights"]) == 2

    def test_invalid_capital_zero(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.post("/allocation/proposals", json={"total_capital": 0})
        assert response.status_code == 422  # Pydantic validation

    def test_invalid_capital_negative(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.post("/allocation/proposals", json={"total_capital": -100})
        assert response.status_code == 422

    def test_no_workers(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.post("/allocation/proposals", json={"total_capital": 100000})
        assert response.status_code == 400

    def test_with_policy_id(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.post("/allocation/proposals", json={
            "total_capital": 100000,
            "policy_id": "custom-policy",
        })

        assert response.status_code == 201
        assert response.json()["policy_id"] == "custom-policy"


class TestListProposals:
    def test_empty_list(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService()

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.get("/allocation/proposals")
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_with_data(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        # Generate two proposals
        client.post("/allocation/proposals", json={"total_capital": 100000})
        client.post("/allocation/proposals", json={"total_capital": 200000})

        response = client.get("/allocation/proposals")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    def test_pagination(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        for i in range(5):
            client.post("/allocation/proposals", json={"total_capital": 10000 * (i + 1)})

        response = client.get("/allocation/proposals?page=1&size=2")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2


class TestGetProposal:
    def test_success(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        create_response = client.post("/allocation/proposals", json={"total_capital": 100000})
        proposal_id = create_response.json()["proposal_id"]

        # Simulate projection worker processing the event
        projection_repo.upsert_pending(proposal_id, event_sequence=1)

        response = client.get(f"/allocation/proposals/{proposal_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["proposal_id"] == proposal_id
        assert data["total_capital"] == 100000
        assert data["status"] == "PENDING"
        assert "portfolio_context" in data
        assert "policy_snapshot" in data

    def test_not_found(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService()

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        response = client.get("/allocation/proposals/nonexistent")
        assert response.status_code == 404

    def test_with_status(self):
        proposal_repo = InMemoryProposalRepo()
        projection_repo = InMemoryProjectionRepo()
        publisher = InMemoryEventPublisher()
        intel = FakeIntelligenceService([_make_worker("w1", 0.80)])

        app = _create_app(proposal_repo, projection_repo, intel, publisher)
        client = TestClient(app)

        create_response = client.post("/allocation/proposals", json={"total_capital": 100000})
        proposal_id = create_response.json()["proposal_id"]

        # Mark as approved
        projection_repo.mark_approved(proposal_id, "dec-1", "cio", "2026-06-20T12:00:00", 10)

        response = client.get(f"/allocation/proposals/{proposal_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"
        assert response.json()["decision_id"] == "dec-1"
