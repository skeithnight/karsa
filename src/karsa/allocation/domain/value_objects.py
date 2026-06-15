import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class PortfolioHorizon:
    horizon_id: str
    horizon_start: datetime
    horizon_end: datetime

    def __post_init__(self):
        if not self.horizon_id or not isinstance(self.horizon_id, str):
            raise ValueError("horizon_id must be a non-empty string")
        if not isinstance(self.horizon_start, datetime) or not isinstance(self.horizon_end, datetime):
            raise ValueError("horizon_start and horizon_end must be datetime objects")
        if self.horizon_start >= self.horizon_end:
            raise ValueError("horizon_start must be strictly before horizon_end")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horizon_id": self.horizon_id,
            "horizon_start": self.horizon_start.isoformat(),
            "horizon_end": self.horizon_end.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PortfolioHorizon':
        return cls(
            horizon_id=data["horizon_id"],
            horizon_start=datetime.fromisoformat(data["horizon_start"]),
            horizon_end=datetime.fromisoformat(data["horizon_end"])
        )


@dataclass(frozen=True)
class AllocationScore:
    raw_score: float
    performance_score: float
    attribution_score: float
    review_penalty_multiplier: float

    def __post_init__(self):
        # Allow checking float type and values
        for field_name in ("raw_score", "performance_score", "attribution_score", "review_penalty_multiplier"):
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)):
                raise ValueError(f"{field_name} must be a numeric value")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_score": float(self.raw_score),
            "performance_score": float(self.performance_score),
            "attribution_score": float(self.attribution_score),
            "review_penalty_multiplier": float(self.review_penalty_multiplier)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationScore':
        return cls(
            raw_score=float(data["raw_score"]),
            performance_score=float(data["performance_score"]),
            attribution_score=float(data["attribution_score"]),
            review_penalty_multiplier=float(data["review_penalty_multiplier"])
        )


@dataclass(frozen=True)
class RiskBudgetAssignment:
    tracking_error_pct: float
    max_drawdown_limit: float

    def __post_init__(self):
        for field_name in ("tracking_error_pct", "max_drawdown_limit"):
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)):
                raise ValueError(f"{field_name} must be a numeric value")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tracking_error_pct": float(self.tracking_error_pct),
            "max_drawdown_limit": float(self.max_drawdown_limit)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskBudgetAssignment':
        return cls(
            tracking_error_pct=float(data["tracking_error_pct"]),
            max_drawdown_limit=float(data["max_drawdown_limit"])
        )


@dataclass(frozen=True)
class AllocationRecommendation:
    recommended_weight: float
    recommended_capital_percentage: float
    risk_budget: RiskBudgetAssignment

    def __post_init__(self):
        if not isinstance(self.recommended_weight, (int, float)):
            raise ValueError("recommended_weight must be a numeric value")
        if not isinstance(self.recommended_capital_percentage, (int, float)):
            raise ValueError("recommended_capital_percentage must be a numeric value")
        if not isinstance(self.risk_budget, RiskBudgetAssignment):
            raise ValueError("risk_budget must be a RiskBudgetAssignment object")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_weight": float(self.recommended_weight),
            "recommended_capital_percentage": float(self.recommended_capital_percentage),
            "risk_budget": self.risk_budget.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationRecommendation':
        return cls(
            recommended_weight=float(data["recommended_weight"]),
            recommended_capital_percentage=float(data["recommended_capital_percentage"]),
            risk_budget=RiskBudgetAssignment.from_dict(data["risk_budget"])
        )


@dataclass(frozen=True)
class AllocationMethodologyManifest:
    allocation_methodology_urn: str
    allocation_policy_hash: str
    allocation_strategy_version: str

    def __post_init__(self):
        for field_name in ("allocation_methodology_urn", "allocation_policy_hash", "allocation_strategy_version"):
            val = getattr(self, field_name)
            if not val or not isinstance(val, str):
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_methodology_urn": self.allocation_methodology_urn,
            "allocation_policy_hash": self.allocation_policy_hash,
            "allocation_strategy_version": self.allocation_strategy_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AllocationMethodologyManifest':
        return cls(
            allocation_methodology_urn=data["allocation_methodology_urn"],
            allocation_policy_hash=data["allocation_policy_hash"],
            allocation_strategy_version=data["allocation_strategy_version"]
        )

    def compute_hash(self) -> str:
        payload = self.to_dict()
        canonical_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
