# Phase 4: Live Risk Calibration & CIO Dashboards - Engineering Specification

**Phase:** 4 (Final Production Phase)  
**Target Systems:** `karsa-risk-calibration-engine`, `karsa-cio-producer`, `karsa-web` (CIO Dashboard)  
**Status:** Ready for Engineering Handoff  
**Dependencies:** Phase 3 (Execution Bridge) must be emitting `OrderFilledEvent` and `OrderCancelledEvent`. Phase 1 (Data Bridge) must be emitting live `NormalizedAggregatedBar`.

---

## 1. Objective & Scope

**The Problem:** Phase 3 successfully executes trades, but the desk is flying blind at the portfolio level. We have individual trade fills, but we lack real-time, portfolio-wide risk metrics (Value at Risk, Gross/Net Exposure, Sector Concentration). Furthermore, the initial position sizing was static; it does not adapt to changing market volatility.  
**The Solution:** Implement the **Live Risk Calibration Engine** to dynamically size positions based on real-time volatility, and build the **`karsa-cio-producer`** to aggregate all desk activity into a real-time, executive-level CIO Dashboard.

**Scope of Phase 4:**
- Build the Volatility Targeting & Position Sizing algorithms.
- Implement Portfolio-level Risk Metrics (VaR, Drawdown, Factor Exposures).
- Build the `karsa-cio-producer` worker to aggregate event streams into time-series read-models.
- Finalize the Next.js CIO Dashboard backend APIs and real-time WebSocket feeds.

*Out of Scope for Phase 4:* Multi-asset class optimization (Mean-Variance), high-frequency microstructure risk, and automated macro-hedging.

---

## 2. High-Level Architecture

Phase 4 shifts the system from "micro" (individual trade execution) to "macro" (portfolio oversight).

```text
[KARSA EVENT STORE]
   │ (Topics: karsa.execution.fill, karsa.market.bar, karsa.ai.thesis.approved)
   ▼
┌─────────────────────────────────────────────────────────────┐
│              `karsa-cio-producer` (The Aggregator)           │
│                                                             │
│  1. Consumes Fills & Market Bars                            │
│  2. Updates Portfolio State (Cash, Positions, PnL)          │
│  3. Calculates Time-Series Metrics (Gross/Net, Drawdown)    │
│  4. Writes to Read-Model DB (TimescaleDB / Postgres)        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              `karsa-risk-calibration-engine`                 │
│                                                             │
│  1. Consumes `karsa.market.bar`                             │
│  2. Calculates Rolling Volatility (EWMA / GARCH)            │
│  3. Updates `asset_volatility` table                        │
│  4. Intercepts `ThesisApprovedEvent` to apply Vol-Scaling   │
│     BEFORE passing to Execution Bridge                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              CIO Dashboard API (FastAPI)                     │
│                                                             │
│  1. Serves REST endpoints for historical charts             │
│  2. Pushes real-time updates via WebSockets to Next.js UI   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema (Risk & Read-Models)

We will use **TimescaleDB** (a PostgreSQL extension) for the read-models, as it is optimized for time-series financial data (OHLCV, PnL curves) while maintaining SQL compatibility.

```sql
-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Asset Volatility & Risk Metrics (Updated by Calibration Engine)
CREATE TABLE asset_risk_metrics (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL, -- '1D', '1W'
    realized_volatility DECIMAL(10, 6) NOT NULL, -- Annualized %
    beta_to_spy DECIMAL(10, 4),
    var_95 DECIMAL(18, 4), -- 95% 1-Day Value at Risk in USD
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timeframe)
);

-- 2. Portfolio Snapshots (Time-Series for CIO Dashboard Charts)
CREATE TABLE portfolio_snapshots (
    snapshot_time TIMESTAMPTZ NOT NULL,
    total_equity DECIMAL(18, 4) NOT NULL,
    cash_balance DECIMAL(18, 4) NOT NULL,
    gross_exposure DECIMAL(18, 4) NOT NULL,
    net_exposure DECIMAL(18, 4) NOT NULL,
    daily_pnl DECIMAL(18, 4) NOT NULL,
    max_drawdown_pct DECIMAL(10, 4) NOT NULL
);
SELECT create_hypertable('portfolio_snapshots', 'snapshot_time');

-- 3. Sector / Factor Exposures
CREATE TABLE sector_exposures (
    snapshot_time TIMESTAMPTZ NOT NULL,
    sector_name VARCHAR(50) NOT NULL, -- e.g., 'Technology', 'Energy'
    gross_exposure DECIMAL(18, 4) NOT NULL,
    net_exposure DECIMAL(18, 4) NOT NULL
);
SELECT create_hypertable('sector_exposures', 'snapshot_time');
```

---

## 4. Core Component 1: Live Risk Calibration Engine

The AI (Phase 2) suggests a position size based on conviction. The Risk Engine overrides this size based on **realized market volatility** to ensure every trade contributes an equal amount of risk to the portfolio (Volatility Targeting).

### 4.1 Volatility Calculation (Exponentially Weighted Moving Average)
```python
import numpy as np
import pandas as pd

class VolatilityCalculator:
    def __init__(self, span_days: int = 20):
        self.span = span_days

    def calculate_ewma_vol(self, returns_series: pd.Series) -> float:
        """Calculates annualized EWMA volatility."""
        ewma_var = returns_series.ewm(span=self.span).var().iloc[-1]
        daily_vol = np.sqrt(ewma_var)
        # Annualize (assuming 252 trading days)
        annualized_vol = daily_vol * np.sqrt(252) 
        return annualized_vol
```

### 4.2 Volatility-Targeted Position Sizing
When a `ThesisApprovedEvent` arrives, the Risk Engine intercepts it and scales the quantity.

```python
class RiskCalibrationEngine:
    def __init__(self, target_risk_per_trade_usd: float = 10000.0):
        self.target_risk = target_risk_per_trade_usd # e.g., risk exactly $10k per trade

    async def scale_position_size(self, thesis: ThesisApprovedEvent, current_price: float, annualized_vol: float) -> int:
        # 1. Calculate 1-day standard deviation of the price
        daily_vol_pct = annualized_vol / np.sqrt(252)
        daily_price_vol = current_price * daily_vol_pct
        
        # 2. Calculate how many shares equal our target risk
        # Formula: Target Risk $ / (Price * Daily Vol %)
        raw_shares = self.target_risk / daily_price_vol
        
        # 3. Apply hard caps (Never exceed AI's max suggested size or desk limits)
        final_shares = min(raw_shares, thesis.max_allowed_shares)
        
        # 4. Update the thesis event with the calibrated size
        thesis.calibrated_quantity = int(final_shares)
        thesis.risk_scaling_applied = True
        return thesis
```

---

## 5. Core Component 2: The `karsa-cio-producer`

The CIO Producer is the "accountant" of the system. It listens to the raw event stream and maintains the materialized view of the portfolio for the UI.

### 5.1 Event Consumption & State Updates
```python
class CIOProducer:
    def __init__(self, db, event_bus):
        self.db = db
        self.event_bus = event_bus
        self.portfolio_state = PortfolioState() # In-memory cache

    async def start(self):
        await self.event_bus.subscribe("karsa.execution.fill", self.on_fill)
        await self.event_bus.subscribe("karsa.market.bar", self.on_market_bar)

    async def on_fill(self, event: OrderFilledEvent):
        # 1. Update in-memory state
        self.portfolio_state.process_fill(event)
        
        # 2. Recalculate exposures
        gross, net = self.portfolio_state.calculate_exposures()
        sector_map = self.portfolio_state.calculate_sector_exposures()
        
        # 3. Persist to TimescaleDB for the dashboard
        await self.db.insert_portfolio_snapshot(
            total_equity=self.portfolio_state.equity,
            gross_exposure=gross,
            net_exposure=net
        )
        await self.db.insert_sector_exposures(sector_map)
        
        # 4. Push real-time update to UI via WebSocket
        await self.ws_manager.broadcast("portfolio_update", {...})

    async def on_market_bar(self, event: NormalizedAggregatedBar):
        # Mark-to-market: Update the value of open positions based on the latest bar close
        self.portfolio_state.mark_to_market(event.symbol, event.close)
```

---

## 6. CIO Dashboard API & Frontend Integration

The Next.js frontend (`karsa-web/`) requires fast, read-optimized endpoints to render the AG Grids and Recharts/TradingView charts.

### 6.1 FastAPI Endpoints
```python
# cio_api.py
from fastapi import APIRouter, Depends
from fastapi.websockets import WebSocket

router = APIRouter(prefix="/api/cio", tags=["CIO Dashboard"])

@router.get("/portfolio/summary")
async def get_portfolio_summary():
    """Returns current equity, cash, gross/net exposure, and daily PnL."""
    return await db.get_latest_portfolio_snapshot()

@router.get("/portfolio/equity-curve")
async def get_equity_curve(timeframe: str = "1D"):
    """Returns time-series data for the equity curve chart."""
    return await db.get_portfolio_snapshots_history(timeframe)

@router.get("/exposures/sectors")
async def get_sector_exposures():
    """Returns current gross/net exposure by GICS sector."""
    return await db.get_latest_sector_exposures()

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time push for trade fills and PnL updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, push updates from CIO Producer
            data = await manager.receive() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### 6.2 Frontend UI Requirements (Next.js)
- **Top Banner:** Real-time Total Equity, Daily PnL (Green/Red), Gross/Net Exposure percentages.
- **Main Chart:** Interactive Equity Curve (using TradingView Lightweight Charts or Recharts) pulling from `/portfolio/equity-curve`.
- **Exposure Grid:** AG Grid showing Sector, Gross Exposure, Net Exposure, and Beta.
- **Risk Gauges:** Visual speedometers for Portfolio VaR and Max Drawdown.

---

## 7. Security & Operational Safeguards

1.  **Stale Data Circuit Breaker:** If the `karsa-cio-producer` stops receiving `karsa.market.bar` events for more than 5 minutes during market hours, it must flag the dashboard as "STALE DATA" and halt any new order approvals to prevent trading on outdated prices.
2.  **Read-Replica Routing:** The CIO Dashboard API should route all `GET` requests to a PostgreSQL Read Replica to ensure heavy analytical queries do not slow down the core transactional Event Store.
3.  **Audit Trail:** Every time the Risk Calibration Engine overrides the AI's suggested position size, it must emit a `RiskScalingAppliedEvent` to the Event Store so the PM can audit *why* a trade was sized smaller than the AI requested.

---

## 8. Definition of Done (Acceptance Criteria)

Phase 4 is considered complete and the system is ready for Live Production when:

- [ ] **Volatility Scaling:** The Risk Engine successfully intercepts a thesis, calculates the asset's 20-day EWMA volatility, and scales the position size to match the target risk parameter.
- [ ] **CIO Aggregation:** The `karsa-cio-producer` correctly consumes `OrderFilledEvent` and updates the `portfolio_snapshots` TimescaleDB table within 500ms.
- [ ] **Dashboard Rendering:** The Next.js CIO Dashboard successfully renders the Equity Curve, Gross/Net exposure, and Sector heatmaps using the new API endpoints.
- [ ] **Real-Time Updates:** When a simulated fill occurs, the CIO Dashboard updates the Total Equity and Daily PnL via WebSocket without requiring a page refresh.
- [ ] **Stale Data Protection:** Disconnecting the Phase 1 Data Bridge correctly triggers the "STALE DATA" warning on the CIO Dashboard and halts the Execution Bridge.

---

## 9. Engineering Handoff & Next Steps

1. **DevOps:** Install and configure the TimescaleDB extension on the PostgreSQL instance. Set up read-replicas for the CIO API.
2. **Quant/Backend:** Implement the `VolatilityCalculator` and `RiskCalibrationEngine`. Backtest the volatility scaling logic against historical data to ensure the target risk parameters are calibrated correctly.
3. **Backend:** Build the `karsa-cio-producer` worker, ensuring it handles high-throughput event consumption without lagging.
4. **Frontend:** Connect the Next.js CIO Dashboard to the new FastAPI endpoints and WebSockets. Implement the AG Grid configurations for the exposure tables.
5. **QA / Go-Live:** Run the entire system (Phases 1 through 4) in **Paper Trading Mode** for 2 weeks. Verify that the CIO Dashboard accurately reflects the simulated PnL, and that the Risk Engine correctly scales positions during simulated high-volatility market events.
```