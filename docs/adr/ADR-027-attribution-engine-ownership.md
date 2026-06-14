# ADR-027: Attribution Engine Context Ownership and Boundaries

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires an authoritative, audit-ready subsystem to calculate, track, and allocate execution costs across various business dimensions (e.g., workflows, strategies, research runs, theses, and portfolios). 

If `CostLedgerProjection` remains an aggregate root, any concurrent executions under the same dimension (e.g., a shared `portfolio_id` or `strategy_id`) will compete to write-lock the same ledger row. This creates severe database Optimistic Concurrency Control (OCC) contention, causing transaction rollbacks, latency spikes, and high write amplification.

To eliminate this contention and guarantee maximum write scalability, we must re-evaluate the boundaries of cost data mutation and ledger ownership.

## Decision
We implement the following context ownership rules:

1. **Write Aggregates (Attribution Engine)**:
   - The **Attribution Engine** is the sole writer of the following aggregates:
     - `AttributionRecord`: An immutable, write-once record representing the exact cost calculated for a single execution.
     - `AttributionAdjustment`: An immutable, append-only record representing a correction or change to a previous attribution.
   - The original `AttributionRecord` is never modified or updated.
2. **Read-Side Projection (CostLedgerProjection)**:
   - `CostLedgerProjection` is defined as a **read-side projection** updated asynchronously or via atomic database upserts triggered by `AttributionRecord` and `AttributionAdjustment` events.
   - It maintains cumulative balances of target dimensions for fast queries.
3. **Provider Registry Boundaries**:
   - The **Provider Registry** owns static model pricing definitions (`ProviderPricing`). It does not compute actual execution costs.
4. **Provider Telemetry Boundaries**:
   - The **Provider Telemetry** context owns parsing raw provider client responses to extract input/output token counts and latency metrics. It does not store or calculate financial costs; it merely publishes token counts in execution completion events.
5. **Observability Platform Boundaries**:
   - The **Observability Platform** owns execution tracing and span models. It does **not** store actual costs, estimated costs, or pricing. It references the Attribution Bounded Context by mapping the `attribution_id` tag on spans.
6. **Separation from Downstream Systems**:
   - The **Performance Engine** owns outcome accuracy evaluations (e.g., Brier scores). It reads attribution ledger records to link P&L performance but never mutates cost records.
   - The **Portfolio Engine** owns capital allocation limits and sizes risk exposure based on cost data, but has no write hooks into the Attribution Engine.

## Consequences
- **Zero Lock Contention**: Removing `CostLedgerProjection` from the write path prevents concurrent transactions from locking the same balance row.
- **Single Source of Truth**: Eliminates duplicate cost calculations, ensuring all billing, reporting, and portfolio evaluations reference identical records.
- **Database Decoupling**: Telemetries and observability logs do not block on financial calculation transactions, preventing database write amplification.
- **Audit Traceability**: Financial audits can query the immutable `CostLedgerProjection` or reconstruct it from the append-only `AttributionRecord` and `AttributionAdjustment` tables.
- **Dynamic Pricing Drift Isolation**: Changes to active provider rates in the registry do not alter historical cost records, as the Attribution Engine persists rates at execution time inside the immutable record.
- **Consistency Guarantees**: Write operations achieve immediate consistency. Read-side ledger updates are eventually consistent, which is completely acceptable for reporting and capital allocation check workflows.
