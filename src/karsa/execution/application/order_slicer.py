"""TWAP Order Slicer — Sprint-56.

Splits large orders into time-weighted average price (TWAP) child orders.
E.g., $100k order -> 5-minute intervals over 30 minutes = 6 child orders.

Respects market hours (no child orders after 3:55 PM ET).
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from karsa.execution.domain.bridge_models import (
    ExecutionOrder,
    TWAPPlan,
    TWAPSlice,
    OrderType,
    OrderSide,
    OrderStatus,
    _generate_order_urn,
)

logger = logging.getLogger(__name__)

# TWAP configuration
TWAP_THRESHOLD_USD = 50_000.0  # Orders above this get TWAP sliced
TWAP_INTERVAL_MINUTES = 5
TWAP_DURATION_MINUTES = 30
MARKET_CLOSE_ET = (15, 55)  # 3:55 PM ET — no child orders after this


class OrderSlicer:
    """Determines slicing strategy and creates TWAP plans for large orders.

    Orders below the TWAP threshold are submitted as single orders.
    Orders above the threshold are split into equal-sized child orders
    distributed over a configurable time window.
    """

    def __init__(
        self,
        twap_threshold_usd: float = TWAP_THRESHOLD_USD,
        interval_minutes: int = TWAP_INTERVAL_MINUTES,
        duration_minutes: int = TWAP_DURATION_MINUTES,
    ):
        self._threshold = twap_threshold_usd
        self._interval = interval_minutes
        self._duration = duration_minutes

    def should_slice(self, order: ExecutionOrder, estimated_price: float = 0.0) -> bool:
        """Determine if an order should be TWAP sliced.

        Args:
            order: The execution order.
            estimated_price: Price estimate if order has no limit_price.

        Returns:
            True if order value exceeds TWAP threshold.
        """
        price = order.limit_price or estimated_price
        order_value = order.target_quantity * price
        return order_value >= self._threshold

    def create_twap_plan(
        self,
        order: ExecutionOrder,
        estimated_price: float = 0.0,
        start_time: Optional[datetime] = None,
    ) -> TWAPPlan:
        """Create a TWAP execution plan for a large order.

        Args:
            order: The parent execution order.
            estimated_price: Price estimate for calculating order value.
            start_time: When to start the TWAP (default: now).

        Returns:
            TWAPPlan with scheduled slices.
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc)

        # Calculate number of slices
        num_slices = max(1, self._duration // self._interval)

        # Split quantity equally across slices
        slice_quantity = order.target_quantity / num_slices

        slices: List[TWAPSlice] = []
        for i in range(num_slices):
            scheduled = start_time + timedelta(minutes=i * self._interval)

            # Respect market hours — skip slices after 3:55 PM ET
            # (simplified: assume UTC; real implementation needs ET timezone)
            if not self._is_within_market_hours(scheduled):
                logger.warning(f"TWAP slice {i+1} skipped — outside market hours: {scheduled}")
                continue

            slices.append(TWAPSlice(
                quantity=round(slice_quantity, 8),
                scheduled_time=scheduled,
                sequence=i + 1,
            ))

        if not slices:
            # All slices outside market hours — fall back to single order
            logger.warning("All TWAP slices outside market hours — falling back to single order")
            slices.append(TWAPSlice(
                quantity=order.target_quantity,
                scheduled_time=start_time,
                sequence=1,
            ))

        plan = TWAPPlan(
            parent_order_id=order.order_id,
            slices=slices,
            interval_minutes=self._interval,
            total_duration_minutes=self._duration,
        )

        logger.info(
            f"TWAP plan created: {plan.slice_count} slices over "
            f"{self._duration}min for {order.symbol} "
            f"({order.target_quantity} shares)"
        )
        return plan

    def create_child_orders(
        self,
        parent_order: ExecutionOrder,
        plan: TWAPPlan,
    ) -> List[ExecutionOrder]:
        """Create child ExecutionOrder objects from a TWAP plan.

        Args:
            parent_order: The parent order being sliced.
            plan: The TWAP execution plan.

        Returns:
            List of child ExecutionOrder objects.
        """
        children = []
        for slice in plan.slices:
            child = ExecutionOrder(
                thesis_id=parent_order.thesis_id,
                symbol=parent_order.symbol,
                side=parent_order.side,
                target_quantity=slice.quantity,
                order_type=OrderType.MARKET,  # TWAP slices are market orders
                limit_price=parent_order.limit_price,
                status=OrderStatus.PENDING,
                parent_order_id=parent_order.order_id,
                is_twap_child=True,
                twap_sequence=slice.sequence,
            )
            children.append(child)

        return children

    def _is_within_market_hours(self, dt: datetime) -> bool:
        """Check if a datetime is within US market hours (simplified).

        A production implementation would use pytz for ET timezone
        and handle holidays/half-days.
        """
        # Simplified: skip weekends, assume 9:30 AM - 3:55 PM ET
        # For MVP, just check it's not too late in the day
        hour = dt.hour
        minute = dt.minute
        close_hour, close_minute = MARKET_CLOSE_ET

        if hour > close_hour or (hour == close_hour and minute >= close_minute):
            return False

        # Skip weekends
        if dt.weekday() >= 5:
            return False

        return True

    @property
    def threshold_usd(self) -> float:
        return self._threshold
