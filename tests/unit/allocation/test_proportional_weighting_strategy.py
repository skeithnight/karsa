"""Tests for ProportionalWeightingStrategy — Sprint-06 Wave-4."""
import pytest

from karsa.allocation.application.service.proportional_weighting_strategy import ProportionalWeightingStrategy


def _make_worker(urn, score, eligibility="ALLOCATABLE", alpha=0.5, drawdown=0.0, obs=10):
    return {
        "worker_urn": urn,
        "eligibility_status": eligibility,
        "cumulative_alpha": alpha,
        "max_drawdown": drawdown,
        "observation_count": obs,
        "ranking_explanation": {
            "final_score": score,
            "reward_factor": alpha,
            "risk_penalty": drawdown * 1.5,
        },
    }


class TestProportionalWeightingStrategy:
    def setup_method(self):
        self.strategy = ProportionalWeightingStrategy()

    def test_single_worker(self):
        workers = [_make_worker("w1", 0.80)]
        result = self.strategy.compute_weights(workers, total_capital=100000)

        assert len(result) == 1
        assert "w1" in result
        # Single worker gets 1.0 minus exploration floor (which is reserved but allocated to the only worker)
        assert result["w1"].proposed_weight > 0.0
        assert result["w1"].proposed_weight <= 1.0

    def test_multiple_workers_proportional(self):
        workers = [
            _make_worker("w1", 0.45),
            _make_worker("w2", 0.30),
            _make_worker("w3", 0.25),
        ]
        result = self.strategy.compute_weights(workers, total_capital=100000)

        assert len(result) == 3
        # Total should be <= 1.0
        total = sum(w.proposed_weight for w in result.values())
        assert total <= 1.0 + 1e-9
        # All weights should be positive
        for w in result.values():
            assert w.proposed_weight > 0.0

    def test_equal_scores(self):
        workers = [
            _make_worker("w1", 0.50),
            _make_worker("w2", 0.50),
            _make_worker("w3", 0.50),
        ]
        result = self.strategy.compute_weights(workers, total_capital=100000)

        assert len(result) == 3
        # All weights should be approximately equal
        weights = [w.proposed_weight for w in result.values()]
        assert max(weights) - min(weights) < 1e-6

    def test_ineligible_workers_excluded(self):
        workers = [
            _make_worker("w1", 0.80, eligibility="ALLOCATABLE"),
            _make_worker("w2", 0.60, eligibility="BLOCKED"),
            _make_worker("w3", 0.40, eligibility="LIMITED"),
        ]
        result = self.strategy.compute_weights(workers, total_capital=100000)

        assert len(result) == 1
        assert "w1" in result
        assert "w2" not in result
        assert "w3" not in result

    def test_zero_workers(self):
        result = self.strategy.compute_weights([], total_capital=100000)
        assert result == {}

    def test_all_ineligible(self):
        workers = [
            _make_worker("w1", 0.80, eligibility="BLOCKED"),
        ]
        result = self.strategy.compute_weights(workers, total_capital=100000)
        assert result == {}

    def test_diversification_cap(self):
        # One worker with very high score
        workers = [
            _make_worker("w1", 0.90),
            _make_worker("w2", 0.05),
            _make_worker("w3", 0.05),
        ]
        result = self.strategy.compute_weights(
            workers, total_capital=100000, max_weight_per_worker=0.40
        )

        # w1 should be capped at 0.40
        assert result["w1"].proposed_weight <= 0.40 + 1e-6

    def test_zero_scores_equal_weight(self):
        workers = [
            _make_worker("w1", 0.0),
            _make_worker("w2", 0.0),
        ]
        result = self.strategy.compute_weights(workers, total_capital=100000)

        assert len(result) == 2
        # Should get equal weights (minus exploration floor)
        weights = sorted([w.proposed_weight for w in result.values()])
        assert abs(weights[0] - weights[1]) < 1e-6

    def test_deterministic(self):
        workers = [
            _make_worker("w1", 0.60),
            _make_worker("w2", 0.30),
        ]
        result1 = self.strategy.compute_weights(workers, 100000)
        result2 = self.strategy.compute_weights(workers, 100000)

        for urn in result1:
            assert abs(result1[urn].proposed_weight - result2[urn].proposed_weight) < 1e-10

    def test_no_negative_weights(self):
        workers = [
            _make_worker("w1", 0.99),
            _make_worker("w2", 0.01),
        ]
        result = self.strategy.compute_weights(workers, 100000)

        for urn, w in result.items():
            assert w.proposed_weight >= 0.0

    def test_rationale_populated(self):
        workers = [_make_worker("w1", 0.80, alpha=0.66, drawdown=0.05)]
        result = self.strategy.compute_weights(workers, 100000)

        assert "w1" in result
        assert "0.8000" in result["w1"].rationale or "0.8" in result["w1"].rationale
        assert "cumulative alpha" in result["w1"].rationale.lower() or "Cumulative alpha" in result["w1"].rationale
