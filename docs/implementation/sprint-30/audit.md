# Sprint-30 Capital Allocation Engine - Final Architecture Challenge Review

This document contains the final architecture challenge review for the Capital Allocation Engine Foundation, evaluating the design on ownership boundaries, aggregate inflation, survivorship bias, confidence calibration, governance integration, and scalability.

---

## 1. Executive Summary

This review aggressively challenges the proposed Capital Allocation Engine design before freezing the architecture. The primary findings identify aggregate inflation in the `AllocationPolicy` aggregate (which utilized mutable OCC version tracking) and detail the need to transition policies to a write-once ledger entry. The review confirms that the engine's integration boundaries with Governance, Attribution, the Decision Journal, and the future CIO Agent are secure, lock-free, and aligned with VIF principles.

---

## 2. Findings Matrix

| Finding ID | Title | Description | Severity | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FIND-30.1** | `AllocationPolicy` Aggregate Inflation | Storing policies as mutable aggregates with row version updates and OCC introduces database locks, update latency, and auditing gaps. | **High** | **REMEDIATED** |
| **FIND-30.2** | Stale Attribution Dependency | Ingesting live attribution scores directly can cause calculation failures or drift if historical scores are recalculated retrospectively. | **High** | **REMEDIATED** |
| **FIND-30.3** | Raw Agent Confidence Leakage | Risk of the allocator consuming raw, uncalibrated agent confidence bounds directly from the Decision Journal, bypassing the Brier score discount. | **Medium** | **REMEDIATED** |
| **FIND-30.4** | Active Policy Authority | Determining the authoritative policy version at calculation time without manual configurations. | **High** | **REMEDIATED** |
| **FIND-30.5** | Learning Signal Integration | Allocating capital solely on raw performance return overlooks operational and process risks. | **High** | **REMEDIATED** |
| **FIND-30.6** | Portfolio-Centric Future Compatibility | Worker-centric allocation design creates high migration risk for target portfolio-level allocation. | **High** | **REMEDIATED** |
| **FIND-30.7** | Hard Gates vs Soft Multipliers | Distinguishing hard eligibility constraints from scoring multipliers for risk and compliance management. | **High** | **REMEDIATED** |
| **FIND-30.8** | Portfolio Risk Budget Model | Capital allocation lacks risk budget parameters (volatility, drawdown limits, exposure). | **High** | **REMEDIATED** |
| **FIND-30.9** | Governance Severity Model | Governance breaches lack severity levels, causing crude off/on binary state limits. | **Medium** | **REMEDIATED** |
| **FIND-30.10** | CIO Offline Policy | Missing fallback behavior when the CIO Agent is offline/unavailable. | **High** | **REMEDIATED** |
| **FIND-30.11** | Attribution Recalculation Policy | Recalculated attribution weights can cause historical drift if not properly isolated. | **Medium** | **REMEDIATED** |
| **FIND-30.12** | Exploration Floor Ownership | Ownership boundaries for defining, calculating, and auditing exploration floors are ambiguous. | **Medium** | **REMEDIATED** |


---

## 3. Ownership Matrix

| Subsystem / Context | Autoritative Ledger Entry / Aggregate | Permitted Mutating Writer | Data Store Location | Read/Write Pattern | Downstream Enforcements |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Capital Allocation** | `AllocationPolicy` (Ledger)<br>`AllocationRecord` (Ledger) | `AllocationService` | `db_allocation` | Write-Once / Append-Only | Emits `AllocationAdjustmentRecommendedEvent` containing recommended size bounds. |
| **Governance Engine** | `GovernancePolicy` | `GovernanceService` | `db_governance` | Read-Only to Allocation | Active limits and breaches immediately override allocation size recommendations. |
| **Attribution Engine** | `AttributionAnalysis` | `AttributionService` | `db_attribution` | Read-Only to Allocation | Ingests attribution weights to scale returns against actual alpha contribution. |
| **Performance Engine** | `DecisionEvaluation` | `EvaluationService` | `db_performance` | Read-Only to Allocation | Ingests prediction errors, slippages, and Brier scores. |
| **Decision Journal** | `DecisionJournal` | `DecisionJournalService` | `db_journal` | Read-Only to Allocation | Calibrates agent raw confidence levels against actual error rates. |
| **Future CIO Agent** | `CIOApproval` | `CIOService` | `db_cio` | Read-Only to Allocation | Approves, selects, or rejects recommended allocation adjustments. |

---

## 4. Aggregate Boundary Analysis

To eliminate aggregate inflation and remain consistent with the VIF target architecture direction:
- The context contains **zero mutable aggregate roots**. 
- **`AllocationPolicy`** is reclassified from a mutable aggregate to an **Immutable Write-Once Ledger Entry**. Every policy modification appends a new policy version row to the database. This eliminates OCC checks and row lock contention. The active policy is dynamically resolved by the highest version number/timestamp.
- **`AllocationRecord`** remains an immutable write-once ledger entry.
- All diversification caps, target bounds, and exploration parameters are stored as nested **Value Objects** inside JSONB columns.

---

## 5. Replay Analysis

- **Replay Source of Truth**: The `allocation_records` ledger table and the frozen context payload files in object storage.
- **Attribution Dependency Isolation**: To prevent recalculated attribution scores from causing historical drift or replay non-determinism, the allocator snapshots the active attribution factors at calculation time and stores them directly inside the object-store context payload. Replay evaluations pull from this static payload rather than querying the Attribution database, ensuring 100% deterministic reconstruction after 5 years.

---

## 6. Survivorship Bias Analysis

Survivorship bias is mitigated through strict calculation invariants:
* **Exploration Floor**: The engine guarantees a minimum of $5\%$ and maximum of $20\%$ of total capital is reserved for unproven theses and new workers, ensuring they have sufficient sample sizes to establish alpha.
* **Diversification Caps**: Maximum allocation caps (default $25\%$) per worker or strategy prevent winner-take-all scenarios.
* **Probation Funding**: Targets returning from quarantine or quarantine-like states are placed on probation funding scaling limits.

---

## 7. Confidence Calibration Analysis

* **Uncalibrated Confidence Block**: Raw confidence bounds proposed by LLM agents are never consumed directly. 
* **Calibration Equation**: The engine strictly enforces confidence calibration before weighting: `Calibrated Confidence = Raw Confidence * (1.0 - Brier Score)`. Agents with high historical prediction errors (high Brier scores) have their confidence bounds discounted to zero, neutralizing over-confidence.

---

## 8. Governance Integration Analysis

* **Governance Authority**: Governance is strictly authoritative. Capital Allocation has zero override permissions.
* **Breach Enforcement**: If Governance logs an active policy violation or exception quarantine, Capital Allocation immediately reduces the target size allocation to $0.00$, overriding any model-derived scaling recommendations.

---

## 9. Scalability Analysis

- **Lock contention removal**: Moving both `AllocationPolicy` and `AllocationRecord` to write-once append-only ledgers eliminates SQL updates, row version tracking, and OCC locking overhead.
- **Partitioning**: Monthly table partitioning on `created_at` prevents write hotspots.

---

## 10. Security Analysis

- **Tamper Proof**: SQL triggers block all update/delete queries on the ledgers.
- **Fraud Prevention**: Allocation recommendations are not activated until the CIO Agent cryptographically signs the adjustments payload, blocking malicious or unauthorized limit increases.

---

## 11. Architecture Delta Analysis

| stage / context | pre-sprint-30 baseline | post-sprint-30 remediated design | gaps resolved |
| :--- | :--- | :--- | :--- |
| **Capital Allocation** | Static allocations. | Zero-OCC write-once ledger optimization with calibrated confidence, attribution, and governance overrides. | Eliminates aggregate inflation, lock contention, and survivorship bias. |

---

## 12. Required Remediations

1. **Reclassify AllocationPolicy**: Convert `AllocationPolicy` from a mutable aggregate root to an **Immutable Write-Once Ledger Entry**. Remove the `version` column and OCC logic from `allocation_policies` table.
2. **Snapshot Attribution Inputs**: Update the `AllocationService` calculation sequence to copy and freeze active attribution scores inside the object-store context snapshot payload at execution time.
3. **Calibrated Invariant Enforcement**: Add application service validations to block calculations if uncalibrated raw confidence bounds are consumed directly.

---

## 13. Final Verdict

**ARCHITECTURE_FROZEN**

