# Data Bridge Production Audit

**Auditor:** Senior Quantitative Systems Architect
**Date:** 2026-06-22
**Scope:** Full pipeline from vendor connection to event emission (`src/karsa/providers/`)
**Methodology:** Line-by-line review of 16 source files across Sprints 51-53

---

## 1. Executive Summary

**Verdict: Solid architectural skeleton, NOT production-ready.** The Data Bridge has correct DDD structure, real vendor integrations (not stubs), proper encryption, and a working hot-reload mechanism. However, it has **2 critical bugs that will crash in production**, **zero backpressure handling** that will disconnect WebSockets under load, and **no memory safety** on the aggregation buffer. Fix the 5 critical/high items below before any live market data touches this system.

---

## 2. Code Evidence & Architecture Review

### 2.1 File Inventory (All Real Implementations, No Stubs)

| File | Lines | Verdict |
|------|-------|---------|
| `providers/infrastructure/connectors/polygon_connector.py` | 141 | **Real** WebSocket implementation with auth, subscribe, receive loop |
| `providers/infrastructure/connectors/finnhub_connector.py` | 147 | **Real** REST polling with deduplication and pruning |
| `providers/application/aggregation_engine.py` | 150 | **Real** tick→OHLCV with multi-timeframe support |
| `providers/application/health_monitor.py` | 154 | **Real** background task with degradation callbacks |
| `providers/application/failover_service.py` | 175 | **Real** blue/green swap with alert integration |
| `providers/application/gap_fill_service.py` | 140 | **Real** REST recovery with retry/backoff |
| `providers/application/credential_service.py` | 73 | **Real** AES-256-GCM with random nonce generation |
| `providers/application/config_manager.py` | 174 | **Real** pg_notify LISTEN/NOTIFY with blue/green swap |
| `providers/application/event_emitter.py` | 66 | **Real** topic routing to PostgresEventBus |
| `providers/application/connector_factory.py` | 106 | **Real** registry pattern with decorator registration |
| `providers/domain/normalization.py` | 67 | **Real** Pydantic V2 frozen models |
| `providers/domain/data_bridge.py` | 139 | **Real** AggregateRoot with event emission |
| `providers/infrastructure/storage/data_bridge_repositories.py` | 200 | **Real** SQLAlchemy CRUD with domain reconstruction |
| `providers/application/data_bridge_services.py` | 216 | **Real** application service with event publishing |
| `providers/ports.py` | 35 | **Real** AlertPort ABC |
| `providers/infrastructure/adapters/slack_alert_adapter.py` | 66 | **Real** Slack webhook adapter |

**No stubs, no mocks, no TODO placeholders.** Every file contains functional logic.

### 2.2 Architecture Pattern Compliance

- ✅ **Bounded Context Extension:** All code extends `providers/` — no orphaned modules
- ✅ **Aggregate Pattern:** `DataBridgeProvider` extends `AggregateRoot`, records events
- ✅ **Port/Adapter:** `AlertPort` ABC with `SlackAlertAdapter` implementation
- ✅ **Factory Pattern:** `ConnectorFactory` with `@register_connector` decorator
- ✅ **Event Sourcing:** All state changes emit `DomainEvent` subclasses
- ✅ **Repository Pattern:** `DataBridgeProviderRepository` with domain model reconstruction

---

## 3. Critical Gaps & Production Risks

### CRIT-01: Nonce Not Persisted — Credential Decryption Will Fail

**File:** `providers/infrastructure/storage/data_bridge_repositories.py:104`
**Severity:** CRITICAL — System cannot decrypt credentials after restart

```python
def get_credential(self, provider_id: str) -> Optional[EncryptedCredential]:
    cm = self.session.query(ProviderCredentialModel).filter_by(provider_id=provider_id).first()
    if not cm:
        return None
    return EncryptedCredential(
        ciphertext=cm.api_key_encrypted,
        nonce="",  # <--- BUG: empty string
        key_rotation_version=cm.key_rotation_version,
        expires_at=cm.expires_at,
    )
```

The `nonce` field is returned as `""`. When `CredentialEncryptionService.decrypt()` calls `base64.b64decode("")`, it returns `b""` (0 bytes). AESGCM requires a 12-byte nonce — this will raise `ValueError` on every decryption attempt.

**Root Cause:** The `provider_credentials` table has no `nonce` column. The nonce is generated during encryption but never stored.

**Fix:** Add `nonce_encrypted TEXT` column to `provider_credentials` table, store the base64-encoded nonce alongside the ciphertext.

---

### CRIT-02: Synchronous Event Bus Blocks WebSocket Receive Loop

**File:** `providers/infrastructure/connectors/polygon_connector.py:119-120`
**Severity:** CRITICAL — WebSocket disconnects under market volatility

```python
async def _receive_loop(self, ws):
    async for message in ws:
        ...
        if tick and self._on_tick:
            await self._on_tick(tick)  # <--- blocks on PostgresEventBus.publish()
```

The `_on_tick` callback chains through `AggregationEngine.process_tick()` → `_emit_bar()` → `DataBridgeEventEmitter.emit_bar()` → `PostgresEventBus.publish()`. The `PostgresEventBus.publish()` is **synchronous** (writes to `event_journal` within the current transaction). If the database has any latency spike (GC, checkpoint, lock contention), the WebSocket receive loop blocks, Polygon's server-side ping times out, and the connection drops.

**Impact:** During high-volatility events (exactly when data matters most), the system will disconnect from the data feed.

**Fix:** Insert an `asyncio.Queue` between the connector and the aggregation/emission pipeline:

```python
class PolygonConnector(BaseConnector):
    def __init__(self, ...):
        ...
        self._queue = asyncio.Queue(maxsize=50000)

    async def _receive_loop(self, ws):
        async for message in ws:
            # ... parse tick ...
            try:
                self._queue.put_nowait(tick)  # Never blocks WebSocket
            except asyncio.QueueFull:
                logger.warning("Tick queue full — dropping oldest")
                self._queue.get_nowait()  # Drop oldest
                self._queue.put_nowait(tick)

    async def _process_queue(self):
        """Separate task drains queue → aggregation → emit."""
        while self._running:
            tick = await self._queue.get()
            if self._on_tick:
                await self._on_tick(tick)
```

---

### CRIT-03: Unbounded Aggregation Buffer — Memory Leak Risk

**File:** `providers/application/aggregation_engine.py:77`
**Severity:** CRITICAL — OOM during market hours

```python
self._buffers: Dict[str, TickBuffer] = {}
```

The `_buffers` dictionary grows without limit. Each `TickBuffer.ticks` list appends without bound. For a symbol like SPY that can generate 100+ ticks/second, a single 1-minute window accumulates 6,000+ tick objects. With 500 symbols × 4 timeframes = 2,000 buffers, worst case is millions of tick objects in memory.

**Impact:** Worker process OOM-killed during normal market hours.

**Fix:** Add a `max_ticks_per_buffer` parameter and a stale buffer eviction:

```python
class TickBuffer:
    MAX_TICKS = 10000  # Safety cap

    def add_tick(self, tick: NormalizedMarketTick) -> None:
        if len(self.ticks) >= self.MAX_TICKS:
            logger.warning(f"Buffer overflow for {self.symbol}_{self.timeframe}")
            return  # Drop tick, preserve existing data
        self.ticks.append(tick)
```

Add a periodic `_evict_stale_buffers()` call that removes buffers older than 2× the timeframe duration.

---

### HIGH-04: No WebSocket Heartbeat/Message Timeout

**File:** `providers/infrastructure/connectors/polygon_connector.py:73`
**Severity:** HIGH — Silent data feed death undetected

```python
async with websockets.connect(POLYGON_WS_URL) as ws:
    self._ws = ws
    await self._authenticate(ws)
    await self._subscribe(ws)
    await self._receive_loop(ws)  # <--- blocks forever if no messages
```

If Polygon silently stops sending data (network partition, server-side freeze), `_receive_loop` will block on `async for message in ws` indefinitely. The `health_check()` method returns `True` because `self._ws.open` is still `True` — the TCP socket is open, just silent.

**Fix:** Add a message timeout:

```python
async def _receive_loop(self, ws):
    while self._running:
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=60.0)
        except asyncio.TimeoutError:
            logger.warning("No Polygon messages for 60s — reconnecting")
            break
        # ... process message ...
```

---

### HIGH-05: Finnhub Health Check Burns Rate Limit

**File:** `providers/infrastructure/connectors/finnhub_connector.py:69-75`
**Severity:** HIGH — Health monitor exhausts API quota

```python
async def health_check(self) -> bool:
    ...
    resp = await self._client.get(
        FINNHUB_NEWS_URL,
        params={"category": "general", "token": self.credentials.get("api_key", "")},
    )
    return resp.status_code == 200
```

The health monitor calls `health_check()` every 30 seconds. Each call makes a **real Finnhub API request**. Finnhub's free tier is 60 calls/minute. The health monitor alone consumes 2 calls/minute, plus the actual polling loop — leaving only ~58 calls for real data. Under failover scenarios with multiple providers being checked, this will hit 429s.

**Fix:** Cache the last health check result for 5 minutes. Only make a real API call if the cached result is stale or the connector reports degraded:

```python
def __init__(self, ...):
    ...
    self._last_health_check: Optional[float] = None
    self._last_health_result: bool = False

async def health_check(self) -> bool:
    now = time.monotonic()
    if self._last_health_check and (now - self._last_health_check) < 300:
        return self._last_health_result
    # ... actual API call ...
    self._last_health_check = now
    self._last_health_result = result
    return result
```

---

### HIGH-06: `set_maintenance()` Passes Logger Instead of Provider

**File:** `providers/application/data_bridge_services.py:170`
**Severity:** HIGH — Runtime crash on maintenance mode

```python
def set_maintenance(self, provider_id: str) -> None:
    provider = self._repo.get(provider_id)
    ...
    provider.set_maintenance()
    self._repo.save(provider)
    self._publish_events(logger)  # <--- BUG: passes logging.Logger, not provider
```

`_publish_events()` calls `provider.pull_domain_events()` — but `logger` has no such method. This will raise `AttributeError` every time a PM tries to set a provider to maintenance mode.

**Fix:** Change `logger` → `provider`.

---

### HIGH-07: ConfigManager Has No Postgres Reconnection

**File:** `providers/application/config_manager.py:80-93`
**Severity:** HIGH — Hot-reload silently dies

```python
async def _listen_loop(self) -> None:
    try:
        async with await psycopg.AsyncConnection.connect(self._dsn, autocommit=True) as conn:
            await conn.execute("LISTEN provider_config_updated")
            async for notify in conn.notifies():
                ...
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"ConfigManager listen loop error: {e}")
        # <--- Falls through. No reconnect. Listener is dead.
```

If the Postgres connection drops (network blip, server restart), the listener exits and never reconnects. All subsequent config changes are silently ignored until the worker process is manually restarted.

**Fix:** Wrap in a reconnection loop:

```python
async def _listen_loop(self) -> None:
    while self._running:
        try:
            async with await psycopg.AsyncConnection.connect(self._dsn, autocommit=True) as conn:
                await conn.execute("LISTEN provider_config_updated")
                async for notify in conn.notifies():
                    ...
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"ConfigManager connection lost: {e}")
            if self._running:
                await asyncio.sleep(5)  # Reconnect delay
```

---

### MED-01: Gap Fill Loses Intraday Precision

**File:** `providers/application/gap_fill_service.py:66-69`
**Severity:** MEDIUM — Intraday gaps not filled

```python
start=gap_start.strftime("%Y-%m-%d"),
end=gap_end.strftime("%Y-%m-%d"),
```

The gap fill uses date-only format for the Polygon API. If a 3-minute WebSocket disconnect happens at 14:25, the gap fill requests bars for the entire day, not just 14:25-14:28. This wastes API quota and may return bars the system already has.

**Fix:** Use full datetime format: `gap_start.strftime("%Y-%m-%dT%H:%M:%S")`

---

### MED-02: Finnhub `_seen_ids` Pruning Is Non-Deterministic

**File:** `providers/infrastructure/connectors/finnhub_connector.py:112-113`
**Severity:** MEDIUM — May re-process old articles

```python
if len(self._seen_ids) > 10000:
    self._seen_ids = set(list(self._seen_ids)[-5000:])
```

`set(list(...))` has no guaranteed ordering. Converting a set to a list and taking the last 5000 elements does NOT guarantee the most recent 5000 are kept. Old articles may be pruned while new ones are kept, but it's not deterministic.

**Fix:** Use an `OrderedDict` or a list-based LRU cache instead of a plain set.

---

### MED-03: `DeadLetterEntry` Model Is Defined But Never Used

**File:** `providers/domain/normalization.py:60-67`
**Severity:** MEDIUM — Normalization failures are lost

The `DeadLetterEntry` Pydantic model exists, the `data_bridge_dead_letter` table exists (migration 98), but **no code writes to it**. Normalization failures in `PolygonConnector._normalize_trade()` and `FinnhubConnector._normalize_article()` just log a warning and return `None`. The raw payload is lost forever.

**Fix:** Inject a dead-letter repository into connectors and write failed payloads:

```python
def _normalize_trade(self, event: dict) -> Optional[NormalizedMarketTick]:
    try:
        ...
    except (ValueError, TypeError) as e:
        logger.warning(f"Polygon normalization error: {e}")
        if self._dead_letter_repo:
            self._dead_letter_repo.append(DeadLetterEntry(
                provider_id=self.provider_id,
                raw_payload=event,
                error_message=str(e),
                error_type="TYPE_COERCION",
            ))
        return None
```

---

### MED-04: Credential Plaintext Exposure in Memory

**File:** `providers/application/connector_factory.py:39-41`
**Severity:** MEDIUM — API keys in memory longer than necessary

```python
class BaseConnector:
    def __init__(self, provider_id, config, credentials):
        self.credentials = credentials  # <--- plaintext key stored for connector lifetime
```

The decrypted API key is stored in `self.credentials` for the entire connector lifetime. If the process is dumped (OOM killer, debugger), the plaintext key is in memory.

**Fix:** Use a `SecureString` wrapper that zeroizes on `__del__`, or decrypt on-demand from the encrypted store rather than caching.

---

## 4. Actionable Engineering Fixes (Priority Order)

| # | Priority | Fix | Effort |
|---|----------|-----|--------|
| 1 | CRIT | Add `nonce` column to `provider_credentials`, store nonce on encrypt, return on get | 1h |
| 2 | CRIT | Add `asyncio.Queue` between connector and aggregation pipeline | 2h |
| 3 | CRIT | Add `max_ticks_per_buffer` cap + stale buffer eviction to AggregationEngine | 1h |
| 4 | HIGH | Add `asyncio.wait_for(ws.recv(), timeout=60)` to PolygonConnector | 30m |
| 5 | HIGH | Fix `set_maintenance` bug: `logger` → `provider` | 5m |
| 6 | HIGH | Add reconnection loop to ConfigManager._listen_loop | 30m |
| 7 | HIGH | Cache Finnhub health check results (5-min TTL) | 30m |
| 8 | MED | Wire DeadLetterEntry writes into connector normalization | 1h |
| 9 | MED | Fix gap fill datetime precision | 15m |
| 10 | MED | Replace `_seen_ids` set with OrderedDict for deterministic pruning | 30m |

**Total estimated effort to production-ready: ~7.5 hours.**

---

## 5. Positive Findings

The implementation gets several things right that many trading systems get wrong:

- ✅ **Strict Pydantic V2 models** with `frozen=True` prevent downstream mutation
- ✅ **All timestamps normalized to UTC** — no timezone ambiguity
- ✅ **AES-256-GCM** with random nonces — proper authenticated encryption
- ✅ **pg_notify hot-reload** — zero-downtime config changes
- ✅ **Blue/green connector swap** with health validation before cutover
- ✅ **Failover with priority-based fallback** — same data type, lower priority number wins
- ✅ **Gap fill with exponential backoff** — handles 429 gracefully
- ✅ **AlertPort abstraction** — not hardcoded to Slack
- ✅ **Domain events on every state change** — full audit trail
- ✅ **URN-compatible provider IDs** — ready for Karsa identity system
