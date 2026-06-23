"""Execution Bridge Domain Events — Sprint-56/57.

Events for the hard risk engine, order slicer, and broker feedback loop.
Extends existing execution/ event contracts.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from karsa.shared.domain.event import DomainEvent


@dataclass
class RiskRejectedEvent(DomainEvent):
    """Emitted when Hard Risk Engine rejects an order."""
    order_id: str = ""
    thesis_id: str = ""
    symbol: str = ""
    reason: str = ""
    limit_type: str = ""
    actual_value: float = 0.0
    limit_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "order_id": self.order_id,
            "thesis_id": self.thesis_id,
            "symbol": self.symbol,
            "reason": self.reason,
            "limit_type": self.limit_type,
            "actual_value": self.actual_value,
            "limit_value": self.limit_value,
        }


@dataclass
class OrderSubmittedEvent(DomainEvent):
    """Emitted when an order is submitted to a broker."""
    order_id: str = ""
    thesis_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    order_type: str = ""
    broker_order_id: str = ""
    is_twap_child: bool = False
    parent_order_id: str = ""
    twap_sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "order_id": self.order_id,
            "thesis_id": self.thesis_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "broker_order_id": self.broker_order_id,
            "is_twap_child": self.is_twap_child,
            "parent_order_id": self.parent_order_id,
            "twap_sequence": self.twap_sequence,
        }


@dataclass
class ExecutionFailedEvent(DomainEvent):
    """Emitted when an order fails at the broker."""
    order_id: str = ""
    reason: str = ""
    broker_error_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "order_id": self.order_id,
            "reason": self.reason,
            "broker_error_code": self.broker_error_code,
        }


@dataclass
class KillSwitchActivatedEvent(DomainEvent):
    """Emitted when the kill switch is activated. Cancels all open orders."""
    reason: str = ""
    activated_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "reason": self.reason,
            "activated_by": self.activated_by,
        }


@dataclass
class TWAPPlanCreatedEvent(DomainEvent):
    """Emitted when a TWAP plan is created for a large order."""
    parent_order_id: str = ""
    symbol: str = ""
    total_quantity: float = 0.0
    slice_count: int = 0
    interval_minutes: int = 5
    total_duration_minutes: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "parent_order_id": self.parent_order_id,
            "symbol": self.symbol,
            "total_quantity": self.total_quantity,
            "slice_count": self.slice_count,
            "interval_minutes": self.interval_minutes,
            "total_duration_minutes": self.total_duration_minutes,
        }
