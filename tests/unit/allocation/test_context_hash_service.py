"""Tests for ContextHashService — Sprint-06 Wave-4."""
import pytest

from karsa.allocation.application.service.context_hash_service import ContextHashService
from karsa.allocation.domain.model.value_objects import ProposedWeight, RiskBudget


def _make_weight(urn, weight):
    return ProposedWeight(
        worker_urn=urn,
        proposed_weight=weight,
        ranking_score=0.5,
        eligibility_status="ALLOCATABLE",
        rationale="Test",
        risk_budget=RiskBudget(0.15, 0.10, 0.40),
    )


class TestContextHashService:
    def setup_method(self):
        self.service = ContextHashService()

    def test_deterministic_hash(self):
        workers = [
            {"worker_urn": "w1", "eligibility_status": "ALLOCATABLE", "cumulative_alpha": 0.5, "max_drawdown": 0.0, "observation_count": 10},
            {"worker_urn": "w2", "eligibility_status": "ALLOCATABLE", "cumulative_alpha": 0.3, "max_drawdown": 0.1, "observation_count": 5},
        ]
        weights = {"w1": _make_weight("w1", 0.6), "w2": _make_weight("w2", 0.4)}

        hash1 = self.service.generate_context_hash(workers, "policy-1", weights)
        hash2 = self.service.generate_context_hash(workers, "policy-1", weights)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_hash_changes_with_different_workers(self):
        workers1 = [{"worker_urn": "w1", "eligibility_status": "ALLOCATABLE", "cumulative_alpha": 0.5, "max_drawdown": 0.0, "observation_count": 10}]
        workers2 = [{"worker_urn": "w2", "eligibility_status": "ALLOCATABLE", "cumulative_alpha": 0.3, "max_drawdown": 0.1, "observation_count": 5}]
        weights = {"w1": _make_weight("w1", 1.0)}

        hash1 = self.service.generate_context_hash(workers1, "policy-1", weights)
        hash2 = self.service.generate_context_hash(workers2, "policy-1", weights)

        assert hash1 != hash2

    def test_hash_changes_with_different_policy(self):
        workers = [{"worker_urn": "w1", "eligibility_status": "ALLOCATABLE", "cumulative_alpha": 0.5, "max_drawdown": 0.0, "observation_count": 10}]
        weights = {"w1": _make_weight("w1", 1.0)}

        hash1 = self.service.generate_context_hash(workers, "policy-1", weights)
        hash2 = self.service.generate_context_hash(workers, "policy-2", weights)

        assert hash1 != hash2

    def test_hash_changes_with_different_weights(self):
        workers = [{"worker_urn": "w1", "eligibility_status": "ALLOCATABLE", "cumulative_alpha": 0.5, "max_drawdown": 0.0, "observation_count": 10}]
        weights1 = {"w1": _make_weight("w1", 0.6)}
        weights2 = {"w1": _make_weight("w1", 0.4)}

        hash1 = self.service.generate_context_hash(workers, "policy-1", weights1)
        hash2 = self.service.generate_context_hash(workers, "policy-1", weights2)

        assert hash1 != hash2

    def test_empty_inputs(self):
        hash_val = self.service.generate_context_hash([], "policy-1", {})
        assert len(hash_val) == 64
