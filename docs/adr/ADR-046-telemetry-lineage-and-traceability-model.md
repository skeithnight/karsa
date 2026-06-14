# ADR-046: Telemetry, Lineage, and Traceability Model

## Status
Frozen

## Date
2026-06-14

## Context
A robust Virtual Investment Firm (VIF) requires reconstructing decisions, events, and trade configurations from 5 years ago. To ensure complete auditability, we must define the storage and context propagation models for traces, metrics, logs, and lineage, and evaluate the trade-offs of immutability and concurrency controls. We must also manage telemetry storage volumes (100M+ events/day) without risking write-side database lock contention.

## Decision
We implement the following telemetry, lineage, and traceability model:

1. **Strictly Immutable Telemetry Ledger**:
   - Traces, logs, and metrics are strictly write-once, append-only entries. Update and delete queries on the telemetry schemas are blocked at the database level.
   - Spans are fully immutable. Corrective entries (e.g., late injected event context) are appended as new spans pointing back to the original trace ID, ensuring replay determinism remains intact.

2. **Three-Key Correlation / Causation Propagation**:
   - Every telemetry span and event envelope must propagate three identifiers:
     * **`TraceId`**: Globally unique, shared across the entire request sequence (e.g., from initial proposal to execution).
     * **`CorrelationId`**: Globally unique, groups asynchronous event loops or batch runs.
     * **`CausationId`**: Points directly to the span ID or event ID that triggered the current operation.
   - When a new workflow is triggered, a new `TraceId` and `CorrelationId` are generated. As operations propagate across contexts, the receiver sets its span's `CausationId` to the caller's span ID or incoming event ID.

3. **Trace Storage: Span Ledger + Trace Projection (Option B)**:
   - We reject single trace tables due to write-locking overhead. Instead, we implement:
     * **Span Ledger**: An append-only, strictly immutable SQL table where every child span is written as an independent row.
     * **Trace Projection**: An asynchronous read-side projection compiled via CDC from the Span Ledger and loaded into OpenSearch. This ensures zero write-side database lock contention.

4. **Telemetry Ingestion Sampling Model**:
   - To manage storage footprint, we partition telemetry into three retention tiers:
     * **Tier 1 (Governance, Capital Allocation, Decision Journal)**: 100% Ingestion, 5-Year WORM retention.
     * **Tier 2 (Attribution, Performance, Review, Post-Mortem)**: Adaptive Sampling (100% anomalies/errors, 10% success), 1-Year retention.
     * **Tier 3 (Debug & Operational Telemetry)**: 1% Random Ingestion, 14-Day retention.
   - Authoritative transactional ledgers are written directly to their respective databases and are **100% unaffected** by telemetry sampling.

5. **Zero OCC Concurrency**:
   - Optimistic Concurrency Control (OCC) is completely eliminated from the Observability context. Because all records are append-only, write conflicts never occur.

## Consequences
- **Absolute Trace Reconstructibility**: Spans made 5 years ago can be reconstructed by traversing the immutable Span Ledger.
- **Lock-Free Scalability**: Append-only design eliminates database write locking, enabling the platform to scale beyond 100M+ events/day.
- **Traceability**: Structural relationships are completely decoupled from performance/attribution calculations.
