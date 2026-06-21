"""Tests for InvestmentDecisionProjection -- Sprint-13. ADR-140.

Covers:
- DTO validation
- field defaults
- frozen enforcement
- no internal field leakage
"""

import pytest
from datetime import datetime

from karsa.investment_workflow.projections.investment_decision_projection import (
    InvestmentDecisionProjection,
)


class TestDecisionProjection:
    """InvestmentDecisionProjection DTO validation."""

    def test_valid_projection(self):
        p = InvestmentDecisionProjection(
            decision_id="d-001",
            capability_family_id="f-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            state="PROPOSED",
        )
        assert p.decision_id == "d-001"
        assert p.ticker == "BBCA"

    def test_frozen(self):
        p = InvestmentDecisionProjection(
            decision_id="d-001",
            capability_family_id="f-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            state="PROPOSED",
        )
        with pytest.raises(AttributeError):
            p.ticker = "ASII"

    def test_missing_decision_id(self):
        with pytest.raises(ValueError, match="decision_id"):
            InvestmentDecisionProjection(
                decision_id="",
                capability_family_id="f-001",
                ticker="BBCA",
                decision_date="2026-06-21",
                state="PROPOSED",
            )

    def test_missing_ticker(self):
        with pytest.raises(ValueError, match="ticker"):
            InvestmentDecisionProjection(
                decision_id="d-001",
                capability_family_id="f-001",
                ticker="",
                decision_date="2026-06-21",
                state="PROPOSED",
            )

    def test_defaults(self):
        p = InvestmentDecisionProjection(
            decision_id="d-001",
            capability_family_id="f-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            state="PROPOSED",
        )
        assert p.analyst_count == 0
        assert p.debate_count == 0
        assert p.has_memo is False
        assert p.analyst_scores == {}
        assert p.conviction_level is None

    def test_full_projection(self):
        now = datetime.utcnow()
        p = InvestmentDecisionProjection(
            decision_id="d-001",
            capability_family_id="f-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            state="APPROVED",
            analyst_count=5,
            analyst_scores={
                "FUNDAMENTAL": 8.0,
                "TECHNICAL": 7.0,
                "SENTIMENT": 6.0,
                "RISK": 7.5,
                "MARKET": 6.5,
            },
            debate_count=2,
            latest_bull_conviction="STRONG",
            latest_bear_conviction="WEAK",
            has_memo=True,
            memo_decision="BUY",
            conviction_level="STRONG",
            conviction_score=7.8,
            entry_price="8500",
            exit_target="9200",
            stop_loss="8200",
            position_size_pct=2.5,
            thesis_summary="Strong dividend yield and growth",
            proposed_by="test-user",
            created_at=now,
            updated_at=now,
        )
        assert p.analyst_count == 5
        assert p.analyst_scores["FUNDAMENTAL"] == 8.0
        assert p.has_memo is True
        assert p.memo_decision == "BUY"
        assert p.conviction_level == "STRONG"

    def test_no_internal_fields(self):
        """Projection must not expose domain internals."""
        p = InvestmentDecisionProjection(
            decision_id="d-001",
            capability_family_id="f-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            state="PROPOSED",
        )
        data = p.__dict__
        # No aggregate_version, no internal repository fields
        assert "aggregate_version" not in data
        assert "_store" not in data
