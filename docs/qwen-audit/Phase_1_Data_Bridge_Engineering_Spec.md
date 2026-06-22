# Phase 1: The Data Bridge - Engineering Specification

**Phase:** 1 (Critical Priority)  
**Target System:** `karsa-data-ingestion-worker`  
**Status:** Ready for Engineering Handoff  
**Author:** Lead Systems Architect  

---

## 1. Objective & Scope

**The Problem:** Karsa’s AI orchestration layer is currently "blind" to the real world. It lacks functional integrations for real-time market data, news feeds, or alternative data.  
**The Solution:** Build the `karsa-data-ingestion-worker` (The Data Bridge). This standalone worker will fetch external data, normalize it, aggregate it, and push it into the Karsa Event Store. 

**Scope of Phase 1:**
- Implement a database-driven provider management system (PostgreSQL).
- Build the Connector Factory and Normalization Engine.
- Implement the Aggregation Engine (converting raw ticks to OHLCV bars).
- Establish the Event Emission pipeline to the Karsa Message Broker.
- Implement zero-downtime hot-reloading and health monitoring.

*Out of Scope for Phase 1:* AI Agent consumption (Phase 2), Execution routing (Phase 3), and UI projection updates (handled by existing `karsa-projection-worker` once data flows).

---

## 2. High-Level Architecture

The Data Bridge strictly separates **Data Ingestion (Fast/Dumb)** from **Data Reasoning (Slow/Smart)**.

```text
[PostgreSQL: Provider Config & Credentials] 
        │ (Reads & Watches via LISTEN/NOTIFY)
        ▼
┌─────────────────────────────────────────────────────────────┐
│              `karsa-data-ingestion-worker`                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Config Mgr  │→ │ Connector    │→ │ Normalization      │  │
│  │ (Hot-Reload)│  │ Factory      │  │ Engine (Pydantic)  │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Health      │← │ Aggregation  │← │ Raw Tick Buffer    │  │
│  │ Monitor     │  │ Engine       │  │ (In-Memory)        │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Event Emitter (Publishes to Kafka/Redis/Postgres Bus)   ││
│  └─────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────┘
                            │ 
                            ▼
                 [KARSA EVENT STORE / MESSAGE BROKER]
                 Topics: karsa.market.bar, karsa.news.article
```

---

## 3. Database Schema & Security

All provider metadata is stored in PostgreSQL. This allows Portfolio Managers or Quants to add new data feeds, rotate API keys, or pause feeds via an admin UI without requiring engineering deployments.

### 3.1 Core Tables

```sql
-- 1. Provider Registry
CREATE TABLE data_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'polygon', 'finnhub'
    type VARCHAR(20) NOT NULL CHECK (type IN ('market_tick', 'market_bar', 'news', 'sentiment')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'maintenance')),
    priority INT DEFAULT 100, -- Lower number = higher priority for failover
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Encrypted Credentials
CREATE TABLE provider_credentials (
    provider_id UUID PRIMARY KEY REFERENCES data_providers(id) ON DELETE CASCADE,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT,
    key_rotation_version INT DEFAULT 1,
    expires_at TIMESTAMPTZ
);

-- 3. Dynamic Configuration (JSONB)
CREATE TABLE provider_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES data_providers(id) ON DELETE CASCADE,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    UNIQUE(provider_id, config_key)
);
-- Example config_value: {"symbols": ["AAPL", "SPY"], "aggregation_window": "1m"}

-- 4. Health & Uptime Tracking
CREATE TABLE provider_health_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES data_providers(id),
    status VARCHAR(20) CHECK (status IN ('connected', 'disconnected', 'rate_limited', 'auth_error')),
    error_message TEXT,
    latency_ms INT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 Security Protocol
- **Encryption at Rest:** All API keys in `provider_credentials` must be encrypted using **AES-256-GCM**.
- **Master Key:** The decryption key is injected strictly via environment variable (`DATA_BRIDGE_MASTER_KEY`) at runtime.
- **Rule:** Credentials must *never* be logged, cached in plaintext in memory longer than necessary, or exposed in API responses.

---

## 4. Core Worker Components

### 4.1 Config Manager & Zero-Downtime Hot-Reload
The Config Manager loads active providers on startup and listens for database changes to swap connectors without dropping the WebSocket connections.

**Database Trigger for Hot-Reload:**
```sql
CREATE OR REPLACE FUNCTION notify_provider_config_change() RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('provider_config_updated', NEW.provider_id::TEXT);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER config_change_trigger
AFTER INSERT OR UPDATE ON provider_configurations
FOR EACH ROW EXECUTE FUNCTION notify_provider_config_change();
```

**Hot-Reload Flow (Blue/Green Swap):**
1. Worker receives `provider_config_updated` notification.
2. Spawns new connector instance (**Blue**) with the new config/key.
3. Validates the Blue connection (e.g., sends a test ping to Polygon).
4. If successful, gracefully drains and stops the old connector (**Green**).
5. Replaces Green with Blue in the active registry.

### 4.2 Connector Factory Pattern
We use a Registry pattern to map database provider names to specific Python classes.

```python
# connector_registry.py
from typing import Dict, Type
from uuid import UUID

CONNECTOR_REGISTRY: Dict[str, Type['BaseConnector']] = {}

def register_connector(provider_name: str):
    def decorator(cls: Type['BaseConnector']):
        CONNECTOR_REGISTRY[provider_name] = cls
        return cls
    return decorator

class BaseConnector:
    def __init__(self, provider_id: UUID, config: dict, credentials: dict):
        self.provider_id = provider_id
        self.config = config
        self.credentials = credentials

    async def start(self): raise NotImplementedError
    async def stop(self): raise NotImplementedError

@register_connector("polygon")
class PolygonConnector(BaseConnector):
    async def start(self):
        # Initialize polygon WebSocket client
        pass

@register_connector("finnhub")
class FinnhubConnector(BaseConnector):
    async def start(self):
        # Initialize finnhub REST polling client
        pass
```

### 4.3 Normalization Engine (Pydantic V2)
The Normalization Engine translates vendor-specific JSON into strict, unified Pydantic models. Downstream AI agents will *only* ever see these models.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class EventType(str, Enum):
    MARKET_TICK = "MARKET_TICK"
    MARKET_BAR = "MARKET_BAR"
    NEWS_ARTICLE = "NEWS_ARTICLE"

class NormalizedMarketTick(BaseModel):
    event_type: EventType = Field(default=EventType.MARKET_TICK)
    symbol: str
    price: float
    volume: int
    timestamp_utc: datetime
    source_provider: str

class NormalizedAggregatedBar(BaseModel):
    event_type: EventType = Field(default=EventType.MARKET_BAR)
    symbol: str
    timeframe: str  # "1m", "5m", "1h"
    open: float
    high: float
    low: float
    close: float
    volume: int
    bar_close_utc: datetime
    source_provider: str

class NormalizedNewsEvent(BaseModel):
    event_type: EventType = Field(default=EventType.NEWS_ARTICLE)
    headline: str
    url: str
    tickers: List[str]
    sentiment_score: Optional[float] = None
    published_at: datetime
    source_provider: str
```

### 4.4 Aggregation Engine (Ticks to Bars)
Streaming raw millisecond ticks to an LLM is a critical anti-pattern that will exhaust token budgets. The Aggregation Engine buffers ticks in memory and emits standardized OHLCV bars.

**Implementation Rules:**
1. **Buffering:** Maintain an in-memory dictionary keyed by `symbol` and `timeframe` (e.g., `AAPL_1m`).
2. **Calculation:** When the 1-minute window closes, calculate Open, High, Low, Close, and Volume.
3. **Emission:** Emit a `NormalizedAggregatedBar` event and clear the buffer for that symbol.
4. **Gap Filling:** If the WebSocket disconnects for 3 minutes, the worker must use the vendor's REST API to fetch the missing historical bars before resuming live streaming.

### 4.5 Event Emitter
Once data is normalized and aggregated, it is published to the Karsa message broker.

```python
# event_emitter.py
async def emit_to_karsa(event: BaseModel):
    payload = event.model_dump(mode="json")
    
    # Route to specific topics based on event type
    if event.event_type == EventType.MARKET_BAR:
        topic = "karsa.market.bar"
    elif event.event_type == EventType.NEWS_ARTICLE:
        topic = "karsa.news.article"
    else:
        topic = "karsa.market.raw" # Only consumed by internal aggregation engine
        
    await karsa_event_bus.publish(topic=topic, payload=payload)
```

---

## 5. Health Monitoring & Failover

The Health Monitor runs as a background `asyncio.Task` within the worker to ensure 99.99% uptime.

### 5.1 Metrics Tracked
- **Connection State:** Connected, Disconnected, Reconnecting.
- **Rate Limits:** Tracking `X-RateLimit-Remaining` headers from REST APIs.
- **Latency:** Time delta between the vendor's timestamp and the worker's ingestion timestamp.

### 5.2 Automatic Failover Logic
If the Health Monitor detects an `auth_error` or `rate_limited` state for a primary provider (e.g., Polygon):
1. Log the failure to `provider_health_logs`.
2. Query the DB for another active provider of the same `type` with a higher `priority` (lower number).
3. If a fallback exists, automatically spin it up and route traffic to it.
4. Send an alert to the engineering Slack channel: *"Primary feed [Polygon] failed. Fallback to [Alpaca] initiated."*

---

## 6. Definition of Done (Acceptance Criteria)

Phase 1 is considered complete and ready for Phase 2 when the following criteria are met:

- [ ] **Database:** All 4 core tables are created in PostgreSQL. AES-256 encryption/decryption for API keys is verified.
- [ ] **Hot-Reload:** Updating a row in `provider_configurations` triggers a Blue/Green connector swap without dropping the main event loop.
- [ ] **Market Data:** The `PolygonConnector` successfully connects, receives live ticks, and the Aggregation Engine correctly emits `karsa.market.bar` (1m OHLCV) events to the message broker.
- [ ] **News Data:** The `FinnhubConnector` successfully polls for news, filters out low-impact noise, and emits `karsa.news.article` events.
- [ ] **Resilience:** Simulating a network drop results in the worker auto-reconnecting and gap-filling missing 1m bars via REST API.
- [ ] **Observability:** Connection statuses and errors are accurately logging to `provider_health_logs`.

---

## 7. Engineering Handoff & Next Steps

1. **DevOps:** Provision PostgreSQL instance and apply the schema migrations. Set up the `DATA_BRIDGE_MASTER_KEY` in the secrets manager.
2. **Backend:** Scaffold the `karsa-data-ingestion-worker` Python project. Implement the `Config Manager` and `Connector Factory`.
3. **Backend:** Implement `PolygonConnector` and the `Aggregation Engine`.
4. **QA:** Write unit tests for the Normalization Engine (handling missing bids, timezone drift, string-to-float coercion).
5. **Integration:** Verify that emitted events are successfully landing in the Karsa Event Store/Kafka topics.
```