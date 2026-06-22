# Sprint-51 through Sprint-59: Design Audit Report

**Auditor:** Claude Code
**Date:** 2026-06-22
**Scope:** All 9 design documents (`docs/implementation/sprint-{51..59}/design.md`)
**Baseline:** Existing Karsa codebase at `src/karsa/`

---

## 1. Executive Summary

**Verdict: 6 CRITICAL conflicts, 9 HIGH issues, 12 MEDIUM findings.**

The sprint designs are well-structured and follow Karsa's DDD documentation format. However, they were authored as if the codebase were a greenfield project. **Three of the four phases duplicate or conflict with existing, production-grade modules**: `execution/`, `risk/`, and `providers/`. The designs must be refactored to extend existing bounded contexts rather than creating parallel ones.

**vault.md has been deleted.** Plaintext API keys are no longer on disk.

---

## 2. CRITICAL Findings (Must Fix Before Implementation)

### CRIT-01: Sprint-56 Duplicates Existing Execution Module

**Sprint-56** designs a new `karsa-execution-bridge` with `execution_orders`, `execution_fills`, `execution_risk_limits` tables and a `HardRiskEngine`.

**Conflict:** `src/karsa/execution/` **already exists** with a complete hexagonal architecture:
- `execution/domain/events.py` — `OrderStagedEvent`, `OrderValidatedEvent`, `OrderRoutedEvent`, `OrderFilledEvent`, `OrderRejectedEvent`, `ExecutionIncidentEvent`
- `execution/application/ports.py` — `BrokerAdapterPort` (with `route_order()`), `DecisionAuthorizationPort`, `GovernanceAuthorizationPort`
- `execution/application/services.py` — `OrderPEPService`, `OrderRoutingService`, `FillService`, `ExecutionStateProjectionService`
- `bootstrap.py` already wires all execution services into `ApplicationContainer`

**Impact:** Two competing execution pipelines, two `OrderFilledEvent` definitions, two broker adapter patterns. Implementation will create a forked architecture.

**Remediation:** Sprint-56 must **extend** the existing `execution/` module:
- Add `HardRiskEngine` as a new service within `execution/application/services.py`
- Add new tables (`execution_risk_limits`) via Alembic migration, referencing existing execution tables
- Reuse existing `OrderStagedEvent` → `OrderValidatedEvent` → `OrderRoutedEvent` → `OrderFilledEvent` flow
- The "kill switch" should subscribe to the existing event bus, not a new topic

---

### CRIT-02: Sprint-57 Duplicates Existing BrokerAdapterPort

**Sprint-57** designs a new `BrokerAdapterFactory` with `@register_broker` decorator and `AlpacaAdapter`/`IBKRAdapter`.

**Conflict:** `execution/application/ports.py` already defines:
```python
class BrokerAdapterPort(ABC):
    def route_order(self, execution_id, symbol, quantity, direction, order_type, price, pep_token_signature) -> Dict[str, Any]:
```

**Impact:** Two broker adapter patterns with different interfaces (sync `route_order` vs async `place_order`), different return types, different credential management.

**Remediation:** Sprint-57 must implement concrete adapters **behind the existing `BrokerAdapterPort`**:
- Create `execution/infrastructure/adapters/alpaca_adapter.py` implementing `BrokerAdapterPort`
- Create `execution/infrastructure/adapters/ibkr_adapter.py` implementing `BrokerAdapterPort`
- The feedback loop should emit existing event types (`OrderFilledEvent`, `OrderRejectedEvent`) not new ones

---

### CRIT-03: Sprint-58 Duplicates Existing Risk Module

**Sprint-58** designs a new `RiskCalibrationEngine` with EWMA volatility, `asset_risk_metrics` table, and `RiskScalingAppliedEvent`.

**Conflict:** `src/karsa/risk/` **already exists** with production-grade services:
- `RiskEvaluationService` — Full parametric VaR/CVaR using covariance matrices
- `CovarianceForecastService` — EWMA covariance estimation (already implements EWMA!)
- `ConcentrationRiskService` — HHI, Gini, Top-5 weight
- `LiquidityRiskService` — Days-to-liquidate calculation
- `StressTestingService` — Scenario shock evaluation
- `risk/models.py` — `RiskEvaluationRecord`, `CovarianceForecast`, `StressEvaluationRecord` (all `ImmutableAggregate`)
- `risk/events.py` — `RiskEvaluationCreatedEvent`, `CovarianceForecastUpdatedEvent`, `StressEvaluationCreatedEvent`
- `risk/ports.py` — `ReturnsDataPort`, `RegimeStatePort`, `ObjectStorePort`, `EventPublisherPort`

**Impact:** Two risk engines with overlapping math (both compute volatility, both consume market data). The existing engine uses covariance matrices + regime multipliers; the new one uses per-asset EWMA. They will produce conflicting position sizes.

**Remediation:** Sprint-58 must **extend** the existing `risk/` module:
- Add `VolatilityTargetingService` as a new service in `risk/services.py`
- Reuse `CovarianceForecastService`'s EWMA logic rather than reimplementing
- Add `asset_risk_metrics` table as a new read-model, not a separate aggregate
- The "intercept ThesisApprovedEvent" pattern should be a new service that calls existing risk services
- Emit `RiskScalingAppliedEvent` following existing event pattern (frozen dataclass with `event_id`, `correlation_id`, `causation_id`, `timestamp`)

---

### CRIT-04: Sprint-51 Ignores Existing Provider Module

**Sprint-51** designs `data_providers`, `provider_credentials`, `provider_configurations`, `provider_health_logs` tables and a `ConnectorFactory`.

**Conflict:** `src/karsa/providers/domain/client.py` already defines:
```python
class ProviderClient(ABC):
    def fetch_asset(self, asset_id: str) -> Dict[str, Any]: ...
    def fetch_universe(self, universe_id: str) -> List[Dict[str, Any]]: ...
    def health_check(self) -> bool: ...
```

**Impact:** Two provider abstractions with different interfaces. The existing `ProviderClient` is data-oriented (`fetch_asset`, `fetch_universe`); the new `BaseConnector` is stream-oriented (`start`, `stop`).

**Remediation:** Sprint-51 must **extend** the existing `providers/` module:
- Add new tables under the existing `providers/` bounded context
- `BaseConnector` should compose with (not replace) `ProviderClient`
- The `ConnectorFactory` should be in `providers/infrastructure/`, not a new module
- The `ProviderClient.health_check()` method already exists — reuse it for the Health Monitor

---

### CRIT-05: Event Contract Fragmentation

The sprint designs introduce **18 new event types** that don't follow existing event patterns:

| Sprint | New Events | Existing Pattern |
|--------|-----------|-----------------|
| 51 | `ProviderRegisteredEvent`, `ProviderConfigChangedEvent`, `ProviderPausedEvent`, `ProviderHealthChangedEvent` | — |
| 52 | (uses `karsa.market.bar`, `karsa.news.article` topics) | — |
| 53 | `ProviderFailoverEvent`, `GapFillCompletedEvent` | — |
| 55 | `ThesisGeneratedEvent`, `ThesisApprovedEvent`, `ThesisRejectedEvent` | — |
| 56 | `RiskRejectedEvent`, `OrderSubmittedEvent` | `OrderStagedEvent`, `OrderValidatedEvent`, `OrderRoutedEvent` already exist |
| 57 | `OrderSubmittedEvent`, `OrderFilledEvent`, `ExecutionFailedEvent` | `OrderFilledEvent`, `OrderRejectedEvent` already exist |
| 58 | `RiskScalingAppliedEvent` | `RiskEvaluationCreatedEvent` already exists |
| 59 | `StaleDataAlertEvent` | — |

**Three different event base classes coexist:**
1. `shared/domain/event.py` — `DomainEvent` with `event_id`, `stream_id`, `aggregate_id`, `occurred_at`
2. `risk/events.py` — frozen dataclasses with `event_id`, `correlation_id`, `causation_id`, `timestamp`
3. `execution/domain/events.py` — frozen dataclasses with `event_id`, `event_type`, `correlation_id`, `causation_id`, `timestamp`

**Impact:** Event consumers must handle three different event shapes. Projection workers can't use a single deserializer.

**Remediation:** All new events must inherit from **one** existing base class. Recommend `shared/domain/event.py:DomainEvent` as the canonical base. Add `correlation_id` and `causation_id` to it if missing.

---

### CRIT-06: Bootstrap.py Not Updated

None of the sprint designs mention updating `src/karsa/bootstrap.py` to wire new services.

**Impact:** New services won't be instantiated. The `ApplicationContainer` won't know about Data Bridge, LLM Pool, RAG, or new Execution/Risk services.

**Remediation:** Each sprint's DoD must include: "New services registered in `bootstrap.py:ApplicationContainer`."

---

## 3. HIGH Findings (Should Fix)

### HIGH-01: Sprint-59 Ignores Existing CIO Module

`src/karsa/cio/` already exists with `CIODecisionService`, `PortfolioOrchestrationService`, `DecisionJournalPort`, `GovernanceExceptionPort`. Sprint-59 designs a `karsa-cio-producer` without referencing this module.

**Fix:** The CIO Producer should be a new service **within** `cio/`, not a separate worker module. It should compose with existing `CIODecisionService`.

### HIGH-02: Sync vs Async Mismatch

The existing `BrokerAdapterPort.route_order()` is synchronous. Sprint-57's `AlpacaAdapter.place_order()` is `async def`. The existing `PostgresEventBus.publish()` is synchronous. Sprint designs assume async event emission throughout.

**Fix:** Decide: either migrate the existing execution module to async (breaking change), or keep new adapters synchronous to match existing patterns.

### HIGH-03: URN Not Used in Sprint Designs

The existing codebase uses URNs extensively (`urn:karsa:portfolio:snapshot:...`, `urn:karsa:risk:covariance:...`, `urn:karsa:regime:...`). The sprint designs use plain UUIDs and string identifiers everywhere.

**Fix:** All new entities must use Karsa URN format via `shared/identity/urn_builder.py`.

### HIGH-04: Sprint-54 pgvector May Conflict with Existing Object Storage

The existing `risk/ports.py:ObjectStorePort` stores covariance matrices in S3/MinIO. Sprint-54 introduces pgvector for embeddings. Both are "store large numerical data" patterns but use different backends.

**Fix:** Document clearly: pgvector is for text embeddings (RAG), ObjectStore is for numerical matrices. No overlap, but the distinction must be explicit.

### HIGH-05: Sprint-55 Thesis Aggregate Missing URN Validation

Existing aggregates like `RiskEvaluationRecord` enforce strict URN validation in `__post_init__`. Sprint-55's `TradeThesis` aggregate uses plain `ticker: str` without URN validation.

**Fix:** `TradeThesis.ticker` should be `asset_urn: str` with `urn:karsa:asset:` prefix validation.

### HIGH-06: Sprint-56 Kill Switch Uses New Topic Pattern

The kill switch listens to `karsa.system.kill_switch` — a new topic pattern. Existing Karsa events flow through `PostgresEventBus` writing to `event_journal` table, not separate topics.

**Fix:** Kill switch should be a domain event (`KillSwitchActivatedEvent`) published through the existing event bus, not a separate Redis/Kafka topic.

### HIGH-07: Sprint-52 Dead-Letter Table Not Designed

Sprint-52 mentions "log the raw payload to a dead-letter table" for normalization failures, but doesn't define the schema.

**Fix:** Add dead-letter table schema to Sprint-52 persistence design.

### HIGH-08: Sprint-53 Slack Integration Not Configurable

The Alert Service hardcodes Slack webhooks. The existing codebase uses port/adapter pattern for all external integrations.

**Fix:** Define `AlertPort` (ABC) in ports.py. `SlackAlertAdapter` implements it. Future adapters for email, PagerDuty, etc.

### HIGH-09: Sprint-59 TimescaleDB Extension Not in Existing Migration Strategy

The existing Alembic migrations (43+ files) use standard PostgreSQL. Sprint-59 introduces TimescaleDB hypertables via `create_hypertable()`. This is a PostgreSQL extension that may not be available in all environments.

**Fix:** TimescaleDB should be an optional extension. The CIO Producer must degrade gracefully if TimescaleDB is not installed (fall back to standard tables with manual partitioning).

---

## 4. MEDIUM Findings (Nice to Fix)

### MED-01: Sprint-51 `provider_configurations` JSONB vs Existing Config Pattern

No existing module uses JSONB for configuration. The sprint introduces a new pattern. Consider whether this aligns with how other modules handle configuration (environment variables, YAML files, etc.).

### MED-02: Sprint-52 Aggregation Buffer Has No Persistence

The tick buffer is purely in-memory. If the worker crashes mid-window, all buffered ticks are lost. Consider writing raw ticks to a temporary table or WAL for recovery.

### MED-03: Sprint-53 Gap Fill Has No Ordering Guarantee

Gap-filled bars are replayed through the normalization pipeline, but there's no guarantee they arrive at the consumer before live bars resume. Consider a sequence number or timestamp-based ordering mechanism.

### MED-04: Sprint-54 Embedding Dimension Hardcoded to 1536

`text-embedding-3-small` outputs 1536 dimensions. If the embedding model changes, the table schema must be altered. Consider using a flexible dimension column or storing the model version alongside the embedding.

### MED-05: Sprint-55 Researcher Agent Consumes Every Market Bar

The design implies the Researcher Agent generates a thesis for every `karsa.market.bar` event. This will be extremely expensive (LLM call per bar per symbol). Add a filtering mechanism (e.g., only trigger on significant price moves or news events).

### MED-06: Sprint-55 Governance Agent Has No Caching

Every thesis triggers an LLM call for governance. If the same thesis pattern repeats, the governance check should be cached or deduplicated.

### MED-07: Sprint-56 TWAP Slicer Has No Market Hours Check

The TWAP slicer splits orders over 30 minutes without checking if the market is about to close. Add a market-hours-aware scheduling mechanism.

### MED-08: Sprint-56 Risk Limits Table Seeding Not Specified

"DoD: Seed risk limits table with default values" — but the default values are not specified. Define concrete defaults: `MAX_SINGLE_ORDER_USD=500000`, `MAX_POSITION_SIZE_PCT=0.05`, `MAX_DAILY_TURNOVER_USD=5000000`.

### MED-09: Sprint-57 IBKR Adapter Should Be Stubbed

"DoD: IBKRAdapter places a paper trading order via TWS gateway (if available; otherwise stubbed)" — this is too vague. Either commit to IBKR support or explicitly defer it to a future sprint.

### MED-10: Sprint-58 Fail-Open Is Risky

"If risk engine crashes, thesis passes through unmodified" — this bypasses the safety layer. Consider a fail-closed option where the PM must explicitly approve bypassing risk checks.

### MED-11: Sprint-59 WebSocket Has No Authentication

The `WS /api/cio/ws/live` endpoint has no authentication. Any client can connect and receive real-time portfolio data. Add token-based auth.

### MED-12: Sprint-59 CIO Producer 500ms SLA Is Aggressive

"DoD: CIO Producer updates portfolio state within 500ms" — this depends on TimescaleDB write latency, event bus throughput, and mark-to-market calculation time. 500ms may not be achievable under load. Consider 2000ms as a more realistic target.

---

## 5. Structural Recommendations

### 5.1 Module Mapping (Sprint → Existing Module)

| Sprint | New Module? | Should Extend |
|--------|------------|---------------|
| 51 | `data_bridge/` (new) | `providers/` (existing) |
| 52 | `data_bridge/` (new) | `providers/` (existing) |
| 53 | `data_bridge/` (new) | `providers/` (existing) |
| 54 | `ai/` or `llm/` (new) | New bounded context — OK |
| 55 | `ai/` or `llm/` (new) | New bounded context — OK |
| 56 | None | `execution/` (existing) |
| 57 | None | `execution/` (existing) |
| 58 | None | `risk/` (existing) |
| 59 | None | `cio/` (existing) |

### 5.2 Revised Sprint Scoping

**Sprint-51 → "Data Bridge: Extend Provider Registry"**
- Add tables to `providers/` module, not a new `data_bridge/` module
- Reuse `ProviderClient.health_check()` for health monitoring
- `BaseConnector` wraps `ProviderClient`, adds streaming capability

**Sprint-56 → "Execution Bridge: Add Hard Risk Engine"**
- Add `HardRiskEngine` service to `execution/application/services.py`
- Add `execution_risk_limits` table via Alembic
- Reuse existing `OrderStagedEvent` → `OrderValidatedEvent` → `OrderRoutedEvent` → `OrderFilledEvent` flow
- Kill switch is a `KillSwitchActivatedEvent` on the existing event bus

**Sprint-57 → "Execution Bridge: Alpaca & IBKR Adapters"**
- Implement `BrokerAdapterPort` with `AlpacaAdapter` and `IBKRAdapter`
- Feedback loop emits existing `OrderFilledEvent`, `OrderRejectedEvent`
- Register in `bootstrap.py`

**Sprint-58 → "Risk Module: Volatility Targeting Service"**
- Add `VolatilityTargetingService` to `risk/services.py`
- Reuse `CovarianceForecastService` EWMA logic
- `asset_risk_metrics` is a read-model projection, not a new aggregate
- Events follow existing `risk/events.py` frozen dataclass pattern

**Sprint-59 → "CIO Module: Portfolio Aggregation & Dashboard"**
- Add `CIOProducerService` to `cio/services.py`
- TimescaleDB is optional; degrade to standard PostgreSQL
- WebSocket endpoint in `cio/api.py`

### 5.3 Event Contract Consolidation

All new events must use `shared/domain/event.py:DomainEvent` as base:
```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    stream_id: str
    aggregate_id: str
    aggregate_type: str
    schema_version: int = 1
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""  # ADD THIS
    causation_id: str = ""    # ADD THIS
```

---

## 6. Positive Findings

The sprint designs correctly identify:
- The critical gap in market data ingestion (Data Bridge is genuinely new)
- The need for RAG/institutional memory (no existing equivalent)
- The LLM Pool pattern for multi-provider resilience
- The separation of AI reasoning (Researcher) from validation (Governance)
- The importance of volatility-targeted position sizing
- The stale data circuit breaker as a safety mechanism
- The event-driven architecture as the backbone

The designs are well-documented with sequence diagrams, state diagrams, failure handling, and acceptance criteria. The issue is not quality — it's alignment with existing code.

---

## 7. Action Items

| # | Priority | Sprint | Action |
|---|----------|--------|--------|
| 1 | CRITICAL | 56 | Refactor to extend `execution/` module, not create new one |
| 2 | CRITICAL | 57 | Implement behind existing `BrokerAdapterPort` |
| 3 | CRITICAL | 58 | Extend existing `risk/` module, reuse EWMA from `CovarianceForecastService` |
| 4 | CRITICAL | 51 | Extend `providers/` module, reuse `ProviderClient` |
| 5 | CRITICAL | ALL | Consolidate event base class to `shared/domain/event.py:DomainEvent` |
| 6 | CRITICAL | ALL | Add bootstrap.py wiring to each sprint's DoD |
| 7 | HIGH | 59 | Extend existing `cio/` module |
| 8 | HIGH | ALL | Use URN format for all new entity identifiers |
| 9 | HIGH | 56,57 | Resolve sync vs async mismatch with existing execution module |
| 10 | HIGH | 56 | Kill switch uses existing event bus, not separate topic |
| 11 | HIGH | 59 | TimescaleDB as optional extension |
| 12 | MEDIUM | 55 | Add market bar filtering to avoid LLM-per-bar cost explosion |
| 13 | MEDIUM | 56 | Define concrete risk limit defaults |
| 14 | MEDIUM | 59 | Add WebSocket authentication |
