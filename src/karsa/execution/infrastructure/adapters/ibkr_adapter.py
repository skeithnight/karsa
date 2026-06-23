"""Interactive Brokers Adapter — Sprint-57 (Stubbed).

Implements BrokerAdapterPort for IBKR TWS API.
Stubbed until TWS gateway is available for integration testing.
"""
import logging
from typing import Any, Dict, Optional

from karsa.execution.application.bridge_services import register_broker_adapter

logger = logging.getLogger(__name__)


@register_broker_adapter("ibkr")
class IBKRAdapter:
    """Interactive Brokers TWS adapter (stubbed).

    Production implementation requires ibapi library and TWS gateway.
    Currently returns mock responses for paper trading validation.
    """

    def __init__(self, credentials: Dict[str, str], paper_trading: bool = True):
        self._host = credentials.get("host", "127.0.0.1")
        self._port = int(credentials.get("port", "7497"))  # 7497=paper, 7496=live
        self._client_id = int(credentials.get("client_id", "1"))
        self._paper_trading = paper_trading
        self.broker_id = "ibkr"
        self._connected = False

    async def connect(self) -> bool:
        """Connect to TWS gateway (stubbed)."""
        logger.info(f"IBKR adapter stubbed — would connect to {self._host}:{self._port}")
        self._connected = True
        return True

    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place an order via TWS (stubbed)."""
        logger.info(
            f"IBKR stub: would place {side} {quantity} {symbol} "
            f"({order_type}) on {'paper' if self._paper_trading else 'live'}"
        )
        # Return mock response
        import uuid
        mock_id = f"ibkr-{uuid.uuid4().hex[:8]}"
        return {
            "broker_order_id": mock_id,
            "status": "accepted",
            "submitted_at": "",
        }

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order (stubbed)."""
        logger.info(f"IBKR stub: would cancel {broker_order_id}")
        return True

    async def close(self) -> None:
        """Disconnect from TWS (stubbed)."""
        self._connected = False
        logger.info("IBKR adapter disconnected")

    # BrokerAdapterPort compatibility
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
        """Synchronous wrapper for BrokerAdapterPort compatibility."""
        import asyncio
        try:
            result = asyncio.run(
                self.place_order(
                    symbol=symbol,
                    quantity=quantity,
                    side=direction.lower(),
                    order_type=order_type.lower(),
                    limit_price=price,
                )
            )
            return {
                "broker_id": self.broker_id,
                "broker_order_ref": result["broker_order_id"],
                "status": "SENT",
            }
        except Exception as e:
            return {
                "broker_id": self.broker_id,
                "broker_order_ref": None,
                "status": "REJECTED",
                "error_message": str(e),
            }
