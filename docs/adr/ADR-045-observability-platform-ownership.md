# ADR-045: Observability Bounded Context Boundaries and Ownership

## Status
Frozen

## Date
2026-06-14

## Context
Karsa's Virtual Investment Firm (VIF) requires a centralized subsystem for managing traces, logs, metrics, correlation, and end-to-end lineage mapping. Without strict boundaries, the Observability context is vulnerable to becoming a "God Bounded Context," causing tight operational coupling, transaction bottlenecks, and storage conflicts across the platform.

Furthermore, we must clarify:
1. Whether Observability should own lineage metadata.
2. The trust boundaries between Governance, Capital Allocation, the CIO, and the Observability Platform.
3. Whether Observability serves as an authoritative replay source.

## Decision
We enforce the following boundaries and ownership rules:

1. **Observability Bounded Context Ownership**:
   - The **Observability Platform** is the sole writer and authoritative subsystem for trace logs, aggregated metrics, and execution logs. Other contexts are strictly prohibited from writing to the observability data stores directly.
   - Decoupled, asynchronous execution is mandated: all telemetry is shipped out-of-band via non-blocking queues or event buses to prevent the observability context from blocking transactional execution paths.

2. **Lineage Ownership (Technical Lineage Only - Option C)**:
   - Lineage is split: **Observability** owns technical lineage (spans, traces, metrics, logs, correlation, causation).
   - A future **Knowledge Graph Bounded Context** owns business lineage (Research -> Thesis -> Decision -> Execution -> Outcome -> Performance -> Attribution -> Review -> Post-Mortem -> Governance -> Allocation). This avoids domain model leakage into Observability.
   - In Phase 1, business context IDs are logged as unstructured tags inside spans, migrating to a dedicated graph database in Phase 2.

3. **Replay Source Boundary (Supplementary Only)**:
   - Observability is **not** an authoritative replay source. Authoritative replay coordinator runs must pull from transaction-complete, frozen object storage contexts. Observability logs act as supplementary debug metadata only.

4. **Governance Bounded Trust Boundary & Audit separation**:
   - Governance Engine decisions, breach violations, exception approvals, and policy histories belong to the **Governance Engine Audit Trail** and are stored in transaction-safe, WORM compliance tables.
   - Ephemeral debug, latency, CPU, and operational spans belong to the **Observability Platform**.

5. **CIO Agent Integration Boundary**:
   - The future CIO Agent is prohibited from executing direct analytical queries against live observability databases. Observability must compile data asynchronously into read-only projections (e.g., aggregate scorecards, latency performance charts) which the CIO reads.

## Consequences
- **Decoupled Performance**: Slow database writes or outages in the observability stack cannot halt trading execution or governance gates.
- **Audit Integrity**: Compliance ledgers remain isolated in Governance, preventing lossy telemetry queues from breaking audits.
- **VIF Consistency**: Telemetry is cleanly separated from policy enforcement and business metadata relationships.
