# ADR-024: Observability Trace and Span Model

## Status
Approved

## Date
2026-06-14

## Context
Karsa coordinates distributed, asynchronous executions (Workflow runs, Capability invocations, Provider adapter queries, and Governance checks) across multiple contexts. To trace these executions for debugging, auditing, and historical reconstruction:
1. We must define a unified model representing execution flows.
2. We must ensure that logging telemetry and span records does not create write bottlenecks or lock contentions in the database.
3. We need a standard, globally unique identification strategy for traces and spans that aligns with modern open-source conventions.
4. We must define clean ownership boundaries to prevent Observability from duplicating data owned by other contexts (such as financial cost ledgers or qualitative journals).

## Decision
We implement the following architecture for the Observability Trace and Span Model:
1. **Decoupled Trace-Span Aggregate Boundary**:
   - **`Trace` is NOT an Aggregate Root**: We reject representing the entire `Trace` as a write-locked aggregate containing all child spans. Updating a single trace aggregate concurrently from multiple asynchronous workers would cause database write amplification, race conditions, and severe thread-locking contention.
   - **`Span` is the Write-Aggregation Unit**: Each span is saved as an independent, insert-only record in the database. Once a span is marked as `CLOSED`, its attributes are immutable.
   - **Trace Projections**: Traces are reconstructed dynamically on the read path via index queries or materialized view projections, completely decoupling writes from query loads.
2. **Standardized Identity and Format**:
   - We adopt the **W3C Trace Context** format (`traceparent`) for identity:
     * `TraceId`: A globally unique 32-character hex string (16 bytes) representing the entire workflow execution tree.
     * `SpanId`: A unique 16-character hex string (8 bytes) representing a specific unit of work.
   - Child spans reference their parent span using `parent_span_id`. The root span has no parent.
3. **Strict Ownership Boundaries**:
   - **No Cost Data Ownership**: The Observability Platform does **not** store actual costs, estimated costs, token counts, pricing, or financial calculations. It stores only an `attribution_id` value object tag which maps to a Cost Ledger entry owned by the Attribution Engine.
   - **No Narrative Data Ownership**: The Observability Platform does **not** store qualitative developer notes, rationales, assumptions, or decision narratives. It stores only a `decision_journal_id` value object tag which maps to a JournalEntry owned by the Decision Journal.
   - **No Audit Ledger Ownership**: Cryptographic compliance audit chains are owned by the Governance Audit context. Observability logs only `decision_id` and `audit_id` for timeline rehydration and visibility.
4. **Structured Span Schema**:
   - A span contains:
     * Identifiers: `trace_id`, `span_id`, `parent_span_id`.
     * Timestamps: `start_time`, `end_time` (UTC ISO-8601).
     * Execution Context: `name`, `span_kind` (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER), `status` (OK, ERROR).
     * Correlation Links: `attribution_id`, `decision_journal_id`, `review_session_id`.
     * Events: List of timed annotations (e.g. FSM transitions, retry triggers).
     * Tags: Key-value dictionary of metadata (e.g. `provider_urn`, `workflow_id`).

## Consequences
- **Zero Thread Contention**: Asynchronous execution paths append spans to the database concurrently without database locks, supporting extreme scalability.
- **Clean Context Isolation**: Observability is stripped of financial and journal narrative bloating, preventing duplicate sources of truth.
- **Trace Rehydration Latency**: Reassembling traces dynamically on the read path requires database indexes on `trace_id`, `attribution_id`, and `decision_journal_id`.
- **Immutability of Logs**: Closed spans cannot be modified, protecting the integrity of audit trails.
