from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class PEPValidationStatus(Enum):
    STAGED = "STAGED"
    PEP_VALIDATED = "PEP_VALIDATED"
    REJECTED = "REJECTED"


class RouteStatus(Enum):
    SENT = "SENT"
    REJECTED = "REJECTED"


class ExecutionLifecycleState(Enum):
    STAGED = "STAGED"
    PEP_VALIDATED = "PEP_VALIDATED"
    ROUTED = "ROUTED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"


def generate_urn(entity_type: str, context: str = "execution") -> str:
    """Generates a URN in the format urn:karsa:<context>:<entity_type>:<uuid>."""
    return f"urn:karsa:{context}:{entity_type}:{uuid.uuid4()}"


def validate_urn(urn: str, expected_entity_type: str, expected_context: str = "execution") -> None:
    """Validates that a URN complies with the target format."""
    prefix = f"urn:karsa:{expected_context}:{expected_entity_type}:"
    if not urn.startswith(prefix):
        raise ValueError(f"Invalid URN: '{urn}'. Expected URN to start with '{prefix}'")
    parts = urn[len(prefix):].split(":")
    if len(parts) != 1 or not parts[0]:
        raise ValueError(f"Invalid URN UUID suffix: '{urn}'")


@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: str  # urn:karsa:execution:record:<uuid>
    correlation_id: str  # urn:karsa:cio:decision:<uuid>
    causation_id: str  # urn:karsa:cio:decision:<uuid> (or parent event URN)
    symbol: str  # e.g., urn:karsa:asset:ticker:nvda
    quantity: float
    direction: str  # BUY, SELL
    order_type: str  # MARKET, LIMIT
    price: Optional[float]
    cio_signature: str
    gov_exception_id: Optional[str] = None  # urn:karsa:governance:exception:<uuid>
    gov_exception_signature: Optional[str] = None
    pep_status: PEPValidationStatus = PEPValidationStatus.STAGED
    rejection_reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        validate_urn(self.execution_id, "record")
        if self.symbol.startswith("urn:karsa:"):
            # Ensure it conforms to urn:karsa:<anything>
            if not self.symbol.startswith("urn:karsa:"):
                raise ValueError(f"Invalid asset ticker URN: {self.symbol}")
        if self.gov_exception_id:
            validate_urn(self.gov_exception_id, "exception", expected_context="governance")
        if self.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")


@dataclass(frozen=True)
class RoutingRecord:
    route_id: str  # urn:karsa:execution:route:<uuid>
    execution_id: str  # urn:karsa:execution:record:<uuid>
    broker_id: str
    broker_order_ref: Optional[str]
    route_status: RouteStatus
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        validate_urn(self.route_id, "route")
        validate_urn(self.execution_id, "record")


@dataclass(frozen=True)
class FillRecord:
    fill_id: str  # urn:karsa:execution:fill:<uuid>
    route_id: str  # urn:karsa:execution:route:<uuid>
    filled_quantity: float
    filled_price: float
    commission: float
    slippage: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        validate_urn(self.fill_id, "fill")
        validate_urn(self.route_id, "route")
        if self.filled_quantity <= 0:
            raise ValueError("Filled quantity must be greater than zero")
        if self.filled_price < 0:
            raise ValueError("Filled price cannot be negative")
        if self.commission < 0:
            raise ValueError("Commission cannot be negative")
        if self.slippage < 0:
            raise ValueError("Slippage cannot be negative")
