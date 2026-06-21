"""MandateConfig value object -- Sprint-17.

Defines the complete investment mandate configuration.
Loaded from docs/investment_context/MANDATE.md and RISK_POLICY.md.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from karsa.investment_governance.domain.value_objects.mandate_rule import (
    MandateRule,
)
from karsa.investment_governance.domain.value_objects.enums import MandateRuleType


@dataclass(frozen=True)
class MandateConfig:
    """Complete investment mandate configuration.

    Defines all rules that an investment decision must pass.
    """

    fund_name: str = "KARSA Growth Fund"
    base_currency: str = "IDR"
    benchmark: str = "IHSG"

    # Position limits
    single_stock_limit: float = 0.03  # 3%
    top5_concentration_limit: float = 0.60  # 60%
    top10_concentration_limit: float = 0.80  # 80%
    cash_minimum: float = 0.02  # 2%

    # Sector limits (sector_name -> max_allocation)
    sector_limits: Dict[str, float] = field(default_factory=lambda: {
        "Finance": 0.30,
        "Energy": 0.20,
        "Consumer": 0.25,
        "Technology": 0.15,
        "Infrastructure": 0.15,
    })

    # Conglomerate limits (group_name -> max_exposure)
    conglomerate_limits: Dict[str, float] = field(default_factory=lambda: {
        "Djarum/BCA": 0.15,
        "Astra": 0.12,
        "Sinar Mas": 0.10,
        "Salim": 0.08,
        "Lippo": 0.05,
        "Prajogo": 0.08,
        "Bakrie": 0.05,
    })

    # Risk limits
    max_volatility: float = 0.22  # 22% annual
    max_drawdown: float = 0.15  # 15%
    beta_min: float = 0.8
    beta_max: float = 1.3
    max_correlation: float = 0.7

    def get_sector_rules(self) -> List[MandateRule]:
        """Generate mandate rules for sector limits."""
        rules = []
        for sector, limit in self.sector_limits.items():
            rules.append(MandateRule(
                rule_type=MandateRuleType.SECTOR_LIMIT.value,
                name=f"{sector} Sector Limit",
                limit_value=limit,
                unit="%",
                target_value=limit * 0.8,  # target = 80% of limit
            ))
        return rules

    def get_conglomerate_rules(self) -> List[MandateRule]:
        """Generate mandate rules for conglomerate limits."""
        rules = []
        for group, limit in self.conglomerate_limits.items():
            rules.append(MandateRule(
                rule_type=MandateRuleType.CONGLOMERATE_LIMIT.value,
                name=f"{group} Conglomerate Limit",
                limit_value=limit,
                unit="%",
            ))
        return rules

    def get_position_rules(self) -> List[MandateRule]:
        """Generate mandate rules for position limits."""
        return [
            MandateRule(
                rule_type=MandateRuleType.SINGLE_STOCK_LIMIT.value,
                name="Single Stock Limit",
                limit_value=self.single_stock_limit,
                unit="%",
            ),
            MandateRule(
                rule_type=MandateRuleType.CONCENTRATION_LIMIT.value,
                name="Top 5 Concentration Limit",
                limit_value=self.top5_concentration_limit,
                unit="%",
            ),
        ]

    def get_risk_rules(self) -> List[MandateRule]:
        """Generate mandate rules for risk limits."""
        return [
            MandateRule(
                rule_type=MandateRuleType.VOLATILITY_LIMIT.value,
                name="Annual Volatility Limit",
                limit_value=self.max_volatility,
                unit="%",
            ),
            MandateRule(
                rule_type=MandateRuleType.DRAWDOWN_LIMIT.value,
                name="Max Drawdown Limit",
                limit_value=self.max_drawdown,
                unit="%",
            ),
        ]

    def get_all_rules(self) -> List[MandateRule]:
        """Generate all mandate rules."""
        return (
            self.get_position_rules()
            + self.get_sector_rules()
            + self.get_conglomerate_rules()
            + self.get_risk_rules()
        )
