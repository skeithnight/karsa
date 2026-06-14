# ADR-050: Execution Engine Bounded Context and PEP Architecture

## Status
Approved

## Date
2026-06-14

## Context
As Karsa transitions to the target Virtual Investment Firm (VIF) architecture, we need to design the **Execution Engine** to serve as the authoritative Policy Enforcement Point (PEP) for all outbound portfolio actions. The design must handle high-throughput trade events (100M+ ecosystem events/day), enforce compliance checks, and support future multi-broker integrations while preserving 100% replay determinism.

## Decision
We enforce the following architectural rules:

1. **Immutable Execution Ledger Model (Option B)**:
   - The Execution Engine contains **zero mutable aggregates**. 
   - We reject Option A (Mutable Order Aggregate) in favor of **Option B (Immutable Execution Ledger)**. 
   - All state transitions (Staged, Routed, Filled, Cancelled) are written as append-only records in `execution_requests`, `routing_records`, and `fill_records`. Projections compile the active order state asynchronously. This guarantees lock-free database scaling and absolute auditability.

2. **Policy Enforcement Point (PEP) Architecture**:
   - The Execution Engine acts as the absolute PEP. No trades can reach external brokers without passing through the PEP.
   - The PEP performs dual-signature checks before routing:
     $$\text{Authorized} \iff \text{Verify}(Sig_{CIO}, Payload) \land (\text{WithinDefaultBounds}(Payload) \lor \text{Verify}(Sig_{Gov}, ExceptionPayload))$$
   - Any order failing validation is immediately written to the ledger as `REJECTED` and generates an `ExecutionIncidentEvent`.

3. **Broker Abstraction Model**:
   - The Execution Engine defines a uniform broker integration contract.
   - Broker-specific adapters (Paper, Simulator, Live brokers) implement this interface, translating internal order payloads to vendor-specific protocols (e.g., FIX, REST).

4. **Strict Execution vs. Portfolio Boundary**:
   - The Execution Engine owns **transactional facts** (orders, routes, fills, commissions).
   - The Portfolio Engine owns the **resulting state** (positions, cash balances, NAV, factor/sector exposures).
   - The Portfolio Engine updates its holdings book by consuming the `OrderFilledEvent` emitted by the Execution Engine, ensuring zero direct dependency on mutable execution state.

## Consequences
- **High Concurrency**: Database write contention is eliminated since the write path uses only append-only INSERTs.
- **Auditable Trajectory**: The complete path of an order—from staging, PEP validation, routing, to fills—is written in stone.
- **Fail-Closed Security**: If validation fails or signatures are corrupted, the PEP rejects the order, protecting the firm's capital.
