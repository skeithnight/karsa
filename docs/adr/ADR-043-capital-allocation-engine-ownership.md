# ADR-043: Capital Allocation Engine Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
Karsa's Virtual Investment Firm (VIF) requires a formal bounded context for optimizing virtual capital distribution. Historically, portfolio weighting and funding limits were adjusted manually or statically. 

Adding dynamic capital allocation requires a dedicated **Capital Allocation Engine Bounded Context**. To prevent context overlap and ensure system safety, we must establish strict boundaries, single-writer rules, and integration contracts with the rest of the VIF engines.

## Decision
We enforce the following context boundaries and ownership rules:

1. **Capital Allocation Context Ownership**:
   - The **Capital Allocation Engine** is the sole writer and authoritative subsystem for the `AllocationPolicy` (Immutable Ledger Entry) and `AllocationRecord` (Immutable Ledger Entry). The context contains zero mutable aggregate roots.
   - It **does not** execute trades, write portfolio execution ledgers, or enforce real-time compliance limits.

2. **Integration Boundaries & Single-Writer Constraints**:
   - **Performance Engine Integration**: Read-only return rates and Brier scores are consumed by Allocation during calculations.
   - **Attribution Engine Integration**: Read-only attribution scores are ingested by Allocation to isolate true alpha contribution.
   - **Governance Engine Integration**: Governance is authoritative. Policy limits and breaches immediately constrain recommended sizes. Allocation cannot override governance limits.
   - **Decision Journal Integration**: Read-only reasoning and calibrated confidence bounds are pulled.
   - **CIO Agent Integration**: Allocation publishes recommendations via `AllocationAdjustmentRecommendedEvent`. The future CIO Agent approves or rejects adjustments by publishing `AllocationApprovedEvent`. The actual portfolio limit execution is triggered by this approval.

3. **Active Policy Authority**:
   - The active policy is resolved using a **Governance-Validated, CIO-Signed Policy** model. Any new policy version appended to the ledger must refer to a `governance_policy_decision_id` and contain a cryptographic `cio_signature`. At calculation runtime, the latest version meeting both conditions is resolved.


## Consequences
- **Decoupled Optimization**: Budgeting optimizations run out-of-band without locking the active trading paths.
- **Authority Enforcement**: Governance constraints are strictly preserved.
- **VIF Consistency**: Architectural compliance is maintained through asynchronous event integrations.
