# ADR-047: CIO Engine Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
As Karsa evolves toward the Virtual Investment Firm (VIF) target architecture, multiple subsystems produce signals, recommendations, and reviews, but there is no authoritative portfolio-level decision maker.

To prevent context overlap, operational bottlenecks, and conflict resolution failures, we must define the boundaries of the **CIO Engine Bounded Context** and establish rules for what it owns, what it does not own, and how it interacts with Governance and Capital Allocation.

## Decision
We enforce the following boundaries and ownership rules:

1. **CIO Bounded Context Ownership**:
   - The **CIO Engine** is the sole writer and authoritative subsystem for portfolio decisions (`cio_decisions` ledger) and the active portfolio hierarchy configuration.
   - It **does not** execute trades, write transactional execution books, compute quantitative allocations, validate policy compliance, or log raw performance metrics.
   - It is a **decision maker**, not an execution engine. It generates cryptographically signed authorization payloads that the Execution Engine must consume to update live trading limits.

2. **Strict Portfolio-Centricity**:
   - The CIO Engine operates strictly on a portfolio-centric construction model: `Portfolio -> Strategy -> Thesis -> Decision -> Worker`. Direct worker-only allocation is rejected.

3. **Governance is Authoritative (Zero CIO Override)**:
   - The CIO Engine has **zero** override authority over the Governance Engine. If a thesis or worker triggers a governance `HARD_STOP` violation, it is defunded immediately. To bypass standard policy bounds, the CIO must submit a formal Exception Request to the Governance Engine for validation and signing.

4. **Capital Allocation Bounded Separation**:
   - The CIO Engine cannot modify historical or active allocation engine records. It consumes them as read-only proposals and writes approval or rejection decisions to its own ledger.

## Consequences
- **Decoupled Orchestration**: Strategic allocation adjustments are separated from compliance validations and raw trading pipelines.
- **Traceable Authority**: All adjustments are signed cryptographically, establishing a tamper-proof audit trail of executive decisions.
- **Absolute Compliance**: Governance guardrails remain final and authoritative.
