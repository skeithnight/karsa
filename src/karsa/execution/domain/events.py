from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class OrderStagedEvent:
    event_id: str = field(default_factory=lambda: f"evt_stg_{uuid.uuid4().hex[:8]}")
    event_type: str = "OrderStagedEvent"
    correlation_id: str = ""
    causation_id: str = ""
    execution_id: str = ""
    symbol: str = ""
    quantity: float = 0.0
    direction: str = ""  # BUY, SELL
    order_type: str = "MARKET"  # MARKET, LIMIT
    price: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_version: int = 1


@dataclass(frozen=True)
class OrderValidatedEvent:
    event_id: str = field(default_factory=lambda: f"evt_val_{uuid.uuid4().hex[:8]}")
    event_type: str = "OrderValidatedEvent"
    correlation_id: str = ""
    causation_id: str = ""
    execution_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_version: int = 1


@dataclass(frozen=True)
class OrderRoutedEvent:
    event_id: str = field(default_factory=lambda: f"evt_rot_{uuid.uuid4().hex[:8]}")
    event_type: str = "OrderRoutedEvent"
    correlation_id: str = ""
    causation_id: str = ""
    execution_id: str = ""
    broker_id: str = ""
    broker_order_ref: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_version: int = 1


@dataclass(frozen=True)
class OrderFilledEvent:
    event_id: str = field(default_factory=lambda: f"evt_fil_{uuid.uuid4().hex[:8]}")
    event_type: str = "OrderFilledEvent"
    correlation_id: str = ""
    causation_id: str = ""
    execution_id: str = ""
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_version: int = 1


@dataclass(frozen=True)
class OrderRejectedEvent:
    event_id: str = field(default_factory=lambda: f"evt_rej_{uuid.uuid4().hex[:8]}")
    event_type: str = "OrderRejectedEvent"
    correlation_id: str = ""
    causation_id: str = ""
    execution_id: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_version: int = 1


@dataclass(frozen=True)
class ExecutionIncidentEvent:
    event_id: str = field(default_factory=lambda: f"evt_inc_{uuid.uuid4().hex[:8]}")
    event_type: str = "ExecutionIncidentEvent"
    correlation_id: str = ""
    causation_id: str = ""
    execution_id: str = ""
    incident_type: str = ""
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_version: int = 1
