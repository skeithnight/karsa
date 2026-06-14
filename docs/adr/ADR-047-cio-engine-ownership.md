# ADR-047: CIO Engine Context Boundaries and Ownership

## Status
Frozen

## Date
2026-06-14

## Context
As Karsa evolves toward the Virtual Investment Firm (VIF) target architecture, multiple subsystems produce signals, recommendations, and reviews, but there is no authoritative portfolio-level decision maker. To prevent context overlap, operational bottlenecks, and conflict resolution failures, we must define the boundaries of the **CIO Engine Bounded Context** and establish rules for what it owns, what it does not own, and how it interacts with Governance and Capital Allocation.

## Decision
We enforce the following boundaries and ownership rules:

1. **CIO Bounded Context Ownership**:
   - The **CIO Engine** is the sole writer and authoritative subsystem for portfolio decisions (`cio_decisions` ledger) and the active portfolio hierarchy configuration.
   - It is a **decision maker**, not an execution engine. It generates cryptographically signed authorization payloads that the Execution Engine must consume to update live trading limits.
   - The CIO Engine **does NOT**:
     - calculate allocations
     - optimize allocations
     - mutate allocation ledgers
     - execute trades directly
     - evaluate compliance policies outside the exception flow

2. **Strict Portfolio-Centricity**:
   - The CIO Engine operates strictly on a portfolio-centric construction model: `Portfolio -> Strategy -> Thesis -> Decision -> Worker`. Direct worker-only allocation is rejected.

3. **Governance is Authoritative (Zero CIO Override)**:
   - The CIO Engine has **zero** override authority over the Governance Engine. If a thesis or worker triggers a governance `HARD_STOP` violation, it is defunded immediately.
   - To bypass standard policy bounds, the CIO must submit a formal `GovernanceExceptionRequest` to the Governance Engine PDP. If approved, the Governance Engine signs an Exception token, which the CIO appends to the authorized decision payload.

4. **Capital Allocation Boundary Options Evaluation**:
   - **Option A (CIO modifies allocation values)**: Rejected. Risks violating portfolio covariance and risk-budget constraints, breaking optimization consistency.
   - **Option B (CIO approves/rejects allocation recommendations)**: Rejected. Lacks a feedback loop, causing execution deadlocks upon rejection.
   - **Option C (CIO approves/rejects and requests recalculation)**: Selected. Capital Allocation owns optimization solvers, calculations, and recommendation generation. The CIO serves solely as the gatekeeper. On rejection, it requests recalculation, passing new constraint parameters to the Capital Allocation Engine (e.g., `exclude_worker_ids = ["worker_risk_02"]`).

5. **Explicit Out-of-Bounds Restrictions (God Context Mitigation)**:
   - The CIO context is strictly isolated. It cannot execute trades directly, calculate optimal asset weights from raw return models, or evaluate compliance policies outside of the formal Governance request pipeline.

## Consequences
- **Decoupled Orchestration**: Strategic allocation adjustments are separated from compliance validations and raw trading pipelines.
- **Traceability**: All adjustments are signed cryptographically, establishing a tamper-proof audit trail of executive decisions.
- **Absolute Compliance**: Governance guardrails remain final and authoritative.
- **Feedback Loops**: Capital Allocation can respond to structured recalculation requests rather than stalling on rejection.
