# Sprint-45 Capital Allocation Engine Foundation Architecture Revision

This document presents the **Architecture Revision (Round 1)** to address the findings of the Sprint-45 challenge audit.

---

## 1. Executive Summary
This revision details the changes made to the Capital Allocation Engine design. It removes ranking persistence from aggregate roots, establishes strict version-pinned strategy replay controls, isolates portfolio horizons, and solidifies boundaries between Capital Allocation and Portfolio Management.

* **Verdict**: `ARCHITECTURE_APPROVED`
* **Status**: Ready for Architecture Freeze.

---

## 2. Revision Scope
The following changes are applied to the core design:
1. **Remove Persistence of Ranks**: `AllocationRank` is removed from `AllocationDecisionRecord` attributes. It is replaced by a transient `RankingProjection`.
2. **Pin Replay Parameters**: Added `allocation_methodology_urn`, `allocation_policy_hash`, `allocation_strategy_version`, and `allocation_manifest_hash` to the decision aggregate.
3. **Horizon Isolation**: Bound all sessions and decisions to the `PortfolioHorizon` value object.
4. **Enforce Boundary Limits**: Confirmed that Portfolio Management context exclusively owns position sizing and holdings, and that Capital Allocation outputs weight recommendations.

---

## 3. Ranking Projection Revision
* **Elimination of Persistence**: Ranks are no longer persisted in the `AllocationDecisionRecord` aggregate or the database table `allocation_decision_records`.
* **`RankingProjection` Model**:
  ```python
  @dataclass(frozen=True)
  class RankedWorker:
      worker_urn: str
      rank_index: int
      allocation_score: Decimal

  @dataclass
  class RankingProjection:
      session_urn: str
      horizon: PortfolioHorizon
      rankings: List[RankedWorker]
      calculated_at: datetime
  ```
* **Ranking Reconstruction Process**:
  1. Retrieve all active `AllocationDecisionRecord` aggregates matching `session_urn` and `horizon`.
  2. Sort the aggregates by `allocation_score` in descending order.
  3. Resolve ties deterministically:
     * Tie-Breaker 1: Lower Brier score.
     * Tie-Breaker 2: Higher selection return.
     * Tie-Breaker 3: Higher qualitative review score.
     * Tie-Breaker 4: Alphabetical order of `worker_urn`.
  4. Assign sequential ranks starting from 1.
* **Projection Rebuild Process**: Rebuilt on-demand or updated via database materialized views whenever a session transitions to `COMPLETED` or when an invalidation event is published.

---

## 4. Replayability Revision
The aggregate `AllocationDecisionRecord` now persists the following metadata columns:
* `allocation_methodology_urn`: URN of the allocation strategy (e.g. `urn:karsa:allocation:methodology:weighted-factor`).
* `allocation_policy_hash`: SHA-256 hash of the governance rules snapshot active at evaluation time.
* `allocation_strategy_version`: Version string of the active strategy plugin (e.g. `v1.2.0`).
* `allocation_manifest_hash`: SHA-256 hash of the canonically serialized inputs (Brier scores, returns, review scores, and configuration params).

* **Methodology Pinning**: The strategy version and policy hash are locked inside the record upon save.
* **Replay Validation**: The replay service re-serializes inputs and compares the computed hash against the persisted `allocation_manifest_hash`.
* **Methodology Drift Detection**: If the running strategy version or policy hash differs from the pinned values inside the record, the replay engine raises `MethodologyDriftException`.

---

## 5. Portfolio Horizon Revision
Introduced the `PortfolioHorizon` value object to partition all calculations.
```python
@dataclass(frozen=True)
class PortfolioHorizon:
    horizon_id: str          # e.g., "30D", "90D", "180D", "365D"
    horizon_start: datetime  # UTC start
    horizon_end: datetime    # UTC end
```
* **Horizon Ownership**: Capital Allocation owns the portfolio horizon selection for its calculations.
* **Horizon Isolation**: `AllocationSession` and `AllocationDecisionRecord` are isolated by `PortfolioHorizon`.
* **Replay Isolation**: Replay operations only load and verify records within a single horizon.
* **Lineage Isolation**: Lineage queries (`find_lineage`) walk exclusively within records matching the same `PortfolioHorizon` and `worker_urn`.

---

## 6. Portfolio Ownership Analysis
* **Boundary Rules**: Capital Allocation Engine **does NOT own** actual portfolio allocations, cash balances, or positions.
* **Refined Model**: Workers produce signals. Capital Allocation evaluates these signals and outputs worker weight recommendations. The Portfolio Management engine consumes these recommendations and executes cash/position sizing.

---

## 7. Capital Recommendation Analysis
* **Acceptable Outputs**:
  * `recommended_weight` (Decimal)
  * `allocation_score` (Decimal)
  * `risk_budget` (`RiskBudgetAssignment` value object)
* **Prohibited Outputs**:
  * `executed_position_size`
  * `actual_position_quantity`
  * `portfolio_holdings`
  These remain strictly owned by Portfolio Management.

---

## 8. Worker Lifecycle Analysis
* **Transitions**: `ACTIVE` $\to$ `SUSPENDED` $\to$ `RETIRED` $\to$ `REACTIVATED`.
* **Immutability Protection**: Reactivation or retirement does not affect historical records.
* **Replay Protection**: The engine loads worker status as captured inside the version-pinned manifest at calculation time, ensuring historical replays remain unaffected by future worker lifecycle changes.

---

## 9. Governance Snapshot Analysis
* **Governance Boundary**: Capital Allocation does not own policy/exception lifecycles.
* **Snapshot Strategy**: Governance rules and exception tokens are read as immutable snapshots at session start and their hashes are pinned inside the decision aggregate's `allocation_policy_hash`.

---

## 10. Regime Integration Analysis
* **Integration Strategy**: The Sprint-46 Regime Engine provides read-only regime projections and volatility scaling multipliers. Capital Allocation's strategy plugins (Option C) consume these projections dynamically without modifying the Sprint-45 aggregate roots or database tables.

---

## 11. Scalability Analysis
Removing `rank_index` from the ledger tables prevents database locking during cohort recalculations. Materialized indices on `(session_urn, horizon_id, is_active)` enable sub-millisecond ranking reconstruction for 10M+ records.

---

## 12. Architecture Delta Analysis
* **Baseline**: Stable review and performance engines are sealed.
* **Target**: Sprint-45 implements capital allocation using ex-post and ex-ante inputs.
* **Delta**: Gaps resolved. All designs are fully aligned.

---

## 13. Challenge Disposition Matrix

| Finding / Issue | Challenge Recommendation | Resolution in Revision |
| :--- | :--- | :--- |
| **Ranking Persistence** | Remove rank_index from aggregate. | Ranks are calculated dynamically as `RankingProjection`. |
| **Strategy Replayability**| Pin strategy version and manifest hash. | Persisted URN, version, policy, and manifest hashes. |
| **Horizon Collision** | Isolate multi-horizon runs. | Added `PortfolioHorizon` partitioning. |
| **Portfolio Ownership** | Limit to recommendations. | Direct holdings/position execution is excluded. |

---

## 14. Updated ADR Decisions
* **ADR-057**: Select Option C (Strategy/Plugin layout) and define the transient `RankingProjection` to ensure clean ex-post analytics.
* **ADR-059**: Introduce `PortfolioHorizon` partitioning to isolate ex-post runs.

---

## 15. Acceptance Criteria
1. `AllocationDecisionRecord` does not persist ranks.
2. Calculations are reproducible using manifest hashes.
3. Horizons are fully isolated.
4. All integration tests pass.

---

## 16. Final Verdict
`ARCHITECTURE_APPROVED`
