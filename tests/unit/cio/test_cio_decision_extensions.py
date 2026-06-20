"""Tests for CIODecisionAggregate Sprint-06 extensions — Wave-2."""
import pytest
from datetime import datetime

from karsa.cio.models import CIODecisionAggregate
from karsa.cio.value_objects import CommitteeVote, OverrideReason
from karsa.allocation.domain.model.value_objects import (
    ExpectedOutcome, RiskAssessment, ReviewHorizon, StructuredAssumption
)
from karsa.cio.exceptions import ImmutabilityViolationException


def _make_vote(approve=True):
    return CommitteeVote(
        voter_id="cio-1",
        vote_type="APPROVE" if approve else "REJECT",
        timestamp=datetime.utcnow(),
    )


def _make_expected_outcome():
    return ExpectedOutcome(
        expected_return_bps=50.0,
        expected_drawdown_pct=5.0,
        expected_sharpe_ratio=1.5,
        expected_horizon_days=30,
        confidence_level=0.7,
        benchmark_urn="urn:karsa:benchmark:composite",
        regime_at_decision="BULL",
        key_assumptions=[],
        attribution_expectations={"alpha": 0.7},
    )


def _make_risk_assessment():
    return RiskAssessment(
        worst_case_loss_pct=8.0,
        concentration_risk="LOW",
        liquidity_risk="LOW",
        regime_sensitivity="MEDIUM",
    )


def _make_review_horizon():
    return ReviewHorizon(
        review_date="2026-07-20T00:00:00Z",
        review_criteria="Evaluate if cumulative alpha exceeds 50bps",
    )


def _make_decision(**overrides):
    defaults = dict(
        decision_id="dec-1",
        calculation_id=None,
        governance_exception_id=None,
        decision_journal_ref="urn:karsa:journal:test-1",
        portfolio_snapshot_hash="hash123",
        action_type="APPROVE_ALLOCATION",
        target_node_type="WORKER",
        target_node_id="portfolio-main",
        decision_payload={"allocated_weights": {"w1": 0.5, "w2": 0.5}},
        cryptographic_signature="sig_base64",
        created_at=datetime.utcnow(),
        votes=[_make_vote()],
    )
    defaults.update(overrides)
    return CIODecisionAggregate(**defaults)


class TestCIODecisionWithProposalFields:
    def test_decision_without_proposal_fields(self):
        """Backward compatible: existing decisions still work."""
        decision = _make_decision()
        assert decision.proposal_id is None
        assert decision.expected_outcome is None
        assert decision.risk_assessment is None
        assert decision.review_horizon is None

    def test_decision_with_proposal_id(self):
        decision = _make_decision(proposal_id="urn:karsa:proposal:test-1")
        assert decision.proposal_id == "urn:karsa:proposal:test-1"

    def test_decision_with_all_proposal_fields(self):
        decision = _make_decision(
            proposal_id="urn:karsa:proposal:test-1",
            expected_outcome=_make_expected_outcome(),
            risk_assessment=_make_risk_assessment(),
            review_horizon=_make_review_horizon(),
        )
        assert decision.proposal_id == "urn:karsa:proposal:test-1"
        assert decision.expected_outcome.confidence_level == 0.7
        assert decision.risk_assessment.concentration_risk == "LOW"
        assert decision.review_horizon.auto_expire is False

    def test_decision_immutability_preserved(self):
        decision = _make_decision(proposal_id="urn:karsa:proposal:test-1")
        with pytest.raises(ImmutabilityViolationException):
            decision.proposal_id = "changed"

    def test_decision_expected_outcome_immutability(self):
        decision = _make_decision(
            expected_outcome=_make_expected_outcome(),
        )
        with pytest.raises(ImmutabilityViolationException):
            decision.expected_outcome = None

    def test_existing_validation_preserved(self):
        """Existing validation rules still apply."""
        with pytest.raises(ValueError, match="decision_id cannot be empty"):
            _make_decision(decision_id="")

    def test_override_requires_reason(self):
        """Existing override validation still applies."""
        with pytest.raises(ValueError, match="override decision must contain an override_reason"):
            _make_decision(
                action_type="OVERRIDE",
                override_reason=None,
            )

    def test_override_with_reason_succeeds(self):
        decision = _make_decision(
            action_type="OVERRIDE",
            override_reason=OverrideReason(justification="Risk adjustment"),
            proposal_id="urn:karsa:proposal:test-1",
        )
        assert decision.action_type == "OVERRIDE"
        assert decision.override_reason.justification == "Risk adjustment"
