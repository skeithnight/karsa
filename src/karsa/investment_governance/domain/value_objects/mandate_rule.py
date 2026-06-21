"""MandateRule value object -- Sprint-17."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from karsa.investment_governance.domain.exceptions import InvalidMandateError
from karsa.investment_governance.domain.value_objects.enums import (
    ComplianceStatus,
    MandateRuleType,
)


@dataclass(frozen=True)
class MandateRule:
    """A single mandate rule with limit and current value evaluation.

    Examples:
    - Sector limit: Finance <= 30%
    - Concentration: Top 5 <= 60%
    - Single stock: <= 3%
    - Conglomerate: Prajogo group <= 8%
    """

    rule_type: str  # MandateRuleType value
    name: str  # Human-readable name
    limit_value: float  # Maximum allowed value
    unit: str = "%"  # %, ratio, etc.
    warning_threshold: float = 0.9  # 90% of limit triggers warning
    target_value: Optional[float] = None  # Target allocation
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        valid_types = {e.value for e in MandateRuleType}
        if self.rule_type not in valid_types:
            raise InvalidMandateError(
                f"rule_type must be one of {valid_types}"
            )
        if self.limit_value < 0:
            raise InvalidMandateError("limit_value must be >= 0")

    def evaluate(self, current_value: float) -> ComplianceStatus:
        """Evaluate current value against this rule."""
        if current_value > self.limit_value:
            return ComplianceStatus.VIOLATION
        elif current_value >= self.limit_value * self.warning_threshold:
            return ComplianceStatus.WARNING
        return ComplianceStatus.COMPLIANT

    @property
    def utilization_pct(self) -> float:
        """Return limit as percentage for display."""
        return self.limit_value * 100 if self.unit == "%" else self.limit_value

    def describe(self, current_value: float) -> str:
        """Human-readable compliance description."""
        status = self.evaluate(current_value)
        current_display = (
            f"{current_value * 100:.1f}%"
            if self.unit == "%"
            else str(current_value)
        )
        limit_display = (
            f"{self.limit_value * 100:.1f}%"
            if self.unit == "%"
            else str(self.limit_value)
        )
        return f"{self.name}: {current_display} / {limit_display} [{status.value}]"
