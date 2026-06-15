# Sprint-45 Capital Allocation Engine Foundation Architecture Revision (Round 2)

This document presents the **Architecture Revision (Round 2)** to address the findings of the Sprint-45 Round 2 challenge review.

---

## 1. Executive Summary
This revision details the structural enhancements to guarantee absolute, drift-free replayability and deterministic version lineages. We introduce explicit linked-list pointers to aggregate roots, isolate replay logic from active database queries, and define a deterministic tie-resolution chain.

* **Verdict**: `ARCHITECTURE_APPROVED`
* **Status**: Ready for final freeze.

---

## 2. Revision Scope
1. **Explicit Lineage Pointers**: Added `supersedes_record_urn` and `invalidates_record_urn` to `AllocationDecisionRecord` to construct a deterministic linked list.
2. **Isolated Replay Validation**: Replay operates strictly on the calculation manifest snapshot payload, prohibiting runtime queries to external tables.
3. **Deterministic Ranking Chain**: Defined a five-factor ranking sequence ending in alphabetical `worker_urn` sorting to guarantee stable tie resolution.

---

## 3. Lineage Revision
The aggregate `AllocationDecisionRecord` is augmented with explicit predecessor pointers:
```python
# Expanded attributes of AllocationDecisionRecord
self.supersedes_record_urn = supersedes_record_urn  # Optional[str]
self.invalidates_record_urn = invalidates_record_urn  # Optional[str]
```
* **Deterministic Lineage Walk (`V1 → V2 → V3`)**:
  * Record V1: `supersedes_record_urn = None`, `invalidates_record_urn = None`, `is_active = False`
  * Record V2: `supersedes_record_urn = V1.record_urn`, `invalidates_record_urn = None`, `is_active = False`
  * Record V3: `supersedes_record_urn = None`, `invalidates_record_urn = V2.record_urn`, `is_active = True`
* **Lineage Ingestion**: Enables graph engines to construct linear `:SUPERSEDES` and `:INVALIDATES` relations without sorting on database timestamps or transaction execution order.

---

## 4. Replay Revision
* **Manifest Replay Rule**: During `verify_replay()`, the `AllocationReplayService` loads only the canonically serialized manifest payload that was associated with the record's `allocation_manifest_hash` during creation.
* **Prohibited Operations**: The replay engine is prohibited from executing:
  * Runtime SQL queries to the `workers` or directory tables.
  * Lookups of active `CompliancePolicy` records or exceptions.
  * Active queries of performance `WorkerEvaluationRecord` or `ReviewRecord` tables.
* **Data Guarantee**: All historical inputs, worker states, and parameters are encapsulated inside the manifest payload. This guarantees that calculations executed today can be reproduced identically 5 years later, even if the database state has changed.

---

## 5. Ranking Revision
The transient `RankingProjection` reconstructs rankings using a strict, five-factor sorting chain:
1. **Allocation Score**: Higher raw score is ranked higher (Descending).
2. **Brier Score**: Lower Brier score (higher forecast accuracy) is ranked higher (Ascending).
3. **Selection Return**: Higher selection effect return is ranked higher (Descending).
4. **Review Score**: Higher qualitative outcome independent score is ranked higher (Descending).
5. **Worker URN**: Alphabetical sort of URN strings is used as the final tie-breaker (Ascending).

This ensures that the derived `rank_index` is stable and reproducible across all rebuilds and runs.

---

## 6. Governance Snapshot Verification
* **Scenario**: A policy is modified (e.g. `max_worker_weight` drops from 40% to 20%) after an allocation decision is saved.
* **Verification**:
  * The historical allocation record was computed using the 40% cap, which was serialized into its manifest.
  * Replaying the historical record uses the snapshotted 40% rule.
  * The historical replay returns the exact same weight, bypassing the active 20% rule.

---

## 7. Worker Lifecycle Verification
* **Scenario**: Worker-A is `ACTIVE` during allocation calculation, subsequently `RETIRED`, and later `REACTIVATED`.
* **Verification**:
  * The historical record remains untouched.
  * Replay loads the snapshot manifest where Worker-A's state was recorded as `ACTIVE`.
  * Replay outputs the exact original weights, completely unaffected by subsequent transitions.

---

## 8. Regime Compatibility Verification
* **Scenario**: Sprint-46 introduces market regime scaling multipliers.
* **Verification**:
  * Multipliers are passed as input parameters to the strategy plugin.
  * The aggregate structures of `AllocationSession` and `AllocationDecisionRecord` remain untouched.
  * Input values are stored in the manifest, preserving full replay compatibility.

---

## 9. Architecture Delta Analysis
* **Delta Resolved**: Shifted from timestamp-dependent lineage ordering to explicit aggregate linked-list pointers (`supersedes_record_urn` and `invalidates_record_urn`).

---

## 10. Challenge Disposition Matrix

| Finding / Issue | Challenge Recommendation | Resolution in Revision |
| :--- | :--- | :--- |
| **Implicit Lineage** | Replace timestamp sequencing with explicit pointers. | Added `supersedes_record_urn` and `invalidates_record_urn`. |
| **Replay Snapshot** | Restrict replay to manifest contents only. | Bypassed active DB queries during replay verification. |
| **Ranking Tie-breaks**| Enforce stable tie-breaker sequence. | Terminated tie-breaker chain with alphabetical URN. |

---

## 11. Updated ADR Decisions
* **ADR-060**: Require explicit linked-list lineage references in all write-once aggregates.
* **ADR-061**: Enforce absolute manifest isolation for all ex-post replay services.

---

## 12. Acceptance Criteria
1. Lineage walks walk the linked list via `supersedes_record_urn` and `invalidates_record_urn`.
2. Replay checks do not hit the active database.
3. Ranks are derived deterministically.
4. Closed sprints are untouched.

---

## 13. Final Verdict
`ARCHITECTURE_APPROVED`
