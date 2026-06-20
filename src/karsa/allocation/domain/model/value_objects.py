from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass(frozen=True)
class RiskBudget:
    max_volatility: float
    max_drawdown: float
    max_exposure: float

    def __post_init__(self):
        if self.max_volatility < 0:
            raise ValueError("max_volatility cannot be negative.")
        if self.max_drawdown < 0:
            raise ValueError("max_drawdown cannot be negative.")
        if self.max_exposure < 0:
            raise ValueError("max_exposure cannot be negative.")


@dataclass(frozen=True)
class ProposedWeight:
    worker_urn: str
    proposed_weight: float
    ranking_score: float
    eligibility_status: str
    rationale: str
    risk_budget: RiskBudget

    def __post_init__(self):
        if not self.worker_urn or not self.worker_urn.strip():
            raise ValueError("worker_urn cannot be empty.")
        if self.proposed_weight < 0.0 or self.proposed_weight > 1.0:
            raise ValueError("proposed_weight must be between 0.0 and 1.0.")
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale cannot be empty.")
        if self.eligibility_status not in ("ALLOCATABLE", "BLOCKED", "LIMITED"):
            raise ValueError("eligibility_status must be ALLOCATABLE, BLOCKED, or LIMITED.")


@dataclass(frozen=True)
class PolicySnapshot:
    policy_id: str
    policy_version: int
    policy_hash: str
    active_rules: List[str]

    def __post_init__(self):
        if not self.policy_id or not self.policy_id.strip():
            raise ValueError("policy_id cannot be empty.")
        if not self.policy_hash or not self.policy_hash.strip():
            raise ValueError("policy_hash cannot be empty.")


@dataclass(frozen=True)
class PortfolioContext:
    current_gross_exposure: float
    current_net_exposure: float
    current_cash_ratio: float
    current_concentration: float
    projected_gross_exposure: float
    projected_net_exposure: float
    projected_cash_ratio: float
    projected_concentration: float
    cash_allocation_pct: float
    concentration_impact: str
    alternatives_considered: List[str]

    def __post_init__(self):
        if self.concentration_impact not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError("concentration_impact must be LOW, MEDIUM, or HIGH.")
        if self.cash_allocation_pct < 0.0 or self.cash_allocation_pct > 1.0:
            raise ValueError("cash_allocation_pct must be between 0.0 and 1.0.")


@dataclass(frozen=True)
class StructuredAssumption:
    assumption_id: str
    statement: str
    validation_criteria: str
    source_urn: Optional[str] = None

    def __post_init__(self):
        if not self.assumption_id or not self.assumption_id.strip():
            raise ValueError("assumption_id cannot be empty.")
        if not self.statement or not self.statement.strip():
            raise ValueError("statement cannot be empty.")


@dataclass(frozen=True)
class ExpectedOutcome:
    expected_return_bps: float
    expected_drawdown_pct: float
    expected_sharpe_ratio: float
    expected_horizon_days: int
    confidence_level: float
    benchmark_urn: Optional[str]
    regime_at_decision: Optional[str]
    key_assumptions: List[StructuredAssumption]
    attribution_expectations: Dict[str, float]

    def __post_init__(self):
        if self.expected_horizon_days <= 0:
            raise ValueError("expected_horizon_days must be positive.")
        if self.confidence_level < 0.0 or self.confidence_level > 1.0:
            raise ValueError("confidence_level must be between 0.0 and 1.0.")


@dataclass(frozen=True)
class RiskAssessment:
    worst_case_loss_pct: float
    concentration_risk: str
    liquidity_risk: str
    regime_sensitivity: str

    def __post_init__(self):
        for field_name, value in [("concentration_risk", self.concentration_risk),
                                   ("liquidity_risk", self.liquidity_risk),
                                   ("regime_sensitivity", self.regime_sensitivity)]:
            if value not in ("LOW", "MEDIUM", "HIGH"):
                raise ValueError(f"{field_name} must be LOW, MEDIUM, or HIGH.")


@dataclass(frozen=True)
class ReviewHorizon:
    review_date: str  # ISO datetime string
    review_criteria: str
    auto_expire: bool = False

    def __post_init__(self):
        if not self.review_criteria or not self.review_criteria.strip():
            raise ValueError("review_criteria cannot be empty.")
