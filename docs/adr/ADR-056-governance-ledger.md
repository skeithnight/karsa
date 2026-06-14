# ADR-056: Governance Decision Ledger and Replayability Model

## Status
Accepted

## Context
High-frequency staging checkouts can cause severe database page bloating if all stateless evaluations are persisted. We must establish a ledger storage strategy that protects database performance while retaining a complete, immutable audit trail for compliance and replayability.

## Decision
We define the following ledger and audit trail rules for the Governance Engine:

1. **Pruned Logging (Persisted Decision Types)**:
   - Only write **`DENY`**, **`ALLOW_VIA_EXCEPTION`**, and execution-trigger **`ALLOW`** checks to the database table `governance_decision_records`.
   - General stateless read-only limit checks (e.g., from allocation solvers or optimization loops) must **NOT** be written to the database.

2. **Observability Offloading Strategy**:
   - Non-persisted stateless evaluation checks are exported directly to OpenTelemetry streams as Span Events containing the evaluation parameters, execution context, and outcome.

3. **Replayability Model**:
   - The ledger record must contain all required reference keys to reconstruct the system state at the moment of evaluation.
   - Required columns in `governance_decision_records` include `order_id` (correlation ID mapping to the execution request), `policy_version_urn`, `exception_token_urn` (if applicable), and `evaluated_at` timestamp.
   - Audit reconstruction is performed by loading the historical public keys (from `authorization_policies`) and limit rules (from `compliance_policies`) active at the `evaluated_at` timestamp.

4. **Retention Model**:
   - The decision ledger is permanent and append-only.
   - The table is range-partitioned by the `evaluated_at` timestamp on a quarterly basis to prevent index bloat and ensure fast query execution.

## Consequences
- Protects the PostgreSQL database from page bloating by reducing written rows by over 99%.
- Ensures a complete, immutable, and cryptographically valid audit trail for all order checkout executions.
- Guarantees deterministic replayability of past compliance checks.
