# ADR-052: CIO Engine Authority and Ledger Design

## Status
Approved

## Date
2026-06-14

## Context
During the Sprint-37 closure audit, the repository was found to operate with isolated bounded contexts. In particular:
1. The Execution Engine verified trade requests against mock signature adapters in [test_execution.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/execution/test_execution.py#L45).
2. The Decision Journal captured pre-outcome reasoning expectations in isolation, but no downstream context checked or consumed these records.
3. The Performance Engine calculated Brier scores using hardcoded benchmarks instead of loading confidence values from the journal.

To transition Karsa to a production-ready state, we need to design the **CIO Engine** as the authoritative control plane that bridges the Decision Journal and the Execution Engine. This decision record establishes the cryptographic signature model, single-aggregate ledger boundaries, committee vote orchestration, and historical replay constraints.

## Decision
We implement the following architectural decisions for the CIO Engine Foundation:

1. **Authoritative Signature Payload Structure**:
   - The CIO Engine generates Ed25519 signatures over a combined payload containing:
     $$\text{Payload} = \text{decision\_id} \mid \text{target\_node\_id} \mid \text{allocated\_weights} \mid \text{portfolio\_snapshot\_hash} \mid \text{governance\_exception\_id}$$
   - The `portfolio_snapshot_hash` is the SHA-256 hash of the active portfolio state prior to the decision, locking the decision to a specific base state and preventing replay under drift.
   - The `decision_id` MUST correspond to a sealed record in the Decision Journal. The database schema enforces a `UNIQUE` constraint on the `decision_journal_ref` column in the `cio_decisions` table to guarantee a strict 1:1 cardinality.
   - The Execution PEP will verify this signature and validate the presence of the Decision Journal reference to prevent "phantom executions."
   - Signatures are generated at **consensus approval time** (when the ledger record is written) rather than publication time, preventing post-approval modifications.

2. **Single Aggregate Boundary**:
   - The CIO context implements a single aggregate root: `CIODecisionAggregate` (represented by the `cio_decisions` table). All data modifications are append-only.
   - The active portfolio state is compiled asynchronously as a read-side projection (`portfolio_states` and Redis cache), removing all database locks.

3. **Committee Votes Ownership**:
   - Committee votes belong inside the `CIODecisionAggregate` boundary as value objects. They are part of the input validation required to satisfy the quorum before a decision is sealed and signed. They do not reside in a separate context.

4. **Target Allocations Boundary**:
   - Target allocations are computed and owned by the **Capital Allocation Engine**. The CIO Engine only owns the *approval/rejection state* of these proposals. On rejection, the CIO requests recalculation, passing constraints (Option C).

5. **Override and Exception Ownership**:
   - Allocation overrides are manual decisions owned and signed by the CIO Engine.
   - Compliance exceptions are owned and signed exclusively by the **Governance Engine**. The CIO Engine must request exception tokens when soft policy limits are breached.

## Consequences
- **Elimination of Mocks**: The Execution PEP will transition to validating cryptographically signed CIO decisions containing real Decision Journal references.
- **Replayability**: Replaying the state from 5 years ago is guaranteed by reconstructing the portfolio projections chronologically from the immutable ledger logs.
- **Integrity**: The 1:1 relationship between a CIO Decision and a Decision Journal entry ensures that reasoning is locked to trading outcomes.
