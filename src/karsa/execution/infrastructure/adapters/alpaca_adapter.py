"""Alpaca Markets Broker Adapter — Sprint-57.

Implements BrokerAdapterPort for Alpaca Markets API.
Supports paper trading and live trading endpoints.
Places orders via REST, receives fills via WebSocket.
"""
import logging
from typing import Any, Dict, Optional

import httpx

from karsa.execution.application.bridge_services import register_broker_adapter

logger = logging.getLogger(__name__)

# Alpaca API endpoints
ALPACA_LIVE_URL = "https://api.alpaca.markets"
ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"


@register_broker_adapter("alpaca")
class AlpacaAdapter:
    """Alpaca Markets broker adapter.

    Implements the BrokerAdapterPort interface for order placement
    and management via Alpaca's REST API.
    """

    def __init__(
        self,
        credentials: Dict[str, str],
        paper_trading: bool = True,
    ):
        self._api_key = credentials.get("api_key", "")
        self._api_secret = credentials.get("api_secret", "")
        self._base_url = ALPACA_PAPER_URL if paper_trading else ALPACA_LIVE_URL
        self._client: Optional[httpx.AsyncClient] = None
        self._paper_trading = paper_trading
        self.broker_id = "alpaca"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "APCA-API-KEY-ID": self._api_key,
                    "APCA-API-SECRET-KEY": self._api_secret,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def connect(self) -> bool:
        """Verify connection to Alpaca API."""
        try:
            client = await self._get_client()
            resp = await client.get("/v2/account")
            resp.raise_for_status()
            account = resp.json()
            logger.info(
                f"Alpaca connected ({'paper' if self._paper_trading else 'live'}): "
                f"buying_power=${float(account.get('buying_power', 0)):,.2f}"
            )
            return True
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return False

    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Place an order via Alpaca REST API.

        Args:
            symbol: Ticker symbol.
            quantity: Number of shares.
            side: "buy" or "sell".
            order_type: "market" or "limit".
            limit_price: Limit price (required for limit orders).
            time_in_force: "day", "gtc", "ioc", "fok".

        Returns:
            Dict with broker_order_id, status, submitted_at.
        """
        client = await self._get_client()

        body = {
            "symbol": symbol,
            "qty": str(quantity),
            "side": side.lower(),
            "type": order_type.lower(),
            "time_in_force": time_in_force,
        }
        if limit_price and order_type.lower() == "limit":
            body["limit_price"] = str(limit_price)

        try:
            resp = await client.post("/v2/orders", json=body)
            resp.raise_for_status()
            data = resp.json()

            result = {
                "broker_order_id": data["id"],
                "status": data["status"],
                "submitted_at": data.get("submitted_at", ""),
            }
            logger.info(
                f"Alpaca order placed: {symbol} {side} {quantity} "
                f"(id={data['id']}, status={data['status']})"
            )
            return result

        except httpx.HTTPStatusError as e:
            error_msg = e.response.text
            logger.error(f"Alpaca order rejected: {e.response.status_code} — {error_msg}")
            raise RuntimeError(f"Alpaca order rejected: {error_msg}")
        except Exception as e:
            logger.error(f"Alpaca order error: {e}")
            raise

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order by broker order ID."""
        client = await self._get_client()
        try:
            resp = await client.delete(f"/v2/orders/{broker_order_id}")
            resp.raise_for_status()
            logger.info(f"Alpaca order cancelled: {broker_order_id}")
            return True
        except Exception as e:
            logger.error(f"Alpaca cancel failed for {broker_order_id}: {e}")
            return False

    async def get_order_status(self, broker_order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status from Alpaca."""
        client = await self._get_client()
        try:
            resp = await client.get(f"/v2/orders/{broker_order_id}")
            resp.raise_for_status()
            data = resp.json()
            return {
                "broker_order_id": data["id"],
                "status": data["status"],
                "filled_qty": float(data.get("filled_qty", 0)),
                "filled_avg_price": float(data.get("filled_avg_price", 0)),
            }
        except Exception as e:
            logger.error(f"Alpaca status check failed for {broker_order_id}: {e}")
            return None

    async def get_positions(self) -> list:
        """Get all current positions."""
        client = await self._get_client()
        try:
            resp = await client.get("/v2/positions")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Alpaca positions fetch failed: {e}")
            return []

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

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
            loop = asyncio.get_running_loop()
            # Already in async context — schedule coroutine
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    self.place_order(
                        symbol=symbol,
                        quantity=quantity,
                        side=direction.lower(),
                        order_type=order_type.lower(),
                        limit_price=price,
                    )
                ).result()
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
