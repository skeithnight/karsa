"""IDX (Indonesia Stock Exchange) Broker Adapter — Mock.

Implements BrokerAdapterPort for IDX order routing.
Mock implementation for paper trading and integration testing.
Quantity is expressed in lots (1 lot = 100 shares).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from karsa.execution.application.bridge_services import register_broker_adapter

logger = logging.getLogger(__name__)

# IDX lot sizing constant
IDX_LOT_SIZE = 100


@register_broker_adapter("idx")
class IDXAdapter:
    """IDX broker adapter (mock).

    Simulates order routing to the Indonesia Stock Exchange.
    Quantity is interpreted as lots (1 lot = 100 shares) and converted
    to shares internally. All orders are accepted unless quantity <= 0.
    """

    def __init__(self, credentials: Dict[str, str], **kwargs: Any) -> None:
        self._api_key = credentials.get("api_key", "")
        self._api_secret = credentials.get("api_secret", "")
        self._client_id = credentials.get("client_id", "karsa-idx")
        self.broker_id = "idx"
        self._fill_log: List[Dict[str, Any]] = []

    def route_order(
        self,
        execution_id: str,
        symbol: str,
        quantity: float,
        direction: str,
        order_type: str,
        price: Optional[float] = None,
        pep_token_signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route an order to the IDX exchange (mock).

        Args:
            execution_id: Karsa execution order ID.
            symbol: Ticker symbol (e.g. "BBCA.JK").
            quantity: Order quantity in lots (1 lot = 100 shares).
            direction: "BUY" or "SELL".
            order_type: Order type (e.g. "MARKET", "LIMIT").
            price: Limit price (optional).
            pep_token_signature: PEP validation token (unused in mock).

        Returns:
            Dict with broker_id, broker_order_ref, status, and optional error_message.
        """
        # Validate quantity
        if quantity <= 0:
            return {
                "broker_id": self.broker_id,
                "broker_order_ref": None,
                "status": "REJECTED",
                "error_message": f"Invalid quantity: {quantity}. Must be positive lots.",
            }

        # Convert lots to shares for logging
        shares = quantity * IDX_LOT_SIZE
        broker_order_ref = f"idx_ord_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"IDX mock: routed {direction} {quantity} lots ({shares} shares) "
            f"of {symbol} ({order_type}) — ref={broker_order_ref}"
        )

        # Record in fill log
        fill_record = {
            "execution_id": execution_id,
            "broker_order_ref": broker_order_ref,
            "symbol": symbol,
            "lots": quantity,
            "shares": shares,
            "direction": direction,
            "order_type": order_type,
            "price": price,
            "routed_at": datetime.now(timezone.utc).isoformat(),
            "status": "SENT",
        }
        self._fill_log.append(fill_record)

        return {
            "broker_id": self.broker_id,
            "broker_order_ref": broker_order_ref,
            "status": "SENT",
        }
