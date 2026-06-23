"""Execution Bridge Application Services — Sprint-56/57.

OrderManagementSystem: Orchestrates thesis -> risk check -> order creation -> slicing.
KillSwitchService: Emergency halt for all trading.
BrokerAdapterFactory: Resolves broker name -> concrete adapter.
ExecutionFeedbackLoop: Translates broker reports -> Karsa events.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type

from karsa.execution.domain.bridge_models import (
    ExecutionOrder,
    ExecutionFill,
    OrderSide,
    OrderType,
    OrderStatus,
    RiskLimitType,
)
from karsa.execution.domain.bridge_events import (
    RiskRejectedEvent,
    OrderSubmittedEvent,
    ExecutionFailedEvent,
    KillSwitchActivatedEvent,
    TWAPPlanCreatedEvent,
)
from karsa.execution.application.risk_engine import HardRiskEngine
from karsa.execution.application.order_slicer import OrderSlicer

logger = logging.getLogger(__name__)


class OrderManagementSystem:
    """Orchestrates the order lifecycle: thesis -> risk -> create -> slice -> submit.

    Consumes ThesisApprovedEvent, creates ExecutionOrder, runs risk checks,
    determines slicing strategy, and prepares orders for broker routing.
    """

    def __init__(
        self,
        risk_engine: HardRiskEngine,
        order_slicer: OrderSlicer,
        order_repo: Any,  # PostgresExecutionOrderRepository
        publish_event: Optional[Callable] = None,
        broker_adapter: Optional[Any] = None,  # BrokerAdapterPort
    ):
        self._risk_engine = risk_engine
        self._slicer = order_slicer
        self._order_repo = order_repo
        self._publish_event = publish_event
        self._broker_adapter = broker_adapter
        self._kill_switch_active = False
        self._processed_thesis_ids: set = set()  # Idempotency guard

    async def process_approved_thesis(
        self,
        thesis_id: str,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
        position_size_pct: float = 1.0,
    ) -> Optional[ExecutionOrder]:
        """Process a ThesisApprovedEvent into an execution order.

        Steps:
        1. Idempotency check (dedup by thesis_id)
        2. Kill switch check
        3. Create ExecutionOrder
        4. Run Hard Risk Engine
        5. Determine slicing strategy
        6. Submit to broker (or create TWAP plan)
        """
        # 1. Idempotency check
        if thesis_id in self._processed_thesis_ids:
            logger.info(f"Duplicate thesis {thesis_id} — skipping")
            return None
        self._processed_thesis_ids.add(thesis_id)

        # 2. Kill switch check
        if self._kill_switch_active:
            logger.warning(f"Kill switch active — rejecting thesis {thesis_id}")
            return None

        # 3. Create order
        try:
            order_side = OrderSide(side.upper())
        except ValueError:
            order_side = OrderSide.BUY

        order = ExecutionOrder(
            thesis_id=thesis_id,
            symbol=ticker,
            side=order_side,
            target_quantity=quantity,
            order_type=OrderType.MARKET,
            limit_price=price,
            status=OrderStatus.PENDING,
        )

        # 4. Run risk checks
        approved, rejection = self._risk_engine.validate_order(order, estimated_price=price)

        if not approved:
            order.transition(OrderStatus.RISK_REJECTED)
            await self._save_order(order)

            if self._publish_event:
                await self._publish_event(RiskRejectedEvent(
                    order_id=order.order_id,
                    thesis_id=thesis_id,
                    symbol=ticker,
                    reason=rejection.reason,
                    limit_type=rejection.limit_type.value,
                    actual_value=rejection.actual_value,
                    limit_value=rejection.limit_value,
                ))

            logger.warning(f"Risk rejected order for {ticker}: {rejection.reason}")
            return order

        # 5. Determine slicing strategy
        if self._slicer.should_slice(order, estimated_price=price):
            # TWAP slicing
            plan = self._slicer.create_twap_plan(order, estimated_price=price)
            child_orders = self._slicer.create_child_orders(order, plan)

            order.order_type = OrderType.TWAP
            order.transition(OrderStatus.SUBMITTED)
            await self._save_order(order)

            if self._publish_event:
                await self._publish_event(TWAPPlanCreatedEvent(
                    parent_order_id=order.order_id,
                    symbol=ticker,
                    total_quantity=quantity,
                    slice_count=plan.slice_count,
                    interval_minutes=plan.interval_minutes,
                    total_duration_minutes=plan.total_duration_minutes,
                ))

            # Save and submit child orders
            for child in child_orders:
                await self._save_order(child)
                await self._submit_to_broker(child)

            logger.info(
                f"TWAP plan for {ticker}: {plan.slice_count} slices, "
                f"{quantity} total shares"
            )
        else:
            # Single order
            order.transition(OrderStatus.SUBMITTED)
            await self._save_order(order)
            await self._submit_to_broker(order)

        return order

    async def _submit_to_broker(self, order: ExecutionOrder) -> None:
        """Submit an order to the broker adapter."""
        if not self._broker_adapter:
            logger.info(f"Paper trading mode — order {order.order_id} simulated")
            return

        try:
            result = self._broker_adapter.route_order(
                execution_id=order.order_id,
                symbol=order.symbol,
                quantity=order.target_quantity,
                direction=order.side.value,
                order_type=order.order_type.value,
                price=order.limit_price,
            )
            order.broker_order_id = result.get("broker_order_ref")
            await self._save_order(order)

            if self._publish_event:
                await self._publish_event(OrderSubmittedEvent(
                    order_id=order.order_id,
                    thesis_id=order.thesis_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    quantity=order.target_quantity,
                    order_type=order.order_type.value,
                    broker_order_id=order.broker_order_id or "",
                    is_twap_child=order.is_twap_child,
                    parent_order_id=order.parent_order_id or "",
                    twap_sequence=order.twap_sequence,
                ))
        except Exception as e:
            order.transition(OrderStatus.FAILED)
            await self._save_order(order)
            if self._publish_event:
                await self._publish_event(ExecutionFailedEvent(
                    order_id=order.order_id,
                    reason=str(e),
                ))
            logger.error(f"Broker submission failed for {order.order_id}: {e}")

    async def _save_order(self, order: ExecutionOrder) -> None:
        """Persist order to repository."""
        try:
            await asyncio.to_thread(self._order_repo.save, order)
        except Exception as e:
            logger.error(f"Failed to save order {order.order_id}: {e}")

    def activate_kill_switch(self, reason: str = "Manual activation") -> None:
        """Activate the kill switch — all new theses rejected."""
        self._kill_switch_active = True
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")

    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch."""
        self._kill_switch_active = False
        logger.info("Kill switch deactivated")

    @property
    def is_kill_switch_active(self) -> bool:
        return self._kill_switch_active


class KillSwitchService:
    """Subscribes to KillSwitchActivatedEvent on the event bus.

    On activation: cancels all open orders, rejects new theses.
    """

    def __init__(
        self,
        oms: OrderManagementSystem,
        order_repo: Any,
        publish_event: Optional[Callable] = None,
    ):
        self._oms = oms
        self._order_repo = order_repo
        self._publish_event = publish_event

    async def handle_kill_switch_event(self, event: KillSwitchActivatedEvent) -> None:
        """Handle a kill switch activation event."""
        logger.critical(f"Kill switch event received: {event.reason}")
        self._oms.activate_kill_switch(event.reason)

        # Cancel all open orders
        open_orders = await asyncio.to_thread(
            self._order_repo.find_by_status,
            [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED],
        )
        for order in open_orders:
            try:
                order.transition(OrderStatus.CANCELLED)
                await asyncio.to_thread(self._order_repo.save, order)
                logger.info(f"Cancelled order {order.order_id} due to kill switch")
            except Exception as e:
                logger.error(f"Failed to cancel order {order.order_id}: {e}")

        logger.info(f"Kill switch: cancelled {len(open_orders)} open orders")


# --- Sprint-57: Broker Adapters ---

# Broker adapter registry (same pattern as ConnectorFactory)
BROKER_ADAPTER_REGISTRY: Dict[str, Type] = {}


def register_broker_adapter(broker_name: str):
    """Decorator to register a broker adapter class."""
    def decorator(cls):
        BROKER_ADAPTER_REGISTRY[broker_name] = cls
        return cls
    return decorator


class BrokerAdapterFactory:
    """Resolves broker name -> concrete adapter class.

    Same registry pattern as the Data Bridge's ConnectorFactory.
    """

    @staticmethod
    def create(
        broker_name: str,
        credentials: Dict[str, str],
        **kwargs,
    ) -> Any:
        """Create a broker adapter instance."""
        adapter_cls = BROKER_ADAPTER_REGISTRY.get(broker_name)
        if not adapter_cls:
            available = list(BROKER_ADAPTER_REGISTRY.keys())
            raise ValueError(
                f"No broker adapter registered for '{broker_name}'. "
                f"Available: {available}"
            )
        return adapter_cls(credentials=credentials, **kwargs)

    @staticmethod
    def list_registered() -> List[str]:
        return list(BROKER_ADAPTER_REGISTRY.keys())


class ExecutionFeedbackLoop:
    """Translates broker fill/rejection reports into Karsa domain events.

    Listens to broker WebSocket, updates execution_orders table,
    and emits OrderFilledEvent/ExecutionFailedEvent.
    """

    def __init__(
        self,
        order_repo: Any,
        fill_repo: Any,
        publish_event: Optional[Callable] = None,
    ):
        self._order_repo = order_repo
        self._fill_repo = fill_repo
        self._publish_event = publish_event

    async def on_fill_report(
        self,
        broker_order_id: str,
        broker_fill_id: str,
        quantity: float,
        fill_price: float,
        commission: float = 0.0,
    ) -> Optional[ExecutionFill]:
        """Process a fill report from the broker."""
        order = await asyncio.to_thread(
            self._order_repo.find_by_broker_order_id, broker_order_id
        )
        if not order:
            logger.warning(f"Fill for unknown broker order {broker_order_id}")
            return None

        # Record fill
        fill = ExecutionFill(
            order_id=order.order_id,
            broker_fill_id=broker_fill_id,
            quantity=quantity,
            fill_price=fill_price,
            commission=commission,
        )
        await asyncio.to_thread(self._order_repo.save_fill, fill)

        # Update order filled quantity
        order.filled_quantity += quantity
        if order.filled_quantity >= order.target_quantity:
            order.transition(OrderStatus.FILLED)
        else:
            if order.status == OrderStatus.SUBMITTED:
                order.transition(OrderStatus.PARTIALLY_FILLED)
        await asyncio.to_thread(self._order_repo.save, order)

        logger.info(
            f"Fill recorded: {order.symbol} {quantity}@{fill_price} "
            f"({order.filled_quantity}/{order.target_quantity})"
        )
        return fill

    async def on_rejection_report(
        self,
        broker_order_id: str,
        error_message: str,
        error_code: str = "",
    ) -> None:
        """Process a rejection report from the broker."""
        order = await asyncio.to_thread(
            self._order_repo.find_by_broker_order_id, broker_order_id
        )
        if not order:
            logger.warning(f"Rejection for unknown broker order {broker_order_id}")
            return

        order.transition(OrderStatus.FAILED)
        await asyncio.to_thread(self._order_repo.save, order)

        if self._publish_event:
            await self._publish_event(ExecutionFailedEvent(
                order_id=order.order_id,
                reason=error_message,
                broker_error_code=error_code,
            ))

        logger.error(f"Order {order.order_id} rejected by broker: {error_message}")
