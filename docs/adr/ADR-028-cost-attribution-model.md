# ADR-028: Multi-Dimensional Cost Attribution Model

## Status
Approved

## Date
2026-06-14

## Context
Karsa’s executions span across a variety of business scopes:
- Workflows (`workflow_id`)
- Capability executions (`capability_execution_id`)
- Provider executions (`provider_execution_id`)
- Virtual Investment Firm contexts (`research_run_id`, `thesis_id`, `worker_id`, `portfolio_id`, `strategy_id`, and other dynamic identifiers).

Relying entirely on a JSONB column for all dimensions introduces performance issues for analytical queries (deserialization overhead over 100M+ records) and prevents strong schema validation for critical core dimensions. 

Additionally, we need a mechanism for historical cost correction that guarantees replay determinism (original records must remain untouched) and idempotency across event delivery retries.

## Decision
We implement the following Cost Attribution Model:

1. **Hybrid Dimension Schema**:
   - We split business dimensions into two distinct categories:
     - **Typed Dimensions**: Hardcoded table columns for core Virtual Investment Firm identifiers:
       - `research_run_id` (VARCHAR)
       - `thesis_id` (VARCHAR)
       - `worker_id` (VARCHAR)
       - `portfolio_id` (VARCHAR)
       - `strategy_id` (VARCHAR)
     - **Extension Dimensions**: A JSONB column named `extended_dimensions` for unstructured, dynamic, or downstream context tags.
2. **Dimension Ownership & Validation**:
   - The **Attribution Engine** defines validation constraints for the typed dimensions (e.g., UUID format or specific prefix patterns). The downstream contexts (e.g., Research Engine, Portfolio Engine) supply these IDs in event headers.
   - Extended dimensions are capped in size (maximum 20 keys, key/value lengths restricted to 128 characters) to prevent database bloat.
3. **Indexing Strategy**:
   - B-Tree indexes are created on each individual typed dimension column (`research_run_id`, `thesis_id`, `worker_id`, `portfolio_id`, `strategy_id`) to accelerate analytical filters and grouping operations.
   - A GIN index is applied to the `extended_dimensions` JSONB column to support flexible queries on dynamic metadata.
4. **Analytics Strategy**:
   - Large-scale aggregations (e.g., total spend per portfolio, strategy performance reports) execute direct SQL operations (e.g., `SUM(calculated_cost) GROUP BY portfolio_id`) using the B-Tree indexes. This avoids JSONB parsing overhead and guarantees sub-second execution on 100M+ records.
5. **Immutable Cost Corrections (`AttributionAdjustment`)**:
   - An `AttributionAdjustment` is an append-only, immutable record with:
     - `adjustment_id` (UUID)
     - `original_attribution_id` (UUID reference)
     - `adjustment_amount` (Decimal delta)
     - `adjustment_reason` (string)
     - `adjustment_timestamp` (datetime)
   - The original `AttributionRecord` is **never** updated.
   - Replay execution bypasses active pricing and instead queries the historic `AttributionRecord` and its adjustments to reconstruct the exact cost of the execution trace, ensuring byte-for-byte replay consistency.
6. **Idempotency & Double-Attribution Prevention**:
   - Every provider execution generates a unique `execution_id`. The database enforces a `UNIQUE` constraint on the `execution_id` column of the `attribution_records` table.
   - Duplicate delivery of ingestion events fails safely at the database insertion level without double-billing or mutating state.
7. **Precision & Currency Normalization**:
   - All monetary values use Python's `Decimal` type (and SQL `DECIMAL(19, 6)`) to prevent float rounding errors. Standard currency is `"USD"`.

## Consequences
- **High-Speed Analytics**: Group-by and filter operations on core investment dimensions run at native native SQL speed without JSONB parsing.
- **Zero Schema Migrations**: New subsystems can use `extended_dimensions` immediately without DDL updates.
- **Strict Audit Integrity**: Since both records and adjustments are insert-only, the database is an immutable ledger.
- **Deterministic Replays**: Bypassing cost calculations during event replays guarantees that cost statistics do not drift or balloon during tests or runs.
- **Eventual Consistency**: Downstream projections (`CostLedgerProjection`) can be asynchronously updated or processed in batches without impacting the write path's scalability.
