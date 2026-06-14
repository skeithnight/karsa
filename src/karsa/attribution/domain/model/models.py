from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict
from karsa.shared.domain.aggregate import VersionedAggregate

@dataclass(frozen=True)
class CurrencyAmount:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            try:
                object.__setattr__(self, 'amount', Decimal(str(self.amount)))
            except Exception as e:
                raise ValueError(f"Amount must be a Decimal, got {type(self.amount)}: {e}")
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError("Currency must be a non-empty string")

    def add(self, other: 'CurrencyAmount') -> 'CurrencyAmount':
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")
        return CurrencyAmount(self.amount + other.amount, self.currency)

    def to_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_dict(cls, data: dict) -> 'CurrencyAmount':
        return cls(amount=Decimal(data["amount"]), currency=data.get("currency", "USD"))


@dataclass(frozen=True)
class CostCalculation:
    input_tokens: int
    output_tokens: int
    input_rate_per_1m: Decimal
    output_rate_per_1m: Decimal

    def __post_init__(self):
        if not isinstance(self.input_tokens, int) or self.input_tokens < 0:
            raise ValueError("input_tokens must be a non-negative integer")
        if not isinstance(self.output_tokens, int) or self.output_tokens < 0:
            raise ValueError("output_tokens must be a non-negative integer")
        if not isinstance(self.input_rate_per_1m, Decimal):
            try:
                object.__setattr__(self, 'input_rate_per_1m', Decimal(str(self.input_rate_per_1m)))
            except Exception as e:
                raise ValueError(f"input_rate_per_1m must be Decimal: {e}")
        if not isinstance(self.output_rate_per_1m, Decimal):
            try:
                object.__setattr__(self, 'output_rate_per_1m', Decimal(str(self.output_rate_per_1m)))
            except Exception as e:
                raise ValueError(f"output_rate_per_1m must be Decimal: {e}")

    def calculate_cost(self) -> CurrencyAmount:
        input_cost = Decimal(self.input_tokens) * self.input_rate_per_1m / Decimal("1000000")
        output_cost = Decimal(self.output_tokens) * self.output_rate_per_1m / Decimal("1000000")
        return CurrencyAmount(input_cost + output_cost, "USD")

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_rate_per_1m": str(self.input_rate_per_1m),
            "output_rate_per_1m": str(self.output_rate_per_1m)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CostCalculation':
        return cls(
            input_tokens=int(data["input_tokens"]),
            output_tokens=int(data["output_tokens"]),
            input_rate_per_1m=Decimal(data["input_rate_per_1m"]),
            output_rate_per_1m=Decimal(data["output_rate_per_1m"])
        )


class AttributionRecord(VersionedAggregate):
    def __init__(
        self,
        attribution_id: str,
        execution_id: str,
        trace_id: str,
        calculated_cost: CurrencyAmount,
        calculation_details: CostCalculation,
        research_run_id: Optional[str] = None,
        thesis_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        extended_dimensions: Optional[Dict[str, str]] = None,
        created_at: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.attribution_id = attribution_id
        self.execution_id = execution_id
        self.trace_id = trace_id
        self.calculated_cost = calculated_cost
        self.calculation_details = calculation_details
        self.research_run_id = research_run_id
        self.thesis_id = thesis_id
        self.worker_id = worker_id
        self.portfolio_id = portfolio_id
        self.strategy_id = strategy_id
        self.extended_dimensions = extended_dimensions or {}
        self.created_at = created_at or datetime.utcnow()
        
        self.validate()
        self._initialized = True

    def validate(self):
        if not self.attribution_id:
            raise ValueError("attribution_id is required")
        if not self.execution_id:
            raise ValueError("execution_id is required")
        if not self.trace_id:
            raise ValueError("trace_id is required")
        if not isinstance(self.calculated_cost, CurrencyAmount):
            raise ValueError("calculated_cost must be a CurrencyAmount")
        if not isinstance(self.calculation_details, CostCalculation):
            raise ValueError("calculation_details must be a CostCalculation")
        
        if self.extended_dimensions is not None:
            if not isinstance(self.extended_dimensions, dict):
                raise ValueError("extended_dimensions must be a dictionary")
            if len(self.extended_dimensions) > 20:
                raise ValueError("extended_dimensions cannot have more than 20 keys")
            for k, v in self.extended_dimensions.items():
                if not isinstance(k, str) or len(k) > 128:
                    raise ValueError("extended_dimensions key must be a string under 128 characters")
                if not isinstance(v, str) or len(v) > 128:
                    raise ValueError("extended_dimensions value must be a string under 128 characters")

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable AttributionRecord aggregate")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable AttributionRecord aggregate")
        super().__delattr__(name)

    def to_dict(self) -> dict:
        return {
            "attribution_id": self.attribution_id,
            "execution_id": self.execution_id,
            "trace_id": self.trace_id,
            "calculated_cost": self.calculated_cost.to_dict(),
            "calculation_details": self.calculation_details.to_dict(),
            "research_run_id": self.research_run_id,
            "thesis_id": self.thesis_id,
            "worker_id": self.worker_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "extended_dimensions": self.extended_dimensions,
            "created_at": self.created_at.isoformat(),
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AttributionRecord':
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        return cls(
            attribution_id=data["attribution_id"],
            execution_id=data["execution_id"],
            trace_id=data["trace_id"],
            calculated_cost=CurrencyAmount.from_dict(data["calculated_cost"]),
            calculation_details=CostCalculation.from_dict(data["calculation_details"]),
            research_run_id=data.get("research_run_id"),
            thesis_id=data.get("thesis_id"),
            worker_id=data.get("worker_id"),
            portfolio_id=data.get("portfolio_id"),
            strategy_id=data.get("strategy_id"),
            extended_dimensions=data.get("extended_dimensions"),
            created_at=created_at,
            aggregate_version=data.get("aggregate_version", 1)
        )


class AttributionAdjustment(VersionedAggregate):
    def __init__(
        self,
        adjustment_id: str,
        original_attribution_id: str,
        adjustment_amount: CurrencyAmount,
        adjustment_reason: str,
        adjustment_timestamp: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.adjustment_id = adjustment_id
        self.original_attribution_id = original_attribution_id
        self.adjustment_amount = adjustment_amount
        self.adjustment_reason = adjustment_reason
        self.adjustment_timestamp = adjustment_timestamp or datetime.utcnow()
        
        self.validate()
        self._initialized = True

    def validate(self):
        if not self.adjustment_id:
            raise ValueError("adjustment_id is required")
        if not self.original_attribution_id:
            raise ValueError("original_attribution_id is required")
        if not self.adjustment_reason or not isinstance(self.adjustment_reason, str):
            raise ValueError("adjustment_reason is required and must be a string")
        if not isinstance(self.adjustment_amount, CurrencyAmount):
            raise ValueError("adjustment_amount must be a CurrencyAmount")

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable AttributionAdjustment aggregate")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot modify immutable AttributionAdjustment aggregate")
        super().__delattr__(name)

    def to_dict(self) -> dict:
        return {
            "adjustment_id": self.adjustment_id,
            "original_attribution_id": self.original_attribution_id,
            "adjustment_amount": self.adjustment_amount.to_dict(),
            "adjustment_reason": self.adjustment_reason,
            "adjustment_timestamp": self.adjustment_timestamp.isoformat(),
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AttributionAdjustment':
        timestamp = datetime.fromisoformat(data["adjustment_timestamp"]) if isinstance(data["adjustment_timestamp"], str) else data["adjustment_timestamp"]
        return cls(
            adjustment_id=data["adjustment_id"],
            original_attribution_id=data["original_attribution_id"],
            adjustment_amount=CurrencyAmount.from_dict(data["adjustment_amount"]),
            adjustment_reason=data["adjustment_reason"],
            adjustment_timestamp=timestamp,
            aggregate_version=data.get("aggregate_version", 1)
        )


@dataclass
class CostLedgerProjection:
    dimension_key: str
    dimension_value: str
    balance: CurrencyAmount
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "dimension_key": self.dimension_key,
            "dimension_value": self.dimension_value,
            "balance": self.balance.to_dict(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CostLedgerProjection':
        updated_at = datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"]
        return cls(
            dimension_key=data["dimension_key"],
            dimension_value=data["dimension_value"],
            balance=CurrencyAmount.from_dict(data["balance"]),
            updated_at=updated_at
        )
