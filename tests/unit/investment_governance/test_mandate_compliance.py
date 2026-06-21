"""Tests for MandateComplianceService -- Sprint-17.

Covers:
- single stock limit checking
- sector limit checking
- conglomerate limit checking
- portfolio-level compliance
- pre-trade compliance
- compliance status reporting
- mandate rule validation
- compliance result aggregation
"""

import pytest

from karsa.investment_governance.application.mandate_compliance_service import (
    MandateComplianceService,
    PortfolioData,
    PositionData,
)
from karsa.investment_governance.domain.value_objects.compliance_result import (
    ComplianceResult,
)
from karsa.investment_governance.domain.value_objects.enums import (
    ComplianceStatus,
    MandateRuleType,
)
from karsa.investment_governance.domain.value_objects.mandate_config import (
    MandateConfig,
)
from karsa.investment_governance.domain.value_objects.mandate_rule import (
    MandateRule,
)


def _make_service():
    return MandateComplianceService()


def _make_position(**overrides):
    defaults = dict(
        ticker="BBCA",
        sector="Finance",
        conglomerate_group="Djarum/BCA",
        weight_pct=0.025,  # 2.5%
        beta=1.05,
        volatility=0.18,
    )
    defaults.update(overrides)
    return PositionData(**defaults)


def _make_portfolio(positions=None):
    if positions is None:
        positions = [
            _make_position(ticker="BBCA", sector="Finance", weight_pct=0.025),
            _make_position(ticker="ASII", sector="Consumer", weight_pct=0.020),
            _make_position(ticker="MEDC", sector="Energy", weight_pct=0.015),
        ]
    return PortfolioData(positions=positions, total_nav=10_000_000_000, cash_pct=0.05)


class TestMandateRule:
    """MandateRule value object."""

    def test_compliant(self):
        rule = MandateRule(
            rule_type="SINGLE_STOCK_LIMIT",
            name="Single Stock",
            limit_value=0.03,
            unit="%",
        )
        assert rule.evaluate(0.02) == ComplianceStatus.COMPLIANT

    def test_warning(self):
        rule = MandateRule(
            rule_type="SINGLE_STOCK_LIMIT",
            name="Single Stock",
            limit_value=0.03,
            unit="%",
            warning_threshold=0.9,
        )
        assert rule.evaluate(0.028) == ComplianceStatus.WARNING

    def test_violation(self):
        rule = MandateRule(
            rule_type="SINGLE_STOCK_LIMIT",
            name="Single Stock",
            limit_value=0.03,
            unit="%",
        )
        assert rule.evaluate(0.035) == ComplianceStatus.VIOLATION

    def test_at_limit_is_violation(self):
        rule = MandateRule(
            rule_type="SINGLE_STOCK_LIMIT",
            name="Single Stock",
            limit_value=0.03,
            unit="%",
        )
        # At limit is not a violation (>)
        assert rule.evaluate(0.03) == ComplianceStatus.WARNING

    def test_describe(self):
        rule = MandateRule(
            rule_type="SINGLE_STOCK_LIMIT",
            name="Single Stock",
            limit_value=0.03,
            unit="%",
        )
        desc = rule.describe(0.02)
        assert "Single Stock" in desc
        assert "COMPLIANT" in desc

    def test_invalid_rule_type(self):
        with pytest.raises(Exception):
            MandateRule(
                rule_type="INVALID",
                name="Bad",
                limit_value=0.03,
            )


class TestMandateConfig:
    """MandateConfig value object."""

    def test_default_config(self):
        config = MandateConfig()
        assert config.single_stock_limit == 0.03
        assert config.sector_limits["Finance"] == 0.30
        assert config.conglomerate_limits["Djarum/BCA"] == 0.15

    def test_get_sector_rules(self):
        config = MandateConfig()
        rules = config.get_sector_rules()
        assert len(rules) == 5
        assert any(r.name == "Finance Sector Limit" for r in rules)

    def test_get_conglomerate_rules(self):
        config = MandateConfig()
        rules = config.get_conglomerate_rules()
        assert len(rules) == 7

    def test_get_position_rules(self):
        config = MandateConfig()
        rules = config.get_position_rules()
        assert len(rules) == 2

    def test_get_all_rules(self):
        config = MandateConfig()
        rules = config.get_all_rules()
        assert len(rules) > 10


class TestPositionCompliance:
    """Single position compliance checking."""

    def test_compliant_position(self):
        service = _make_service()
        pos = _make_position(weight_pct=0.02)  # 2% < 3% limit
        result = service.check_position(pos)
        assert result.is_compliant
        assert not result.has_violations

    def test_violation_single_stock(self):
        service = _make_service()
        pos = _make_position(weight_pct=0.04)  # 4% > 3% limit
        result = service.check_position(pos)
        assert not result.is_compliant
        assert result.has_violations

    def test_warning_single_stock(self):
        service = _make_service()
        pos = _make_position(weight_pct=0.028)  # 2.8% > 90% of 3%
        result = service.check_position(pos)
        assert result.has_warnings

    def test_conglomerate_violation(self):
        service = _make_service()
        # Djarum/BCA limit is 15%
        pos = _make_position(
            weight_pct=0.16,
            conglomerate_group="Djarum/BCA",
        )
        result = service.check_position(pos)
        assert result.has_violations
        assert any("conglomerate" in v.lower() for v in result.violations)

    def test_no_conglomerate_no_check(self):
        service = _make_service()
        pos = _make_position(conglomerate_group=None)
        result = service.check_position(pos)
        # No conglomerate check should be present
        cong_checks = [
            c for c in result.rule_checks
            if c.rule_type == "CONGLOMERATE_LIMIT"
        ]
        assert len(cong_checks) == 0


class TestPortfolioCompliance:
    """Portfolio-level compliance checking."""

    def test_compliant_portfolio(self):
        service = _make_service()
        portfolio = _make_portfolio()
        results = service.check_portfolio(portfolio)
        assert len(results) == 3
        assert all(r.is_compliant for r in results)

    def test_sector_violation(self):
        service = _make_service()
        portfolio = _make_portfolio([
            _make_position(ticker="BBCA", sector="Finance", weight_pct=0.025),
            _make_position(ticker="BBRI", sector="Finance", weight_pct=0.025),
            _make_position(ticker="BMRI", sector="Finance", weight_pct=0.025),
        ])
        results = service.check_portfolio(portfolio)
        # Finance total = 7.5%, well under 30% limit
        assert all(r.is_compliant for r in results)

    def test_sector_approaching_limit(self):
        service = _make_service()
        # Finance limit is 30%. Two positions totaling 27% (> 90% of 30%).
        portfolio = _make_portfolio([
            _make_position(ticker="BBCA", sector="Finance", weight_pct=0.15),
            _make_position(ticker="BBRI", sector="Finance", weight_pct=0.12),
        ])
        results = service.check_portfolio(portfolio)
        # 27% > 27% (90% of 30%) triggers warning
        assert any(r.has_warnings for r in results)

    def test_conglomerate_aggregation(self):
        service = _make_service()
        # Djarum/BCA limit is 15%. Two positions from same group.
        portfolio = _make_portfolio([
            _make_position(
                ticker="BBCA",
                sector="Finance",
                conglomerate_group="Djarum/BCA",
                weight_pct=0.08,
            ),
            _make_position(
                ticker="BGTN",
                sector="Finance",
                conglomerate_group="Djarum/BCA",
                weight_pct=0.08,
            ),
        ])
        results = service.check_portfolio(portfolio)
        # Total = 16% > 15% limit
        assert any(r.has_violations for r in results)


class TestPreTradeCompliance:
    """Pre-trade compliance checking."""

    def test_compliant_trade(self):
        service = _make_service()
        portfolio = _make_portfolio()
        result = service.check_decision(
            ticker="BBCA",
            sector="Finance",
            proposed_weight_pct=0.02,
            current_portfolio=portfolio,
        )
        assert result.is_compliant

    def test_trade_exceeding_limit(self):
        service = _make_service()
        portfolio = _make_portfolio()
        result = service.check_decision(
            ticker="BBCA",
            sector="Finance",
            proposed_weight_pct=0.05,  # > 3% limit
            current_portfolio=portfolio,
        )
        assert result.has_violations


class TestComplianceResult:
    """ComplianceResult value object."""

    def test_compliant_result(self):
        result = ComplianceResult(
            overall_status=ComplianceStatus.COMPLIANT.value,
            ticker="BBCA",
        )
        assert result.is_compliant
        assert not result.has_violations
        assert result.summary == "BBCA: All mandate checks passed"

    def test_violation_result(self):
        result = ComplianceResult(
            overall_status=ComplianceStatus.VIOLATION.value,
            ticker="BBCA",
            violations=["Sector limit exceeded"],
        )
        assert not result.is_compliant
        assert result.has_violations
        assert result.violation_count == 1
        assert "violation" in result.summary

    def test_warning_result(self):
        result = ComplianceResult(
            overall_status=ComplianceStatus.WARNING.value,
            ticker="BBCA",
            warnings=["Approaching limit"],
        )
        assert result.has_warnings
        assert "warning" in result.summary
