# ADR-048: CIO Decision and Orchestration Model

## Status
Frozen

## Date
2026-06-14

## Context
Designing the decision orchestrator for the Virtual Investment Firm (VIF) requires a model that handles conflicting recommendations, resolves concurrency, and ensures that a portfolio configuration from 5 years ago can be reconstructed with absolute audit integrity. We must evaluate direct worker allocations versus hierarchical models, decide whether the CIO context requires mutable aggregate roots, design conflict resolution models, and support human and agent acting roles.

## Decision
We implement the following CIO decision and orchestration model:

1. **Portfolio Projection Model**:
   - The CIO context contains **zero mutable aggregate roots**. 
   - The "Portfolio" is **not** a first-class mutable write-model entity. Instead, it is a **read-side projection** compiled out-of-band.
   - All decisions are written to the write-once append-only `cio_decisions` ledger. A Change Data Capture (CDC) worker projects these entries to a read-side snapshot table `portfolio_states` and Redis cache, enabling lock-free, highly scalable writes ($100\text{M}+$ daily event capability) and $O(1)$ read lookups.

2. **CIODecision Structural Design Evaluation**:
   - **Option A (Mutable Aggregate with State Machine & OCC)**: Rejected. Requires database row-locking and optimistic concurrency checks, creating major write hotspots under concurrent agent signals.
   - **Option B (Immutable Decision Ledger - Selected)**: The context contains zero mutable state machines. Every decision is an append-only, write-once ledger entry. Transitions are logged as new entries, completely eliminating database locks and OCC overhead.
   - **Metrics Comparison**:
     - *Replayability*: Option B is 100% replayable by re-indexing append logs. Option A risks historical overwrite loss.
     - *Scalability*: Option B scales linearly. Option A locks on concurrent updates.
     - *Auditability*: Option B preserves an immutable, chronological trail. Option A overwrites state.
     - *Multi-Agent Compatibility*: Option B allows lock-free parallel writes by multiple concurrent agents.

3. **Hierarchical Portfolio Construction**:
   - We enforce the `Portfolio -> Strategy -> Thesis -> Decision -> Worker` construction model. Direct worker-only allocation is rejected.

4. **Precedence-Multiplier Conflict Resolution Framework**:
   - Competing recommendations are resolved using a deterministic mathematical model:
     $$A_{raw} = A_{base} \times W_{pm} \times W_{rev} \times \left(1.0 + \sum_{i} (Signal_{i} \times (1.0 - Brier_{i})) \times 0.1\right)$$
     $$A_{final} = \min(A_{raw}, Cap_{gov})$$
   - Precedence Order:
     1. **Governance Hard Stop**: Cuts allocation to 0.0 ($W_{gov\_stop} = 0.0$).
     2. **CIO Override Decision**: Applies manual strategic override values.
     3. **Governance Soft Limit / Warning**: Caps limits ($Cap_{gov}$).
     4. **Post-Mortem Failure Weight**: Multiplier penalty ($W_{pm}$).
     5. **Capital Allocation Model**: Base proposed weight ($A_{base}$).
     6. **Review Engine Score**: Multiplier penalty ($W_{rev}$).
     7. **Analyst Signals**: Weighted direction scaled by Decision Journal Brier scores.
   - **Tie-Breaking**: Broken by consensus trend, followed by risk-contribution minimization, and defaulting to passive cash.
   - **Escalation**: Defunds and creates a Governance review ticket if $A_{final}$ falls below the economic threshold.

5. **Unified Decision Contract**:
   - Both Human and Agent CIO actors use the same decision workflow and emit identical event schemas. Differentiated cryptosigners are verified at the PEP: human actions are signed using WebAuthn/HSM keys; agent actions are signed using KMS-managed service keys.

6. **Replay Lineage Chain**:
   - Complete determinism is proven by tracing: `Research -> Thesis -> Decision Journal -> Attribution -> Governance -> Allocation -> CIO Decision -> Execution`.
   - Each hop logs its parent `causation_id` and the overall `correlation_id` in immutable databases, allowing historical reconstruction.

## Consequences
- **Lock-Free Scaling**: The write-path operates without Optimistic Concurrency Control (OCC) locking overhead.
- **Traceability**: Audit paths recursively trace execution events back to research signals.
- **Unified Security**: Downstream engines verify a single decision contract regardless of the signer role.
