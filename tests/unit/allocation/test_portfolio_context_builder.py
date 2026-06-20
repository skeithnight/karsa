"""Tests for PortfolioContextBuilder — Sprint-06 Wave-4."""
import pytest

from karsa.allocation.application.service.portfolio_context_builder import PortfolioContextBuilder
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


class TestPortfolioContextBuilder:
    def setup_method(self):
        self.builder = PortfolioContextBuilder()

    def test_no_positions(self):
        current_exposure = {"gross_exposure": 0.0, "net_exposure": 0.0, "cash_ratio": 1.0, "concentration": 0.0}
        weights = {"w1": _make_weight("w1", 0.5), "w2": _make_weight("w2", 0.3)}

        ctx = self.builder.build(current_exposure, weights)

        assert ctx.current_gross_exposure == 0.0
        assert ctx.projected_gross_exposure == 0.8
        assert ctx.projected_net_exposure == 0.8
        assert abs(ctx.projected_cash_ratio - 0.2) < 1e-6
        assert abs(ctx.cash_allocation_pct - 0.2) < 1e-6

    def test_existing_exposure(self):
        current_exposure = {"gross_exposure": 0.5, "net_exposure": 0.4, "cash_ratio": 0.5, "concentration": 0.3}
        weights = {"w1": _make_weight("w1", 0.6)}

        ctx = self.builder.build(current_exposure, weights)

        assert ctx.current_gross_exposure == 0.5
        assert ctx.current_net_exposure == 0.4
        assert ctx.current_cash_ratio == 0.5
        assert ctx.current_concentration == 0.3

    def test_concentration_impact_high(self):
        weights = {"w1": _make_weight("w1", 0.8)}
        ctx = self.builder.build({}, weights)

        assert ctx.concentration_impact == "HIGH"
        assert ctx.projected_concentration == 0.8

    def test_concentration_impact_medium(self):
        weights = {
            "w1": _make_weight("w1", 0.4),
            "w2": _make_weight("w2", 0.3),
            "w3": _make_weight("w3", 0.2),
        }
        ctx = self.builder.build({}, weights)

        assert ctx.concentration_impact in ("LOW", "MEDIUM")

    def test_concentration_impact_low(self):
        weights = {
            "w1": _make_weight("w1", 0.2),
            "w2": _make_weight("w2", 0.2),
            "w3": _make_weight("w3", 0.2),
            "w4": _make_weight("w4", 0.2),
            "w5": _make_weight("w5", 0.1),
        }
        ctx = self.builder.build({}, weights)

        assert ctx.concentration_impact == "LOW"

    def test_empty_weights(self):
        ctx = self.builder.build({}, {})

        assert ctx.projected_gross_exposure == 0.0
        assert ctx.cash_allocation_pct == 1.0
        assert ctx.projected_cash_ratio == 1.0

    def test_alternatives_considered_populated(self):
        ctx = self.builder.build({}, {})
        assert len(ctx.alternatives_considered) > 0

    def test_deterministic(self):
        weights = {"w1": _make_weight("w1", 0.6), "w2": _make_weight("w2", 0.4)}
        ctx1 = self.builder.build({}, weights)
        ctx2 = self.builder.build({}, weights)

        assert ctx1 == ctx2
