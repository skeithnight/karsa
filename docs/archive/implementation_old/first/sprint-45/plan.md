# Sprint-45 Capital Allocation Engine Foundation Roadmap Dependency Baseline Audit

This document establishes the dependency baseline for Sprint-45 (Capital Allocation Engine Foundation) before architecture design begins. It validates that the Capital Allocation Engine can be implemented using read-only exports from upstream bounded contexts without reopening, modifying, or extending any closed sprints.

---

## 1. Executive Summary
This baseline audit reviews the upstream exports from the sealed Governance, Attribution, Performance, and Review & Post-Mortem engines. All inputs required by the Capital Allocation Engine are verified to exist as stable, read-only exports. No schema modifications, new events, or model extensions are required in any of the closed sprints.

* **Verdict**: `ROADMAP_BASELINE_APPROVED`
* **Upstream Sprint Closures Preserved**: Sprint-41, Sprint-42, Sprint-43, and Sprint-44 remain closed and protected.

---

## 2. Governance Export Matrix
The Governance Engine (Sprint-41) owns compliance policy lifecycles, permission mappings, exception overrides, and auditing.

| Exported Artifact | Type | Consumed Attribute / Description | Repository / Interface | Read-Only Verification |
| :--- | :--- | :--- | :--- | :--- |
| **GovernanceDecisionRecord** | Aggregate | `decision_outcome` (`ALLOW`, `DENY`, `ALLOW_VIA_EXCEPTION`) | `GovernanceDecisionRecordRepository` | PASS. Consumed as read-only record. |
| **ExceptionToken** | Aggregate | `limit_ceiling`, `limit_parameter`, `expire_time`, `state` | `ExceptionTokenRepository` | PASS. Read-only token checks. |
| **CompliancePolicy** | Aggregate | Policy scope, conditions, and thresholds | `CompliancePolicyRepository` | PASS. Read-only rules matching. |

* **Ownership Status**: Retained exclusively by the Governance bounded context.
* **Write Permissions**: Prohibited. No write operations or state modifications will be requested.
* **Schema Changes**: None.

---

## 3. Attribution Export Matrix
The Attribution Engine (Sprint-42) owns realized return calculations and factor decompositions.

| Exported Artifact | Type | Consumed Attribute / Description | Repository / Interface | Read-Only Verification |
| :--- | :--- | :--- | :--- | :--- |
| **PerformanceAttributionRecord** | Aggregate | `selection_return`, `allocation_return`, `execution_return`, `beta_return`, `liquidation_tracking_residual` | `PerformanceAttributionRepository` | PASS. Read-only decimal returns consumption. |

* **Ownership Status**: Factor attribution calculation logic remains strictly owned by the Attribution engine.
* **Write Permissions**: Prohibited. Capital Allocation only consumes calculated outputs ex-post.
* **Schema Changes**: None.

---

## 4. Performance Export Matrix
The Performance Engine (Sprint-43) evaluates worker forecast calibration and accuracy.

| Exported Artifact | Type | Consumed Attribute / Description | Repository / Interface | Read-Only Verification |
| :--- | :--- | :--- | :--- | :--- |
| **WorkerEvaluationRecord** | Aggregate | `forecast_probability`, `realized_outcome`, `brier_score_component`, `realized_return` | `WorkerEvaluationRepository` | PASS. Read-only evaluations extraction. |

* **Worker Rankings ownership**: Worker ranking logic is **NOT** owned by the Performance Engine. The Capital Allocation Engine will derive worker performance weightings and rankings independently.
* **Schema Changes**: None.

---

## 5. Review Export Matrix
The Review & Post-Mortem Engine (Sprint-44) orchestrates qualitative review sessions and post-mortem syntheses.

| Exported Artifact | Type | Consumed Attribute / Description | Repository / Interface | Read-Only Verification |
| :--- | :--- | :--- | :--- | :--- |
| **ReviewRecord** | Aggregate | `decision_quality` (`outcome_independent_score`, `outcome_dependent_score`, `hindsight_bias_deviation`) | `PostgresReviewRecordRepository` | PASS. Read-only scores consumption. |
| **PostMortemRecord** | Aggregate | `failure_classification`, `success_classification`, `recommendation` | `PostgresPostMortemRecordRepository` | PASS. Read-only consensus outputs. |

* **Sizing/Allocation Information**: Confirmed that no capital sizing or allocation attributes exist in the Review context (removed during Sprint-44 revisions).
* **Schema Changes**: None.

---

## 6. Dependency Matrix
The following table maps the ex-ante and ex-post parameters required by Capital Allocation to their respective stable upstream aggregates:

| Required Input Parameter | Source Bounded Context | Source Aggregate | Source Repository | Source Field | Access Mode |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Active Policies** | Governance | `CompliancePolicy` | `CompliancePolicyRepository` | `rules` | Read-Only |
| **Active Exceptions** | Governance | `ExceptionToken` | `ExceptionTokenRepository` | `limit_ceiling` | Read-Only |
| **Realized Returns** | Attribution | `PerformanceAttributionRecord` | `PerformanceAttributionRepository` | `selection_return` | Read-Only |
| **Accuracy Score** | Performance | `WorkerEvaluationRecord` | `WorkerEvaluationRepository` | `brier_score_component` | Read-Only |
| **Qualitative Score** | Review & Post-Mortem | `ReviewRecord` | `PostgresReviewRecordRepository` | `outcome_independent_score` | Read-Only |
| **Postmortem Recommendation**| Review & Post-Mortem | `PostMortemRecord` | `PostgresPostMortemRecordRepository`| `recommendation` | Read-Only |

---

## 7. Reopen Risk Assessment
All inputs required for the Capital Allocation Engine are classified as follows:

1. **Governance Compliance status**: `ALREADY_AVAILABLE`
2. **Attribution realized returns**: `ALREADY_AVAILABLE`
3. **Performance Brier components**: `ALREADY_AVAILABLE`
4. **Review qualitative scores**: `ALREADY_AVAILABLE`
5. **Post-mortem classifications & recommendations**: `ALREADY_AVAILABLE`

* **Gaps Identified**: None. No requirements trigger a `GAP_REQUIRES_REALIGNMENT`.
* **Reopen Risk**: **Zero**. All closed sprints remain fully sealed.

---

## 8. Roadmap Compatibility Assessment
This audit verifies that the sequencing of Karsa's roadmap remains intact:
* **Sprint-41 (Governance)**: Status = CLOSED_SPRINT_PROTECTED (Unchanged)
* **Sprint-42 (Attribution)**: Status = CLOSED_SPRINT_PROTECTED (Unchanged)
* **Sprint-43 (Performance)**: Status = CLOSED_SPRINT_PROTECTED (Unchanged)
* **Sprint-44 (Review & Post-Mortem)**: Status = CLOSED_SPRINT_PROTECTED (Unchanged)

Sprint-45 can proceed directly to architecture design, preserving the closure and immutability of all previous implementation stages.

---

## 9. Architecture Delta Analysis
* **Target Architecture**: Virtual Investment Firm Target Architecture requires a decoupled Capital Allocation Engine to allocate portfolio risk budgets and determine sector capital weightings based on ex-ante bounds (Governance) and ex-post outcomes (Attribution, Performance, Review).
* **Current State Baseline**: All required ex-ante and ex-post metrics are persisted in immutable PostgreSQL tables and exposed via clean domain query repositories.
* **Delta**: No dependency gap exists. The current baseline has all prerequisites ready for the implementation of Sprint-45.

---

## 10. Findings
* All database tables representing upstream aggregates (`review_records`, `postmortem_records`, `worker_evaluation_records`, `performance_attribution_records`, `review_sessions`, etc.) are partitioned and mapped to query operations.
* Domain events published by closed sprints (e.g., `PostMortemFinalizedEvent`, `ReviewRecordRecordedEvent`) are stable and contain the correct correlation and causation URN links.
* Public ports and interfaces are cleanly structured in read-only methods.

---

## 11. Final Verdict
`ROADMAP_BASELINE_APPROVED`
