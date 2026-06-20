"""Tests for Sprint-06 value objects — Wave-2."""
import pytest

from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, PolicySnapshot, PortfolioContext, RiskBudget,
    StructuredAssumption, ExpectedOutcome, RiskAssessment, ReviewHorizon
)


class TestRiskBudget:
    def test_valid_risk_budget(self):
        rb = RiskBudget(max_volatility=0.15, max_drawdown=0.10, max_exposure=0.40)
        assert rb.max_volatility == 0.15

    def test_negative_volatility_raises(self):
        with pytest.raises(ValueError, match="max_volatility cannot be negative"):
            RiskBudget(max_volatility=-0.01, max_drawdown=0.10, max_exposure=0.40)

    def test_negative_drawdown_raises(self):
        with pytest.raises(ValueError, match="max_drawdown cannot be negative"):
            RiskBudget(max_volatility=0.15, max_drawdown=-0.01, max_exposure=0.40)

    def test_negative_exposure_raises(self):
        with pytest.raises(ValueError, match="max_exposure cannot be negative"):
            RiskBudget(max_volatility=0.15, max_drawdown=0.10, max_exposure=-0.01)


class TestProposedWeight:
    def _make(self, **overrides):
        defaults = dict(
            worker_urn="urn:karsa:worker:analyst-1",
            proposed_weight=0.30,
            ranking_score=0.66,
            eligibility_status="ALLOCATABLE",
            rationale="Top performer.",
            risk_budget=RiskBudget(0.15, 0.10, 0.40),
        )
        defaults.update(overrides)
        return ProposedWeight(**defaults)

    def test_valid_proposed_weight(self):
        pw = self._make()
        assert pw.worker_urn == "urn:karsa:worker:analyst-1"
        assert pw.proposed_weight == 0.30

    def test_empty_worker_urn_raises(self):
        with pytest.raises(ValueError, match="worker_urn cannot be empty"):
            self._make(worker_urn="")

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="proposed_weight must be between"):
            self._make(proposed_weight=-0.01)

    def test_weight_exceeds_one_raises(self):
        with pytest.raises(ValueError, match="proposed_weight must be between"):
            self._make(proposed_weight=1.01)

    def test_weight_zero_succeeds(self):
        pw = self._make(proposed_weight=0.0)
        assert pw.proposed_weight == 0.0

    def test_weight_one_succeeds(self):
        pw = self._make(proposed_weight=1.0)
        assert pw.proposed_weight == 1.0

    def test_empty_rationale_raises(self):
        with pytest.raises(ValueError, match="rationale cannot be empty"):
            self._make(rationale="")

    def test_invalid_eligibility_status_raises(self):
        with pytest.raises(ValueError, match="eligibility_status must be"):
            self._make(eligibility_status="UNKNOWN")

    def test_frozen_immutability(self):
        pw = self._make()
        with pytest.raises(AttributeError):
            pw.proposed_weight = 0.50


class TestPolicySnapshot:
    def test_valid_policy_snapshot(self):
        ps = PolicySnapshot(policy_id="p1", policy_version=1, policy_hash="hash", active_rules=["rule1"])
        assert ps.policy_id == "p1"

    def test_empty_policy_id_raises(self):
        with pytest.raises(ValueError, match="policy_id cannot be empty"):
            PolicySnapshot(policy_id="", policy_version=1, policy_hash="hash", active_rules=[])

    def test_empty_policy_hash_raises(self):
        with pytest.raises(ValueError, match="policy_hash cannot be empty"):
            PolicySnapshot(policy_id="p1", policy_version=1, policy_hash="", active_rules=[])


class TestPortfolioContext:
    def _make(self, **overrides):
        defaults = dict(
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
            alternatives_considered=["Equal weight"],
        )
        defaults.update(overrides)
        return PortfolioContext(**defaults)

    def test_valid_portfolio_context(self):
        pc = self._make()
        assert pc.concentration_impact == "LOW"

    def test_invalid_concentration_impact_raises(self):
        with pytest.raises(ValueError, match="concentration_impact must be"):
            self._make(concentration_impact="CRITICAL")

    def test_cash_allocation_negative_raises(self):
        with pytest.raises(ValueError, match="cash_allocation_pct must be between"):
            self._make(cash_allocation_pct=-0.01)

    def test_cash_allocation_exceeds_one_raises(self):
        with pytest.raises(ValueError, match="cash_allocation_pct must be between"):
            self._make(cash_allocation_pct=1.01)


class TestStructuredAssumption:
    def test_valid_assumption(self):
        sa = StructuredAssumption(
            assumption_id="a1",
            statement="Market remains bullish",
            validation_criteria="Composite benchmark positive",
            source_urn="urn:karsa:thesis:th-1",
        )
        assert sa.assumption_id == "a1"

    def test_empty_assumption_id_raises(self):
        with pytest.raises(ValueError, match="assumption_id cannot be empty"):
            StructuredAssumption(assumption_id="", statement="x", validation_criteria="y")

    def test_empty_statement_raises(self):
        with pytest.raises(ValueError, match="statement cannot be empty"):
            StructuredAssumption(assumption_id="a1", statement="", validation_criteria="y")

    def test_optional_source_urn(self):
        sa = StructuredAssumption(assumption_id="a1", statement="x", validation_criteria="y")
        assert sa.source_urn is None


class TestExpectedOutcome:
    def _make(self, **overrides):
        defaults = dict(
            expected_return_bps=50.0,
            expected_drawdown_pct=5.0,
            expected_sharpe_ratio=1.5,
            expected_horizon_days=30,
            confidence_level=0.7,
            benchmark_urn="urn:karsa:benchmark:composite",
            regime_at_decision="BULL",
            key_assumptions=[],
            attribution_expectations={"alpha": 0.7, "beta": 0.3},
        )
        defaults.update(overrides)
        return ExpectedOutcome(**defaults)

    def test_valid_expected_outcome(self):
        eo = self._make()
        assert eo.confidence_level == 0.7
        assert eo.expected_horizon_days == 30

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence_level must be between"):
            self._make(confidence_level=-0.1)

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence_level must be between"):
            self._make(confidence_level=1.1)

    def test_zero_horizon_raises(self):
        with pytest.raises(ValueError, match="expected_horizon_days must be positive"):
            self._make(expected_horizon_days=0)

    def test_negative_horizon_raises(self):
        with pytest.raises(ValueError, match="expected_horizon_days must be positive"):
            self._make(expected_horizon_days=-1)


class TestRiskAssessment:
    def _make(self, **overrides):
        defaults = dict(
            worst_case_loss_pct=8.0,
            concentration_risk="LOW",
            liquidity_risk="LOW",
            regime_sensitivity="MEDIUM",
        )
        defaults.update(overrides)
        return RiskAssessment(**defaults)

    def test_valid_risk_assessment(self):
        ra = self._make()
        assert ra.concentration_risk == "LOW"

    def test_invalid_concentration_risk_raises(self):
        with pytest.raises(ValueError, match="concentration_risk must be"):
            self._make(concentration_risk="CRITICAL")

    def test_invalid_liquidity_risk_raises(self):
        with pytest.raises(ValueError, match="liquidity_risk must be"):
            self._make(liquidity_risk="UNKNOWN")

    def test_invalid_regime_sensitivity_raises(self):
        with pytest.raises(ValueError, match="regime_sensitivity must be"):
            self._make(regime_sensitivity="NONE")


class TestReviewHorizon:
    def test_valid_review_horizon(self):
        rh = ReviewHorizon(
            review_date="2026-07-20T00:00:00Z",
            review_criteria="Evaluate if cumulative alpha exceeds 50bps",
        )
        assert rh.auto_expire is False

    def test_empty_review_criteria_raises(self):
        with pytest.raises(ValueError, match="review_criteria cannot be empty"):
            ReviewHorizon(review_date="2026-07-20", review_criteria="")

    def test_auto_expire_flag(self):
        rh = ReviewHorizon(
            review_date="2026-07-20T00:00:00Z",
            review_criteria="Evaluate performance",
            auto_expire=True,
        )
        assert rh.auto_expire is True
