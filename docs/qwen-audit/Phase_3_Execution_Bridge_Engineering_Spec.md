# Phase 3: The Execution Bridge - Engineering Specification

**Phase:** 3 (Critical Priority)  
**Target System:** `karsa-execution-bridge`  
**Status:** Ready for Engineering Handoff  
**Dependencies:** Phase 2 (AI Governance) must be emitting `ThesisApprovedEvent` and `ThesisRejectedEvent`. Phase 1 (Data Bridge) must be providing live market state.

---

## 1. Objective & Scope

**The Problem:** Phase 2 successfully generates and validates AI trade theses. However, an approved thesis is just an *intent*. It is not a trade. Furthermore, LLMs cannot be trusted with hard quantitative risk limits (e.g., "Do not exceed $50,000 daily exposure").  
**The Solution:** Build the `karsa-execution-bridge`. This deterministic, highly resilient microservice acts as the "muscle" of the desk. It translates AI intents into broker-specific orders, enforces **hard quantitative risk limits**, manages order lifecycle (slicing, routing, tracking), and reports execution status back to the Karsa Event Store.

**Scope of Phase 3:**
- Build the Execution Event Listener to consume `ThesisApprovedEvent`.
- Implement a **Hard Pre-Trade Risk Engine** (quantitative limits, circuit breakers).
- Build the Order Management System (OMS) state machine and Order Slicer (basic TWAP/VWAP).
- Implement the Broker Adapter Factory (Interactive Brokers, Alpaca).
- Establish the feedback loop: Emitting `OrderSubmittedEvent`, `OrderFilledEvent`, and `ExecutionFailedEvent` back to the Karsa Event Store.

*Out of Scope for Phase 3:* High-Frequency Trading (HFT) low-latency optimizations, complex multi-leg options routing, and direct exchange FIX protocol implementation (we will use broker APIs for this phase).

---

## 2. High-Level Architecture

The Execution Bridge sits between the AI's "intent" and the actual market. It is strictly deterministic—no LLMs are involved in this phase.

```text
[KARSA EVENT STORE]
   │ (Topic: karsa.ai.thesis.approved)
   ▼
┌─────────────────────────────────────────────────────────────┐
│              `karsa-execution-bridge`                        │
│                                                             │
│  1. Event Listener (Consumes ThesisApprovedEvent)           │
│         │                                                   │
│         ▼                                                   │
│  2. Hard Pre-Trade Risk Engine                              │
│     (Checks: Max Position Size, Daily Turnover, Cash)       │
│         │ (If Pass)                                         │
│         ▼                                                   │
│  3. Order Slicer & State Machine (OMS)                      │
│     (Splits large orders into TWAP/VWAP child orders)       │
│         │                                                   │
│         ▼                                                   │
│  4. Broker Adapter Factory                                  │
│     (Routes to IBKR / Alpaca / Binance)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ (WebSockets / REST)
                            ▼
                     [EXTERNAL BROKER / EXCHANGE]
                            │ (Execution Reports)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Execution Feedback Loop                                 │
│     (Translates broker fills into Karsa events)             │
│     Emits: OrderSubmitted, OrderFilled, ExecutionFailed     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                 [KARSA EVENT STORE] -> (Updates PnL, UI, AI Memory)
```

---

## 3. Database Schema (Execution State)

The Execution Bridge maintains its own relational state in PostgreSQL to track the lifecycle of every order and fill. This is separate from the Karsa Event Store but synced via events.

```sql
-- 1. Master Order Ledger
CREATE TABLE execution_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thesis_id UUID NOT NULL, -- Links back to the AI's ThesisApprovedEvent
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL', 'SELL_SHORT')),
    target_quantity DECIMAL(18, 8) NOT NULL,
    filled_quantity DECIMAL(18, 8) DEFAULT 0,
    order_type VARCHAR(20) NOT NULL, -- 'MARKET', 'LIMIT', 'TWAP'
    limit_price DECIMAL(18, 8),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RISK_REJECTED', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'FAILED')),
    broker_order_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Execution Fills (The actual trades)
CREATE TABLE execution_fills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES execution_orders(id),
    broker_fill_id VARCHAR(100),
    quantity DECIMAL(18, 8) NOT NULL,
    fill_price DECIMAL(18, 8) NOT NULL,
    commission DECIMAL(18, 4) DEFAULT 0,
    filled_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Hard Risk Limits (Configurable by PMs)
CREATE TABLE execution_risk_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    limit_type VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'MAX_POSITION_SIZE_PCT', 'MAX_DAILY_TURNOVER_USD', 'MAX_SINGLE_ORDER_USD'
    limit_value DECIMAL(18, 4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);
```

---

## 4. Core Components

### 4.1 Hard Pre-Trade Risk Engine
*Crucial Rule: Never trust the LLM with hard money limits.* The Governance Agent (Phase 2) checks for logic and hallucinations. The Execution Bridge checks for **math and survival**.

```python
class HardRiskEngine:
    def __init__(self, db, portfolio_state):
        self.db = db
        self.portfolio = portfolio_state # In-memory cache of current cash/positions

    async def validate_order(self, thesis_event: ThesisApprovedEvent) -> tuple[bool, str]:
        order_value = thesis_event.quantity * thesis_event.current_price
        
        # 1. Check Max Single Order Size
        max_order_limit = await self.db.get_limit('MAX_SINGLE_ORDER_USD')
        if order_value > max_order_limit:
            return False, f"Order value ${order_value} exceeds max single order limit ${max_order_limit}"
            
        # 2. Check Max Position Size (Post-trade)
        current_pos = self.portfolio.get_position_value(thesis_event.symbol)
        new_pos = current_pos + order_value
        max_pos_limit = self.portfolio.total_equity * await self.db.get_limit('MAX_POSITION_SIZE_PCT')
        if new_pos > max_pos_limit:
            return False, f"Post-trade position ${new_pos} exceeds max position limit ${max_pos_limit}"
            
        # 3. Check Daily Turnover Circuit Breaker
        daily_turnover = await self.db.get_daily_turnover()
        if daily_turnover + order_value > await self.db.get_limit('MAX_DAILY_TURNOVER_USD'):
            return False, "Daily turnover circuit breaker triggered. Trading halted."
            
        return True, "Passed hard risk checks."
```

### 4.2 Broker Adapter Factory
Similar to Phase 1, we use a registry pattern to abstract the broker. This allows us to swap brokers or route to different brokers for different asset classes without changing core logic.

```python
# broker_registry.py
from typing import Dict, Type

BROKER_REGISTRY: Dict[str, Type['BaseBrokerAdapter']] = {}

def register_broker(broker_name: str):
    def decorator(cls: Type['BaseBrokerAdapter']):
        BROKER_REGISTRY[broker_name] = cls
        return cls
    return decorator

class BaseBrokerAdapter:
    async def connect(self): raise NotImplementedError
    async def place_order(self, symbol: str, side: str, qty: float, order_type: str, limit_price: float = None) -> str: 
        """Returns broker_order_id"""
        raise NotImplementedError
    async def cancel_order(self, broker_order_id: str): raise NotImplementedError

@register_broker("alpaca")
class AlpacaAdapter(BaseBrokerAdapter):
    async def place_order(self, symbol, side, qty, order_type, limit_price=None):
        # Implement Alpaca API logic here
        pass

@register_broker("interactive_brokers")
class IBKRAdapter(BaseBrokerAdapter):
    async def place_order(self, symbol, side, qty, order_type, limit_price=None):
        # Implement IBKR TWS API logic here
        pass
```

### 4.3 Order Slicer & State Machine (OMS)
If the AI approves a $100,000 order in a low-liquidity stock, sending a single market order will cause massive slippage. The OMS slices the order.

```python
class OrderManagementSystem:
    async def process_approved_thesis(self, thesis: ThesisApprovedEvent):
        # 1. Save to DB
        order = await self.db.create_order(thesis)
        
        # 2. Determine Slicing Strategy
        if order.target_quantity * order.current_price > 50000:
            # Slice into 5-minute TWAP (Time-Weighted Average Price)
            child_orders = self.slice_twap(order, duration_minutes=30)
        else:
            # Send as single Limit Order
            child_orders = [order]
            
        # 3. Route to Broker
        for child in child_orders:
            broker_id = await self.broker.place_order(...)
            child.broker_order_id = broker_id
            await self.emit_event(OrderSubmittedEvent(order_id=child.id))
```

---

## 5. The Feedback Loop (Closing the Architecture)

The Execution Bridge must not be a black box. Every time the broker reports a status change, the bridge translates it into a Karsa event and pushes it back to the Event Store. This allows the `karsa-projection-worker` to update the UI, and the AI agents to update their PnL.

### 5.1 Handling Broker WebSockets
```python
async def on_broker_fill_report(broker_fill_data: dict):
    # 1. Record fill in local DB
    await db.record_fill(broker_fill_data)
    
    # 2. Update local portfolio state cache
    portfolio.update_fill(broker_fill_data)
    
    # 3. Emit to Karsa Event Store
    fill_event = OrderFilledEvent(
        order_id=broker_fill_data['order_id'],
        quantity=broker_fill_data['qty'],
        fill_price=broker_fill_data['price'],
        timestamp=broker_fill_data['time']
    )
    await karsa_event_bus.publish("karsa.execution.fill", fill_event)
```

### 5.2 Handling Execution Failures
If an order is rejected by the broker (e.g., insufficient margin, market halted), the bridge must emit a failure event so the AI doesn't wait forever for a fill.

```python
async def on_broker_rejection(broker_reject_data: dict):
    await db.update_order_status(broker_reject_data['order_id'], 'FAILED')
    
    fail_event = ExecutionFailedEvent(
        order_id=broker_reject_data['order_id'],
        reason=broker_reject_data['error_message']
    )
    await karsa_event_bus.publish("karsa.execution.failed", fail_event)
```

---

## 6. Security & Operational Safeguards

Because this component has direct access to capital, it requires strict operational safeguards:

1.  **Idempotency:** The Execution Bridge must track `thesis_id`. If a duplicate `ThesisApprovedEvent` is received from the message broker (due to network retries), the bridge must ignore it to prevent double-ordering.
2.  **Kill Switch:** The bridge must listen to a special Redis/Kafka topic: `karsa.system.kill_switch`. If a PM publishes a `HALT` message to this topic, the bridge must immediately cancel all open orders and stop accepting new theses.
3.  **Paper Trading Mode:** The `execution_risk_limits` table must include a `mode` column (`LIVE` vs `PAPER`). In `PAPER` mode, the Broker Adapter simulates fills locally without sending orders to the exchange.

---

## 7. Definition of Done (Acceptance Criteria)

Phase 3 is considered complete and ready for Phase 4 when:

- [ ] **Event Consumption:** The bridge successfully consumes `ThesisApprovedEvent` and creates a record in `execution_orders`.
- [ ] **Hard Risk Checks:** The bridge correctly rejects an order that exceeds the `MAX_SINGLE_ORDER_USD` limit and emits a `RiskRejected` status.
- [ ] **Broker Integration:** The `AlpacaAdapter` (or `IBKRAdapter`) successfully places a live (or paper) order and receives a confirmation.
- [ ] **Feedback Loop:** When the broker reports a fill, the bridge successfully emits an `OrderFilledEvent` to the Karsa Event Store.
- [ ] **Kill Switch:** Publishing a `HALT` message to the kill switch topic immediately cancels all open orders and halts the worker.
- [ ] **Idempotency:** Sending the exact same `ThesisApprovedEvent` twice results in only one order being placed.

---

## 8. Engineering Handoff & Next Steps

1. **DevOps:** Provision the `execution_orders` and `execution_fills` tables. Set up the broker API credentials in the secrets manager.
2. **Backend:** Scaffold the `karsa-execution-bridge` Python project. Implement the `HardRiskEngine` and write unit tests for the mathematical limits.
3. **Backend:** Implement the `AlpacaAdapter` (recommended for MVP due to excellent API/docs) and the `OrderManagementSystem`.
4. **QA:** Run the system in **Paper Trading Mode**. Feed it 100 random `ThesisApprovedEvent` messages and verify that the risk engine correctly slices orders, respects limits, and handles simulated rejections.
5. **Integration:** Verify that the `karsa-projection-worker` correctly reads the `OrderFilledEvent` and updates the CIO Dashboard PnL in real-time.
```