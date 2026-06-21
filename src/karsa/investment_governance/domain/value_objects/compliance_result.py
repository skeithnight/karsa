"""ComplianceResult value object -- Sprint-17."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from karsa.investment_governance.domain.value_objects.enums import ComplianceStatus


@dataclass(frozen=True)
class RuleCheckResult:
    """Result of a single rule check."""

    rule_name: str
    rule_type: str
    current_value: float
    limit_value: float
    status: str  # ComplianceStatus value
    message: str


@dataclass(frozen=True)
class ComplianceResult:
    """Aggregate result of a mandate compliance check."""

    overall_status: str  # ComplianceStatus value
    ticker: str
    rule_checks: List[RuleCheckResult] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return self.overall_status == ComplianceStatus.COMPLIANT.value

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def summary(self) -> str:
        if self.is_compliant:
            return f"{self.ticker}: All mandate checks passed"
        parts = []
        if self.violations:
            parts.append(f"{len(self.violations)} violation(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return f"{self.ticker}: {', '.join(parts)}"
