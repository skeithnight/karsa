# Sprint-45 Capital Allocation Engine Foundation Architecture Challenge Review (Round 2)

This document contains the **Architecture Challenge Review (Round 2)** for the **Capital Allocation Engine Foundation** in Sprint-45. It tests the revised design under aggressive operational scenarios.

---

## 1. Executive Summary
This second challenge review analyzes the revised design against version lineages, 5-year replayability, concentration risk limits, and future regime integrations. While the transient ranking projection and policy pinning are successful, the audit identifies weaknesses in lineage traversal without sequence identifiers, concentration enforcement boundaries, and replay snapshot boundaries.

* **Verdict**: `ARCHITECTURE_REQUIRES_REVISION`
* **Status**: Revisions are required to finalize the freeze eligibility.

---

## 2. Allocation Lineage Challenge
* **Challenge**: Reconstructing lineage during complex recomputations (e.g. V1 $\to$ superseded by V2 $\to$ invalidated by V3) without relying on database timestamps.
* **Flaw Identified**: Depending on timestamps (`allocated_at`) to order versions is vulnerable to NTP synchronization drift, batch execution within the same millisecond, and database transaction ordering anomalies.
* **Resolution**: The `AllocationDecisionRecord` aggregate must include an explicit, deterministic pointer to its predecessor:
  * `supersedes_record_urn`: URN of the specific record it supersedes.
  * `invalidates_record_urn`: URN of the specific record it invalidates.
  This establishes a true linked list in the ledger records, allowing lineage to be walked deterministically without timestamp inference.

---

## 3. Replayability Analysis
* **Challenge**: Exact replication of recommendations 5 years later, despite worker retirement, strategy upgrades, or policy modifications.
* **Flaw Identified**: If a strategy plugin references external catalogs or status queries during replay, changes to those systems over 5 years will cause replay calculations to drift.
* **Resolution**: The canonical manifest payload associated with `allocation_manifest_hash` must encapsulate the complete snapshot of all inputs, worker statuses, and parameters. The replay engine must execute purely using this manifest as its data source, avoiding any runtime database queries to external tables.

---

## 4. Concentration Risk Analysis
* **Challenge**: What prevents a single worker from receiving 95% weight? Who owns concentration limits?
* **Flaw Identified**: Overlapping boundaries in limit enforcement. If Capital Allocation decides limits, it leaks Governance logic.
* **Resolution**: 
  * **Governance Bounded Context** owns the definition of concentration limits (e.g. `max_worker_weight = 40%`) as policies.
  * **Capital Allocation Bounded Context** is responsible for *enforcing* these limit rules during the execution of its allocation strategy (capping recommended weights to conform to limits).
  * **Replay implications**: The limits used to cap weights are recorded inside the pinned `allocation_policy_hash`.

---

## 5. Governance Constraint Analysis
* **Challenge**: If policy rules change (e.g. sector limits change), does historical replay still succeed?
* **Flaw Identified**: Replaying historic calculations against active rules causes mismatches.
* **Resolution**: The strategy must read rules from the snapshotted parameters stored in the methodology manifest. Replays run strictly against these historic snapshotted constraints, ignoring live policy changes.

---

## 6. Portfolio Boundary Analysis
* **Challenge**: Capital Allocation leaking into Portfolio Management.
* **Resolution**: Validated. The engine output is strictly limited to weight recommendations, risk budgets, and scores. It has no access to executed positions, transaction ledgers, or execution orders.

---

## 7. Ranking Projection Analysis
* **Challenge**: Can rankings be reconstructed deterministically under all tie conditions?
* **Flaw Identified**: If a tie persists through all factor checks, rank index order becomes non-deterministic.
* **Resolution**: The tie-breaking chain must terminate with `worker_urn` (which is unique and alphabetically sortable). This ensures absolute determinism for rankings under all conditions.

---

## 8. Regime Compatibility Analysis
* **Challenge**: Can Sprint-46 Regime multipliers be integrated without schema changes?
* **Resolution**: Yes. The strategy/plugin pattern (Option C) receives regime signals as input variables. The aggregate schema is generic and does not contain explicit "regime" columns, avoiding any modification to Sprint-45 aggregates.

---

## 9. Scalability Analysis
* **Challenge**: Query cost of lineage traversal and ranking reconstruction for 10M+ records.
* **Flaw Identified**: Traversing a recursive lineage tree via SQL is highly inefficient.
* **Resolution**: Quarterly range partitioning restricts the search space. Indexes on `(worker_urn, horizon_id)` allow the application to retrieve all version nodes for a worker in a single flat query and rebuild the lineage linked-list locally in memory.

---

## 10. Knowledge Graph Analysis
* **Challenge**: Graph ingestion compatibility.
* **Resolution**: Validated. The inclusion of `supersedes_record_urn` and URN IDs allows graph databases to ingest records as nodes and form `:SUPERSEDES` relationships directly without any parsing.

---

## 11. Future Compatibility Analysis
* **Challenge**: Sprint-46 and Sprint-47 integration.
* **Resolution**: Validated. Pluggable strategies ensure future compatibility without modifying the aggregate roots of Sprint-45.

---

## 12. Closed Sprint Protection Assessment
* **Review**: All closed sprints remain protected. No writes or schema migrations are proposed on Sprint-41 through Sprint-44 tables.

---

## 13. Architecture Delta Analysis
* **Gap**: Lineage reconstruction was dependent on timestamp sequence inference.
* **Mitigation**: Switched to explicit `supersedes_record_urn` aggregate pointers.

---

## 14. Required Revisions
To freeze the architecture, the design must incorporate:
1. **Explicit Predecessor Pointers**: Add `supersedes_record_urn` and `invalidates_record_urn` to `AllocationDecisionRecord` attributes.
2. **Deterministic Tie-Breaking**: Explicitly append unique `worker_urn` sorting as the final tie-breaker.
3. **Encapsulated Manifest Replay**: Specify that the replay engine runs purely on the manifest snapshot, excluding active runtime lookups.

---

## 15. Final Verdict
`ARCHITECTURE_REQUIRES_REVISION`
