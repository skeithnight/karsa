# Sprint-15 Performance Engine Foundation - Execution Hardening Review

## 1. Executive Summary
The Execution Hardening Review applies extreme stress-testing to the Implementation Planning Package against the `ARCHITECTURE_FROZEN` v6 baseline. While the vast majority of the architecture is sound, the review identified a critical, non-idempotent flaw in the additive UPSERT logic for daily buckets which mathematically violates CQRS guarantees under duplicate delivery scenarios. Additionally, ranking persistence remains underspecified, risking O(N^2) write amplification. This document issues specific, implementation-level remediations to completely harden the execution path without altering bounded contexts or architectural boundaries.

## 2. Findings Matrix

| Severity | Description | Impact | Recommendation |
|----------|-------------|--------|----------------|
| **CRITICAL** | **Additive Bucket Upsert is Not Idempotent.** The proposed `SET pnl = pnl + EXCLUDED.pnl` will double-count PNL if the message broker (e.g., Kafka) delivers the exact same event twice. | Mathematically corrupts all rolling windows, Sharpe proxies, and Capital Allocation limits on duplicate delivery. | Replace additive delta UPSERT with a target-scoped **Recompute UPSERT** derived directly from the idempotent `projection_decision_performance` root table. |
| **HIGH** | **Ranking Persistence Underspecified.** Ranking is described as a projection, but persisting a global rank upon every single event requires rewriting the entire leaderboard table continuously. | Severe Write Amplification (O(N^2) lock contention on leaderboard updates). | Declare Ranking as a **Query-Time Computation** (or Database View) executing `RANK() OVER (...)` natively against materialized target profiles, abandoning the physical `projection_ranking` table. |
| **MEDIUM** | **Invalidation Cost on 10M Events.** "Drop from T-14 and Rebuild" implies streaming thousands of events from Institutional Memory. | Restatements affecting high-volume workers may cause multi-second DB locks or read stalls. | Optimization: Rebuild boundaries should query the local `projection_decision_performance` table instead of reaching across the network to Institutional Memory. |
| **MEDIUM** | **Observability Deficit.** Relying solely on DLQ logs and stream offsets creates blind spots for projection lag and invalidation timings. | Capital Allocation could unwittingly consume stale data if the local-bus projection pipeline lags behind ingestion. | Introduce explicit `projection_lag_ms` Prometheus/OpenTelemetry metrics and temporal watermark tracking. |

---

## 3. Deep Area Analysis

### Area 1 — Delta Projection Idempotency Proof
- **Current Design**: Additive UPSERT.
- **Failure Scenarios**: Kafka "at-least-once" delivery causes the ingestion service to process offset 105 twice. The root `DecisionPerformanceRecord` safely ignores it via `ON CONFLICT DO NOTHING`. But the downstream bucket aggregator blindly executes `UPDATE pnl = pnl + 100`, resulting in `+200`.
- **Mathematical Proof**: `f(x) = x + y`. Executing `f(f(x))` yields `x + 2y`. This is non-idempotent.
- **Required Constraints**: The downstream projector MUST query the idempotent root table. When an event updates `target X` on `Date Y`, the projector executes: `INSERT INTO projection_daily_pnl_bucket (target_id, date, pnl) VALUES (X, Y, (SELECT SUM(gross_pnl) FROM projection_decision_performance WHERE target_id=X AND DATE(decision_timestamp)=Y)) ON CONFLICT DO UPDATE SET pnl = EXCLUDED.pnl;`.
- **Verdict**: **FAIL** (Remediation Required).

### Area 2 — Replay Authority Proof
- **Authority Matrix**: 
  - Immutable Inputs: `DecisionCommittedEvent`, `AttributionCalculatedEvent`, `RegimeChangedEvent` (from Institutional Memory).
- **Determinism Proof**: As long as Replay strictly obeys the composite `(occurred_at, global_sequence_id, event_id)` sorting key, the stream of events yields exactly the same idempotent states. Upstream engine evolution (e.g., Regime engine adding new regime types) does not break replay because historic events are immutable facts.
- **Verdict**: **PASS**.

### Area 3 — Ranking Persistence Decision
- **Option Analysis**:
  - *Option A (Materialized Projection)*: Every trade alters a Sharpe ratio, forcing a complete recalculation and rewrite of every row in `projection_ranking`.
  - *Option B (Query-Time)*: A simple SQL View: `CREATE VIEW view_ranking_profile AS SELECT target_id, RANK() OVER (ORDER BY sharpe_proxy DESC) as global_rank FROM projection_worker_performance;`.
- **Recommended Decision**: Option B. Abandon `projection_ranking` table. Ranking is perfectly solved by modern RDBMS window functions querying O(1) indexed profiles.
- **Verdict**: **FAIL** (Remediation Required).

### Area 4 — Projection Invalidation Cost Model
- **Assumptions**: 10M lifetime decisions. 
- **Complexity Model**: If a governance restatement hits a worker with 1M decisions, rebuilding their tree requires re-aggregating 1M rows. 
- **Cost Containment Analysis**: PostgreSQL can `SUM()` 1M indexed rows in ~50-100ms. Because we shifted buckets to a **Recompute UPSERT** (Area 1), the invalidator simply runs the recompute query for the affected dates. 
- **Operational Risks**: Perfectly bounded. Network calls to Institutional Memory are avoided entirely.
- **Verdict**: **PASS**.

### Area 5 — Observability Model
- **Missing Controls**: Projection Pipeline Lag. If Capital Allocation queries the DB while the pipeline is 5 minutes behind due to CPU starvation, it allocates incorrectly. 
- **Alerting Requirements**: System MUST expose `performance_pipeline_lag_seconds`. If lag > 5 seconds, downstream consumers (Capital Engine) must fail-fast or halt allocations.
- **Verdict**: **FAIL** (Remediation Required).

---

## 4. Architecture Compliance Verification
- **Architecture Change Required**: None. Architecture v6 explicitly dictated deterministic replay. Area 1 and Area 3 failures were merely flawed *implementation assumptions* that mathematically violated the frozen v6 guarantees.
- **Implementation Change Only**: Yes. Switching to Recompute UPSERT and Query-Time Ranking.
- **Operational Control Only**: Yes. Adding lag metrics.

## 5. Execution Readiness Assessment
**EXECUTION_HARDENING_REQUIRED**

## 6. Mandatory Remediation List
Before code generation is permitted, the development team must accept the following mandatory execution constraints:

1. **Implement Recompute Bucket Aggregation**: Completely eradicate additive `UPDATE SET pnl = pnl + EXCLUDED.pnl` logic. Replace it with target/date-scoped `SUM()` recalculations derived from the idempotent `projection_decision_performance` root table.
2. **Implement Query-Time Ranking**: Delete any planned `projection_ranking` table schema. Replace it with an explicit RDBMS `VIEW` using `RANK() OVER`.
3. **Implement Local Invalidation**: Ensure the Projection Invalidation Orchestrator queries the local `projection_decision_performance` table for rebuilds, rather than making cross-network calls to Institutional Memory.
4. **Implement Lag Telemetry**: Integrate Prometheus/OTel metrics tracking `projection_pipeline_lag_seconds` comparing ingestion timestamp vs downstream materialization timestamp.
