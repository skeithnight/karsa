"""Execution Bridge Repository — Sprint-56/57.

CRUD for execution_orders and execution_fills tables.
Uses SQLAlchemy ORM.
"""
import logging
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Numeric, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func

from karsa.shared.persistence.base import Base
from karsa.shared.persistence.mixins import UUIDMixin
from karsa.shared.persistence.types import GUID
from karsa.execution.domain.bridge_models import (
    ExecutionOrder,
    ExecutionFill,
    OrderSide,
    OrderType,
    OrderStatus,
)

logger = logging.getLogger(__name__)


# --- SQLAlchemy Models ---

class ExecutionOrderModel(UUIDMixin, Base):
    __tablename__ = "execution_orders"

    thesis_id = Column(String(100), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    target_quantity = Column(Numeric(18, 8), nullable=False)
    filled_quantity = Column(Numeric(18, 8), server_default="0")
    order_type = Column(String(20), nullable=False)
    limit_price = Column(Numeric(18, 8), nullable=True)
    status = Column(String(20), server_default="PENDING", index=True)
    broker_order_id = Column(String(100), nullable=True, index=True)
    parent_order_id = Column(String(36), nullable=True, index=True)
    is_twap_child = Column(Boolean, server_default="false")
    twap_sequence = Column(Integer, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExecutionFillModel(UUIDMixin, Base):
    __tablename__ = "execution_fills"

    order_id = Column(GUID(), ForeignKey("execution_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_fill_id = Column(String(100), nullable=True)
    quantity = Column(Numeric(18, 8), nullable=False)
    fill_price = Column(Numeric(18, 8), nullable=False)
    commission = Column(Numeric(18, 4), server_default="0")
    filled_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskLimitModel(Base):
    __tablename__ = "execution_risk_limits"

    id = Column(String(36), primary_key=True)
    limit_type = Column(String(50), unique=True, nullable=False)
    limit_value = Column(Numeric(18, 4), nullable=False)
    is_active = Column(Boolean, server_default="true")


# --- Repository ---

class PostgresExecutionOrderRepository:
    """CRUD for execution_orders and execution_fills."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, order: ExecutionOrder) -> None:
        """Save or update an execution order."""
        existing = self.session.query(ExecutionOrderModel).filter_by(id=order.order_id).first()
        if existing:
            existing.filled_quantity = order.filled_quantity
            existing.status = order.status.value
            existing.broker_order_id = order.broker_order_id
            existing.updated_at = datetime.now(timezone.utc)
        else:
            model = ExecutionOrderModel(
                id=order.order_id,
                thesis_id=order.thesis_id,
                symbol=order.symbol,
                side=order.side.value,
                target_quantity=order.target_quantity,
                filled_quantity=order.filled_quantity,
                order_type=order.order_type.value,
                limit_price=order.limit_price,
                status=order.status.value,
                broker_order_id=order.broker_order_id,
                parent_order_id=order.parent_order_id,
                is_twap_child=order.is_twap_child,
                twap_sequence=order.twap_sequence,
            )
            self.session.add(model)

    def find_by_id(self, order_id: str) -> Optional[ExecutionOrder]:
        """Find an order by ID."""
        m = self.session.query(ExecutionOrderModel).filter_by(id=order_id).first()
        return self._to_order(m) if m else None

    def find_by_thesis_id(self, thesis_id: str) -> Optional[ExecutionOrder]:
        """Find an order by thesis ID (for idempotency)."""
        m = self.session.query(ExecutionOrderModel).filter_by(thesis_id=thesis_id).first()
        return self._to_order(m) if m else None

    def find_by_broker_order_id(self, broker_order_id: str) -> Optional[ExecutionOrder]:
        """Find an order by broker order ID."""
        m = self.session.query(ExecutionOrderModel).filter_by(broker_order_id=broker_order_id).first()
        return self._to_order(m) if m else None

    def find_by_status(self, statuses: List[OrderStatus]) -> List[ExecutionOrder]:
        """Find all orders with the given statuses."""
        status_values = [s.value for s in statuses]
        models = self.session.query(ExecutionOrderModel).filter(
            ExecutionOrderModel.status.in_(status_values)
        ).all()
        return [self._to_order(m) for m in models]

    def find_children(self, parent_order_id: str) -> List[ExecutionOrder]:
        """Find all TWAP child orders for a parent order."""
        models = self.session.query(ExecutionOrderModel).filter_by(
            parent_order_id=parent_order_id
        ).order_by("twap_sequence").all()
        return [self._to_order(m) for m in models]

    def save_fill(self, fill: ExecutionFill) -> None:
        """Save an execution fill."""
        model = ExecutionFillModel(
            id=fill.fill_id,
            order_id=fill.order_id,
            broker_fill_id=fill.broker_fill_id,
            quantity=fill.quantity,
            fill_price=fill.fill_price,
            commission=fill.commission,
        )
        self.session.add(model)

    def find_fills_by_order(self, order_id: str) -> List[ExecutionFill]:
        """Find all fills for an order."""
        models = self.session.query(ExecutionFillModel).filter_by(order_id=order_id).all()
        return [
            ExecutionFill(
                fill_id=str(m.id),
                order_id=str(m.order_id),
                broker_fill_id=m.broker_fill_id,
                quantity=float(m.quantity),
                fill_price=float(m.fill_price),
                commission=float(m.commission),
                filled_at=m.filled_at,
            )
            for m in models
        ]

    def _to_order(self, m: ExecutionOrderModel) -> ExecutionOrder:
        """Convert ORM model to domain model."""
        return ExecutionOrder(
            order_id=str(m.id),
            thesis_id=str(m.thesis_id),
            symbol=m.symbol,
            side=OrderSide(m.side),
            target_quantity=float(m.target_quantity),
            filled_quantity=float(m.filled_quantity or 0),
            order_type=OrderType(m.order_type),
            limit_price=float(m.limit_price) if m.limit_price else None,
            status=OrderStatus(m.status),
            broker_order_id=m.broker_order_id,
            parent_order_id=str(m.parent_order_id) if m.parent_order_id else None,
            is_twap_child=bool(m.is_twap_child),
            twap_sequence=int(m.twap_sequence or 0),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
