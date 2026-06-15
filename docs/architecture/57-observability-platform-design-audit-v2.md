# Sprint-49 Observability Platform Hostile Architecture Review v2

## 1. Executive Summary
A second hostile verification review has been conducted against the revised `57-observability-platform-design.md` and its supporting ADRs (064, 065, 066). While the foundational protections against metric cardinality explosions and projection connection exhaustion are sound, the architecture introduces severe new operational vulnerabilities. Specifically, it fails to account for "Meta-Observability" (observing the observability platform itself) and structurally conflicts with the explicit constraints of the firm's long-term home-lab deployment strategy. These gaps are fatal blockers for Sprint-50 Production Readiness.

## 2. Ownership Boundary Matrix
* **Observability Ownership**: Clean. Defined as a terminal passive sink.
* **Telemetry Ownership**: Clean. Upstream systems own creation.
* **Worker/Queue/Provider Ownership**: Clean.
**Verdict**: PASS. 

## 3. Architecture Review
* **Event Contracts**: Missing explicit `ObservabilityHealthDegraded` or `IngestionLagDetected` events.
* **Backpressure Handling**: ADR-066 introduces backpressure off the bus, but ignores the consequence: if backpressure halts ingestion, the bus buffers grow infinitely until the broker crashes, transferring the outage back to the core system.
* **Fail-Open Guarantees**: PASS. Upstream systems continue unharmed if Observability disconnects.

## 4. Replayability Review
* **Cold Storage Recovery Risk**: **FATAL**. The architecture mandates day-8 telemetry offloading to S3/Parquet. However, if S3 is unreachable, the 7-day hot storage pruning cron job will eventually obliterate un-archived data to protect Postgres, causing permanent historical loss. The architecture provides no protocol for pausing pruning during cold-storage degradation.

## 5. Retention Review
* **Storage Tiers (ADR-064)**: Conceptually sound, but practically incomplete. It lacks a restoration mechanism. A 10-year replay is theoretically possible, but the architecture fails to define how a Parquet file is re-hydrated into the execution engine to actually perform the replay.

## 6. Scalability Review
* **Projection Scalability**: Solved via ADR-066 debounced batching.
* **Database Monitoring**: **FAIL**. The architecture monitors upstream business databases, but entirely lacks internal monitoring of the massive partitioned Postgres ledger it relies on. 

## 7. Fail-Open Review
* **Upstream Protection**: Validated. The HTTP/RPC and Bus emitters are decoupled.

## 8. Production Readiness Review
* **SLO / Failure Visibility**: Addressed.
* **Projection Lag Visibility**: **MISSING**. Without measuring the delta between `event.created_at` and `projection.updated_at`, operators will not know if the Operational Snapshot is 100ms old or 12 hours old during a retry storm.

## 9. UI Readiness Review
* **Worker/Queue/Capability Dashboard**: Fully supported by `OperationalStateRepository`.
* **Governance/Attribution Dashboard**: **OUT OF BOUNDS**. Observability correctly does NOT expose query models for these domains. Sprint-51 must pull business dashboards directly from the respective bounded contexts, preserving pure architectural separation.

## 10. Home Lab Review
* **Storage Growth Exhaustion**: **FATAL**. 100M+ events per day generating high-cardinality JSONB traces in PostgreSQL will rapidly exhaust the limited SSD capacities of a standard Lenovo Tiny Node, destroying disk endurance (TBW) through constant 7-day rolling partition rewrites.
* **Memory Exhaustion**: In-memory debounced batching of 10M message retry storms (ADR-066) will immediately OOM crash a Tiny Node possessing limited RAM.

## 11. Risks
* **Meta-Observability Blindspot**: If the `IngestTelemetryService` dies silently, the dashboards will display stagnant, false-healthy states because there is no heartbeat monitor tracking the ingestion workers themselves.
* **Disk Burnout**: Extreme high-frequency writes on consumer-grade SSD hardware.

## 12. Architecture Delta Analysis
* **Improvements**: Robust projection storm protection and cardinality governance.
* **Hidden Complexity**: S3 archival pipelines are incredibly complex to orchestrate transactionally alongside destructive pruning.
* **Missing Capabilities**: Meta-monitoring, Parquet rehydration, SSD-aware batching.

## 13. Acceptance Criteria Review
* Ownership boundaries remain intact: **YES**
* Telemetry is replayable: **PARTIAL** (No rehydration strategy defined)
* Visibility is complete: **NO** (Observability platform itself is invisible)
* Home Lab Compatible: **NO** (Destroys SSD endurance / OOM risks)

## 14. Final Verdict
**ARCHITECTURE_REQUIRES_REVISION**
