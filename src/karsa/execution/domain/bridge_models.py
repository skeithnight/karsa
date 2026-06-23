"""Execution Bridge Domain Models — Sprint-56.

Hard Risk Engine, Order Slicer, and Kill Switch value objects.
Extends the existing execution/ bounded context.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    RISK_REJECTED = "RISK_REJECTED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class RiskLimitType(str, Enum):
    MAX_POSITION_SIZE_PCT = "MAX_POSITION_SIZE_PCT"
    MAX_DAILY_TURNOVER_USD = "MAX_DAILY_TURNOVER_USD"
    MAX_SINGLE_ORDER_USD = "MAX_SINGLE_ORDER_USD"


@dataclass
class RiskLimit:
    """Value object: a configurable risk limit."""
    limit_type: RiskLimitType
    limit_value: float
    is_active: bool = True


@dataclass
class RiskRejection:
    """Value object: a risk check rejection with details."""
    reason: str
    limit_type: RiskLimitType
    actual_value: float
    limit_value: float


def _generate_order_urn() -> str:
    return f"urn:karsa:execution:order:{uuid.uuid4()}"


def _generate_fill_urn() -> str:
    return f"urn:karsa:execution:fill:{uuid.uuid4()}"


@dataclass
class ExecutionOrder:
    """Aggregate: an execution order with lifecycle state machine.

    Lifecycle: PENDING -> RISK_REJECTED | SUBMITTED -> PARTIALLY_FILLED -> FILLED | CANCELLED | FAILED
    """
    order_id: str = field(default_factory=_generate_order_urn)
    thesis_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    target_quantity: float = 0.0
    filled_quantity: float = 0.0
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None
    parent_order_id: Optional[str] = None  # For TWAP child orders
    is_twap_child: bool = False
    twap_sequence: int = 0  # Position in TWAP slice sequence
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition(self, new_status: OrderStatus) -> None:
        """Transition order to new status with validation."""
        valid_transitions = {
            OrderStatus.PENDING: {OrderStatus.RISK_REJECTED, OrderStatus.SUBMITTED},
            OrderStatus.SUBMITTED: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FILLED},
            OrderStatus.PARTIALLY_FILLED: {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FAILED},
        }
        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self.status.value} -> {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    @property
    def order_value_usd(self) -> float:
        """Estimated order value in USD."""
        price = self.limit_price or 0.0
        return self.target_quantity * price

    @property
    def is_complete(self) -> bool:
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
            OrderStatus.RISK_REJECTED,
        )


@dataclass
class ExecutionFill:
    """Entity: a single fill against an execution order."""
    fill_id: str = field(default_factory=_generate_fill_urn)
    order_id: str = ""
    broker_fill_id: Optional[str] = None
    quantity: float = 0.0
    fill_price: float = 0.0
    commission: float = 0.0
    filled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def fill_value_usd(self) -> float:
        return self.quantity * self.fill_price


@dataclass
class TWAPSlice:
    """Value object: a single TWAP slice plan."""
    child_order_id: str = field(default_factory=_generate_order_urn)
    quantity: float = 0.0
    scheduled_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sequence: int = 0


@dataclass
class TWAPPlan:
    """Value object: a TWAP execution plan with multiple slices."""
    parent_order_id: str = ""
    slices: List[TWAPSlice] = field(default_factory=list)
    interval_minutes: int = 5
    total_duration_minutes: int = 30

    @property
    def slice_count(self) -> int:
        return len(self.slices)
