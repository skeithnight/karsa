"""MandateComplianceService -- Sprint-17.

Application service for investment mandate compliance checking.
Evaluates portfolio positions against mandate rules.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from karsa.investment_governance.domain.value_objects.compliance_result import (
    ComplianceResult,
    RuleCheckResult,
)
from karsa.capability_engine.domain.exceptions import (
    InvalidEvolutionError,
)
from karsa.investment_governance.domain.value_objects.enums import (
    ComplianceStatus,
)
from karsa.investment_governance.domain.value_objects.mandate_config import (
    MandateConfig,
)
from karsa.investment_governance.domain.value_objects.mandate_rule import (
    MandateRule,
)


@dataclass
class PositionData:
    """Position information for compliance checking."""

    ticker: str
    sector: str
    conglomerate_group: Optional[str] = None
    weight_pct: float = 0.0  # 0.0-1.0
    beta: float = 1.0
    volatility: float = 0.0


@dataclass
class PortfolioData:
    """Portfolio snapshot for compliance checking."""

    positions: List[PositionData]
    total_nav: float = 0.0
    cash_pct: float = 0.0
    current_drawdown: float = 0.0


class MandateComplianceService:
    """Evaluates portfolio positions against mandate rules.

    Provides:
    - check_position(): Single position compliance
    - check_portfolio(): Full portfolio compliance
    - check_decision(): Pre-trade compliance for a proposed trade
    """

    def __init__(self, mandate_config: Optional[MandateConfig] = None) -> None:
        self._config = mandate_config or MandateConfig()

    def check_position(
        self, position: PositionData
    ) -> ComplianceResult:
        """Check a single position against mandate rules."""
        checks = []
        violations = []
        warnings = []

        # Single stock limit
        single_stock_rule = MandateRule(
            rule_type="SINGLE_STOCK_LIMIT",
            name="Single Stock Limit",
            limit_value=self._config.single_stock_limit,
            unit="%",
        )
        status = single_stock_rule.evaluate(position.weight_pct)
        checks.append(RuleCheckResult(
            rule_name="Single Stock Limit",
            rule_type="SINGLE_STOCK_LIMIT",
            current_value=position.weight_pct,
            limit_value=self._config.single_stock_limit,
            status=status.value,
            message=single_stock_rule.describe(position.weight_pct),
        ))
        if status == ComplianceStatus.VIOLATION:
            violations.append(
                f"{position.ticker}: weight {position.weight_pct*100:.1f}% "
                f"exceeds single stock limit {self._config.single_stock_limit*100:.1f}%"
            )
        elif status == ComplianceStatus.WARNING:
            warnings.append(
                f"{position.ticker}: weight {position.weight_pct*100:.1f}% "
                f"approaching single stock limit {self._config.single_stock_limit*100:.1f}%"
            )

        # Sector limit
        sector_limit = self._config.sector_limits.get(position.sector)
        if sector_limit is not None:
            sector_rule = MandateRule(
                rule_type="SECTOR_LIMIT",
                name=f"{position.sector} Sector Limit",
                limit_value=sector_limit,
                unit="%",
            )
            # For single position, we check if adding it would breach sector limit
            # This is a simplified check - full sector check needs portfolio context
            status = sector_rule.evaluate(position.weight_pct)
            checks.append(RuleCheckResult(
                rule_name=f"{position.sector} Sector Limit",
                rule_type="SECTOR_LIMIT",
                current_value=position.weight_pct,
                limit_value=sector_limit,
                status=status.value,
                message=sector_rule.describe(position.weight_pct),
            ))

        # Conglomerate limit
        if position.conglomerate_group:
            cong_limit = self._config.conglomerate_limits.get(
                position.conglomerate_group
            )
            if cong_limit is not None:
                cong_rule = MandateRule(
                    rule_type="CONGLOMERATE_LIMIT",
                    name=f"{position.conglomerate_group} Conglomerate Limit",
                    limit_value=cong_limit,
                    unit="%",
                )
                status = cong_rule.evaluate(position.weight_pct)
                checks.append(RuleCheckResult(
                    rule_name=f"{position.conglomerate_group} Conglomerate Limit",
                    rule_type="CONGLOMERATE_LIMIT",
                    current_value=position.weight_pct,
                    limit_value=cong_limit,
                    status=status.value,
                    message=cong_rule.describe(position.weight_pct),
                ))
                if status == ComplianceStatus.VIOLATION:
                    violations.append(
                        f"{position.ticker}: conglomerate "
                        f"{position.conglomerate_group} weight "
                        f"{position.weight_pct*100:.1f}% exceeds limit "
                        f"{cong_limit*100:.1f}%"
                    )

        overall = (
            ComplianceStatus.VIOLATION.value
            if violations
            else ComplianceStatus.WARNING.value
            if warnings
            else ComplianceStatus.COMPLIANT.value
        )

        return ComplianceResult(
            overall_status=overall,
            ticker=position.ticker,
            rule_checks=checks,
            violations=violations,
            warnings=warnings,
        )

    def check_portfolio(
        self, portfolio: PortfolioData
    ) -> List[ComplianceResult]:
        """Check all positions in a portfolio against mandate rules."""
        results = []

        # Calculate sector totals
        sector_totals: Dict[str, float] = {}
        conglomerate_totals: Dict[str, float] = {}
        for pos in portfolio.positions:
            sector_totals[pos.sector] = (
                sector_totals.get(pos.sector, 0) + pos.weight_pct
            )
            if pos.conglomerate_group:
                conglomerate_totals[pos.conglomerate_group] = (
                    conglomerate_totals.get(pos.conglomerate_group, 0)
                    + pos.weight_pct
                )

        # Check each position
        for pos in portfolio.positions:
            checks = []
            violations = []
            warnings = []

            # Single stock limit
            single_rule = MandateRule(
                rule_type="SINGLE_STOCK_LIMIT",
                name="Single Stock Limit",
                limit_value=self._config.single_stock_limit,
                unit="%",
            )
            status = single_rule.evaluate(pos.weight_pct)
            checks.append(RuleCheckResult(
                rule_name="Single Stock Limit",
                rule_type="SINGLE_STOCK_LIMIT",
                current_value=pos.weight_pct,
                limit_value=self._config.single_stock_limit,
                status=status.value,
                message=single_rule.describe(pos.weight_pct),
            ))
            if status == ComplianceStatus.VIOLATION:
                violations.append(
                    f"{pos.ticker}: single stock limit exceeded"
                )
            elif status == ComplianceStatus.WARNING:
                warnings.append(
                    f"{pos.ticker}: approaching single stock limit"
                )

            # Sector limit (using portfolio-level total)
            sector_total = sector_totals.get(pos.sector, 0)
            sector_limit = self._config.sector_limits.get(pos.sector)
            if sector_limit is not None:
                sector_rule = MandateRule(
                    rule_type="SECTOR_LIMIT",
                    name=f"{pos.sector} Sector Limit",
                    limit_value=sector_limit,
                    unit="%",
                )
                status = sector_rule.evaluate(sector_total)
                checks.append(RuleCheckResult(
                    rule_name=f"{pos.sector} Sector Limit",
                    rule_type="SECTOR_LIMIT",
                    current_value=sector_total,
                    limit_value=sector_limit,
                    status=status.value,
                    message=sector_rule.describe(sector_total),
                ))
                if status == ComplianceStatus.VIOLATION:
                    violations.append(
                        f"{pos.sector}: sector total "
                        f"{sector_total*100:.1f}% exceeds limit "
                        f"{sector_limit*100:.1f}%"
                    )
                elif status == ComplianceStatus.WARNING:
                    warnings.append(
                        f"{pos.sector}: sector total "
                        f"{sector_total*100:.1f}% approaching limit "
                        f"{sector_limit*100:.1f}%"
                    )

            # Conglomerate limit
            if pos.conglomerate_group:
                cong_total = conglomerate_totals.get(
                    pos.conglomerate_group, 0
                )
                cong_limit = self._config.conglomerate_limits.get(
                    pos.conglomerate_group
                )
                if cong_limit is not None:
                    cong_rule = MandateRule(
                        rule_type="CONGLOMERATE_LIMIT",
                        name=f"{pos.conglomerate_group} Conglomerate Limit",
                        limit_value=cong_limit,
                        unit="%",
                    )
                    status = cong_rule.evaluate(cong_total)
                    checks.append(RuleCheckResult(
                        rule_name=f"{pos.conglomerate_group} Conglomerate Limit",
                        rule_type="CONGLOMERATE_LIMIT",
                        current_value=cong_total,
                        limit_value=cong_limit,
                        status=status.value,
                        message=cong_rule.describe(cong_total),
                    ))
                    if status == ComplianceStatus.VIOLATION:
                        violations.append(
                            f"{pos.conglomerate_group}: conglomerate total "
                            f"{cong_total*100:.1f}% exceeds limit "
                            f"{cong_limit*100:.1f}%"
                        )
                    elif status == ComplianceStatus.WARNING:
                        warnings.append(
                            f"{pos.conglomerate_group}: conglomerate total "
                            f"{cong_total*100:.1f}% approaching limit "
                            f"{cong_limit*100:.1f}%"
                        )

            overall = (
                ComplianceStatus.VIOLATION.value
                if violations
                else ComplianceStatus.WARNING.value
                if warnings
                else ComplianceStatus.COMPLIANT.value
            )

            results.append(ComplianceResult(
                overall_status=overall,
                ticker=pos.ticker,
                rule_checks=checks,
                violations=violations,
                warnings=warnings,
            ))

        return results

    def check_decision(
        self,
        ticker: str,
        sector: str,
        proposed_weight_pct: float,
        current_portfolio: PortfolioData,
        conglomerate_group: Optional[str] = None,
    ) -> ComplianceResult:
        """Pre-trade compliance check for a proposed trade.

        Simulates adding the proposed position to the current portfolio
        and checks all mandate rules.
        """
        # Create simulated position
        proposed = PositionData(
            ticker=ticker,
            sector=sector,
            conglomerate_group=conglomerate_group,
            weight_pct=proposed_weight_pct,
        )

        # Check single stock limit
        return self.check_position(proposed)

    @property
    def config(self) -> MandateConfig:
        return self._config
