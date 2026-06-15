# Sprint-45 Capital Allocation Engine Foundation Architecture Challenge Review

This document contains the **Architecture Challenge Review (Round 1)** for the **Capital Allocation Engine Foundation** in Sprint-45. It analyzes potential architectural flaws, boundary violations, and replayability gaps in the current design.

---

## 1. Executive Summary
This challenge review analyzes the proposed design against the target architecture of the Virtual Investment Firm. While the plugin strategy (Option C) and trigger-based immutability lay a strong foundation, the audit reveals critical weaknesses in ranking persistence, strategy code-drift, horizon isolation, and worker lifecycle assumptions.

* **Verdict**: `ARCHITECTURE_REQUIRES_REVISION`
* **Status**: Revisions are mandatory before the architecture can be frozen.

---

## 2. Ranking Ownership Analysis
* **Challenge**: The current design proposes persisting `AllocationRank` (`rank_index`) inside the `AllocationDecisionRecord` aggregate.
* **Flaw Identified**: This introduces data duplication and synchronization bottlenecks. If one worker's score is superseded or invalidated, the rankings of the entire cohort must be recalculated. Under the current immutable design, updating `rank_index` across multiple records forces the engine to supersede all of them, causing massive write amplification.
* **Resolution**: `AllocationRank` must **NOT** be a persisted field or attribute on the aggregate. It must be computed exclusively as a transient, read-only projection reconstructed dynamically from active `AllocationDecisionRecord` scores. This eliminates cohort-wide updates and preserves write-once characteristics.

---

## 3. Strategy Replayability Analysis
* **Challenge**: Strategy plugins (Option C) support future extensions, but code adjustments (e.g. adding new weighting strategies) run the risk of causing historical calculations to drift during replays.
* **Flaw Identified**: The design lack concrete fields to pin the exact version and rules of the code used during execution.
* **Resolution**: The aggregate `AllocationDecisionRecord` must persist four explicit metadata fields:
  1. `allocation_methodology_urn`: URN of the strategy.
  2. `allocation_policy_hash`: Hash of the applied governance rules.
  3. `allocation_strategy_version`: Version string of the active strategy code.
  4. `allocation_manifest_hash`: Hash of the complete canonical serialization of inputs (Brier scores, returns, review scores) and strategy configuration.
  Replays must execute using these values to guarantee deterministic outcomes.

---

## 4. Governance Boundary Analysis
* **Challenge**: Leakage of governance rules or state ownership into the Capital Allocation Engine.
* **Flaw Identified**: Differentiating between exceptions, token hashes, and active policy lists within the allocation engine risks duplicating Governance Engine logic.
* **Resolution**: Capital Allocation must never own, mutate, or manage governance state. All governance policies and exceptions must be loaded as read-only snapshots (`CompliancePolicy` rules, active `ExceptionToken` ceilings) at session start, and their URNs must be referenced in the final allocation manifest hash.

---

## 5. Worker Lifecycle Analysis
* **Challenge**: How does worker lifecycle transitions (`ACTIVE` $\to$ `SUSPENDED` $\to$ `RETIRED` $\to$ `REACTIVATED`) affect allocations?
* **Flaw Identified**: If calculations query worker status dynamically during replay, reactivating a worker would alter historical replay output.
* **Resolution**: Historical weight calculations are immutable ledger records. Reactivation or retirement must never alter historical records. The engine must evaluate allocations using worker status *at the time of execution* (captured inside the version-pinned manifest). Worker lifecycle remains owned by the Directory/Identity context.

---

## 6. Multi-Horizon Analysis
* **Challenge**: Conflicting weights existing simultaneously across different portfolio horizons (e.g. 30D vs 365D).
* **Flaw Identified**: Lack of explicit horizon isolation within the aggregate.
* **Resolution**: The `AllocationSession` and `AllocationDecisionRecord` must be explicitly bound to a `PortfolioHorizon` value object (defining interval length and dates). Query repository methods must filter by `horizon` and `session_urn` to maintain absolute isolation and prevent cross-horizon collision.

---

## 7. Regime Integration Analysis
* **Challenge**: Potential boundary violation if the Sprint-46 Regime Engine directly manages allocations.
* **Flaw Identified**: High risk of overlapping responsibilities.
* **Resolution**: The Regime Engine will exclusively provide read-only projections and scaling signals. Capital Allocation remains the sole owner of worker weights. Sprint-46 will integrate by feeding its regime multiplier factors into Capital Allocation's strategy plugins.

---

## 8. Portfolio Ownership Analysis
* **Challenge**: Does Capital Allocation execute trades or manage cash?
* **Flaw Identified**: Boundary leak if allocation directly alters capital accounts.
* **Resolution**: Capital Allocation only outputs weight recommendations and relative worker weights. The Portfolio Management engine consumes these weights and executes cash allocation, balancing capital across actual positions.

---

## 9. Replayability Analysis
* **Challenge**: Querying mutable databases during replay.
* **Flaw Identified**: Changes or deletions in upstream tables will break replay accuracy.
* **Resolution**: Replays must be executed entirely using the inputs archived in the canonical input payload associated with the `allocation_manifest_hash` (or stored in a dedicated document repository), bypassing active database lookups.

---

## 10. Aggregate Analysis
* **Challenge**: Are transaction boundaries and OCC correct?
* **Flaw Identified**: Multi-record updates inside a single transaction could lead to database lock contention.
* **Resolution**: `AllocationSession` manages state and is persisted independently. Each `AllocationDecisionRecord` is an independent aggregate, saved individually with optimistic concurrency control (`aggregate_version`), ensuring high transaction throughput.

---

## 11. Scalability Analysis
* **Challenge**: Restructuring ranking projections for 10M+ records.
* **Flaw Identified**: Querying ranks dynamically across millions of records will cause severe latency.
* **Resolution**: Employs quarterly range partitioning on `allocated_at`. Materialized indices on `(session_urn, is_active)` enable instant cohort retrieval and projection rebuilding.

---

## 12. Knowledge Graph Analysis
* **Challenge**: Graph ingestion compatibility.
* **Resolution**: Validated. All model entities expose URNs (`urn:karsa:allocation:session:<uuid>`, `urn:karsa:allocation:record:<uuid>`) alongside UUID primary keys, ensuring compatibility with virtual graph mapping.

---

## 13. Future Compatibility Analysis
* **Challenge**: Integrating Sprint-46 (Regime) and Sprint-47 (Thesis) without modifying aggregates.
* **Resolution**: Validated. The strategy/plugin pattern (Option C) allows new factor calculation plugins to be loaded to support regime signals and thesis health metrics without changing the core schemas of Sprint-45.

---

## 14. Closed Sprint Protection Assessment
* **Review**: Upstream closed sprints (Governance, Attribution, Performance, Review) are accessed solely through read-only repositories. No modifications, migrations, or updates to closed code are requested. All protections are intact.

---

## 15. Architecture Delta Analysis
* **Gap Identified**: The persistence of `AllocationRank` inside the aggregate contradicts the target architecture's requirement for a pure, decoupled ex-post ledger.
* **Mitigation**: Removed ranking persistence from the aggregate design.

---

## 16. Required Revisions
To move to Architecture Freeze, the design must be revised to:
1. **Remove `AllocationRank`** from the persisted attributes of `AllocationDecisionRecord` and model it as a transient read-only projection.
2. **Add explicit metadata fields** (`allocation_methodology_urn`, `allocation_policy_hash`, `allocation_strategy_version`, `allocation_manifest_hash`) to the decision aggregate to ensure absolute replayability.
3. **Bind all sessions and decisions** to a `PortfolioHorizon` value object to enforce horizon isolation.

---

## 17. Final Verdict
`ARCHITECTURE_REQUIRES_REVISION`
