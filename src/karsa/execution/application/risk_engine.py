"""Hard Pre-Trade Risk Engine — Sprint-56.

Deterministic, non-AI risk checks on every order before broker routing.
Three checks:
1. Max single order USD value
2. Max position size % of portfolio (post-trade)
3. Daily turnover circuit breaker

No LLMs. No probabilistic decisions. Hard money limits.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from karsa.execution.domain.bridge_models import (
    ExecutionOrder,
    ExecutionFill,
    RiskLimit,
    RiskLimitType,
    RiskRejection,
    OrderSide,
)

logger = logging.getLogger(__name__)

# Default risk limits (seeded into execution_risk_limits table)
DEFAULT_LIMITS = {
    RiskLimitType.MAX_SINGLE_ORDER_USD: 500_000.0,
    RiskLimitType.MAX_POSITION_SIZE_PCT: 5.0,  # 5% of portfolio
    RiskLimitType.MAX_DAILY_TURNOVER_USD: 5_000_000.0,
}


class HardRiskEngine:
    """Validates orders against quantitative risk limits.

    All checks are deterministic — no AI, no probability.
    Returns (True, None) if approved, (False, RiskRejection) if rejected.
    """

    def __init__(
        self,
        risk_limits: Optional[Dict[RiskLimitType, RiskLimit]] = None,
        portfolio_value_usd: float = 1_000_000.0,  # Default portfolio value
        get_position_value: Optional[callable] = None,  # (symbol) -> float USD
        get_daily_turnover: Optional[callable] = None,  # () -> float USD
    ):
        self._limits = risk_limits or {
            lt: RiskLimit(limit_type=lt, limit_value=v, is_active=True)
            for lt, v in DEFAULT_LIMITS.items()
        }
        self._portfolio_value = portfolio_value_usd
        self._get_position_value = get_position_value or (lambda s: 0.0)
        self._get_daily_turnover = get_daily_turnover or (lambda: 0.0)
        self._rejected_count = 0
        self._approved_count = 0

    def validate_order(
        self,
        order: ExecutionOrder,
        estimated_price: Optional[float] = None,
    ) -> Tuple[bool, Optional[RiskRejection]]:
        """Run all hard risk checks on an order.

        Args:
            order: The ExecutionOrder to validate.
            estimated_price: Price estimate if order has no limit_price.

        Returns:
            (True, None) if approved, (False, RiskRejection) if rejected.
        """
        price = order.limit_price or estimated_price or 0.0
        order_value = order.target_quantity * price

        # Check 1: Max single order USD
        rejection = self._check_max_single_order(order_value)
        if rejection:
            self._rejected_count += 1
            return False, rejection

        # Check 2: Max position size % (post-trade)
        rejection = self._check_max_position_size(order.symbol, order.side, order_value)
        if rejection:
            self._rejected_count += 1
            return False, rejection

        # Check 3: Daily turnover circuit breaker
        rejection = self._check_daily_turnover(order_value)
        if rejection:
            self._rejected_count += 1
            return False, rejection

        self._approved_count += 1
        return True, None

    def _check_max_single_order(self, order_value_usd: float) -> Optional[RiskRejection]:
        """Check if order value exceeds max single order limit."""
        limit = self._limits.get(RiskLimitType.MAX_SINGLE_ORDER_USD)
        if not limit or not limit.is_active:
            return None

        if order_value_usd > limit.limit_value:
            return RiskRejection(
                reason=f"Order value ${order_value_usd:,.2f} exceeds max single order ${limit.limit_value:,.2f}",
                limit_type=RiskLimitType.MAX_SINGLE_ORDER_USD,
                actual_value=order_value_usd,
                limit_value=limit.limit_value,
            )
        return None

    def _check_max_position_size(
        self,
        symbol: str,
        side: OrderSide,
        order_value_usd: float,
    ) -> Optional[RiskRejection]:
        """Check if post-trade position would exceed max % of portfolio."""
        limit = self._limits.get(RiskLimitType.MAX_POSITION_SIZE_PCT)
        if not limit or not limit.is_active:
            return None

        current_position = self._get_position_value(symbol)

        # Calculate post-trade position value
        if side in (OrderSide.BUY,):
            post_trade_position = current_position + order_value_usd
        else:  # SELL, SELL_SHORT
            post_trade_position = current_position - order_value_usd

        max_allowed = self._portfolio_value * (limit.limit_value / 100.0)

        if abs(post_trade_position) > max_allowed:
            return RiskRejection(
                reason=(
                    f"Post-trade position ${abs(post_trade_position):,.2f} would exceed "
                    f"{limit.limit_value}% of portfolio (${max_allowed:,.2f})"
                ),
                limit_type=RiskLimitType.MAX_POSITION_SIZE_PCT,
                actual_value=abs(post_trade_position),
                limit_value=max_allowed,
            )
        return None

    def _check_daily_turnover(self, order_value_usd: float) -> Optional[RiskRejection]:
        """Check if this order would breach the daily turnover circuit breaker."""
        limit = self._limits.get(RiskLimitType.MAX_DAILY_TURNOVER_USD)
        if not limit or not limit.is_active:
            return None

        current_turnover = self._get_daily_turnover()
        projected = current_turnover + order_value_usd

        if projected > limit.limit_value:
            return RiskRejection(
                reason=(
                    f"Daily turnover ${projected:,.2f} would exceed circuit breaker "
                    f"${limit.limit_value:,.2f} (current: ${current_turnover:,.2f})"
                ),
                limit_type=RiskLimitType.MAX_DAILY_TURNOVER_USD,
                actual_value=projected,
                limit_value=limit.limit_value,
            )
        return None

    def update_limit(self, limit_type: RiskLimitType, new_value: float) -> None:
        """Update a risk limit value (runtime reconfiguration)."""
        if limit_type in self._limits:
            self._limits[limit_type].limit_value = new_value
            logger.info(f"Risk limit {limit_type.value} updated to {new_value}")

    def set_portfolio_value(self, value_usd: float) -> None:
        """Update the portfolio value reference."""
        self._portfolio_value = value_usd

    @property
    def approved_count(self) -> int:
        return self._approved_count

    @property
    def rejected_count(self) -> int:
        return self._rejected_count
