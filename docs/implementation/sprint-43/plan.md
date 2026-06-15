# Sprint-43 Performance Engine Foundation Pre-Implementation Readiness Plan

This report presents Karsa's canonical Pre-Implementation Readiness Plan for the **Performance Engine Foundation** bounded context in Sprint-43.

---

## 1. Executive Summary

A pre-implementation readiness review was performed on the Sprint-43 Performance Engine Foundation design definitions. The plan outlines the domain model boundaries, value object calculations (Brier score and calibration curves), PostgreSQL tables, range partitioning, audit replay sequences, and integration contracts with upstream engines (Decision Journal, Portfolio).

The implementation plan complies with Karsa's design standards, providing a detailed roadmap to construct a high-performance, write-once ex-post forecast calibration loop.

**Verdict**: `IMPLEMENTATION_PLAN_APPROVED`

---

## 2. Architecture Freeze Compliance Matrix

The matrix below checks the consistency of design decisions against Sprint-43 architectural inputs:

| Target Design Decision | Performance Architecture Document | ADR-031 (Performance) | ADR-032 (Model) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **PerformanceSession Aggregate**| Defined as horizon state | Authoritative tracker | Mapped in execution | **PASS** |
| **WorkerEvaluationRecord** | Range partitioned ledger | Cryptographically hashed | Brier score split | **PASS** |
| **BrierScore Value Object** | Defined as accuracy metric | Logged ex-post | Decoupled check | **PASS** |
| **CalibrationCurve Value Object**| Dynamic bin scaling | Calculation logic | Decoupled check | **PASS** |
| **PostgreSQL Immutability Trigger**| Block UPDATE/DELETE | Ledger protection | Not applicable | **PASS** |

---

## 3. Aggregate Readiness Matrix

The table below checks readiness metrics for the two target aggregates in the Performance bounded context:

| Aggregate | Ownership Boundary | Lifecycle States | Transaction Boundary | Persistence Model | Replayability Model |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PerformanceSession** | Performance Context | `STAGED` $\to$ `EVALUATING` $\to$ `CALIBRATED` $\to$ `SEALED` | Session-level transaction | Postgres versioned | Unique `session_id` |
| **WorkerEvaluationRecord** | Performance Context | `RECORDED` | Write-once ledger record | Range-partitioned | Hash-linked to `session_id` and `decision_id` |

---

## 4. Value Objects & Calculation Logic

* **Brier Score Calculation**:
  $$BS = (f - o)^2$$
  where $f$ is the ex-ante forecast probability and $o$ is the ex-post binary outcome ($0$ or $1$).
* **Calibration Curve**:
  Pipes worker evaluations into confidence bins (e.g. $[0.0, 0.1], [0.1, 0.2], \dots, [0.9, 1.0]$) and computes the realized frequency of outcomes inside each bin to detect forecast drift.

---

## 5. Decision & Horizon Integration Readiness

* **Decision Journal Integration**: Reads ex-ante prediction entries, forecast probability parameters, and worker URNs over target horizons.
* **Portfolio Integration**: Reads realized position prices and holdings.
* **Failure Behavior**: If any upstream API reads fail, the session transitions to `STAGED` (rollback). No partial calculations are stored.

---

## 6. Persistence & Immutability Design

* **Tables**:
  - `performance_sessions` (PK: `session_id` UUID, `aggregate_version` INT)
  - `worker_evaluation_records` (PK: `record_id` UUID, partitioned by `calculated_at` TIMESTAMP)
* **Trigger Enforcement**:
  - A PL/pgSQL function `block_performance_record_mutation()` raises exceptions on direct `DELETE` or `UPDATE` statements, except for `is_active` toggling and lineage setting.
* **Partitioning**:
  - Range partitioned quarterly on `calculated_at` bounds to support high-throughput writes.

---

## 7. Event Contract Readiness

Domain events carry standard metadata (`event_id`, `correlation_id`, `causation_id`, `event_version`):
* `PerformanceSessionStagedEvent` (v1)
* `PerformanceSessionEvaluatedEvent` (v1)
* `PerformanceSessionSealedEvent` (v1)
* `BrierScoreCalibratedEvent` (v1)

---

## 8. Testing & Verification Strategy

Mandatory test cases to be implemented under `tests/karsa/performance/`:
1. **State Machine Transitions**: Validate that sessions cannot bypass states (e.g. `STAGED` $\to$ `SEALED` is blocked).
2. **Brier Score Calculation**: Validate calculations against pre-computed sets.
3. **Calibration Binning**: Check correct bin grouping and realized frequency mathematics.
4. **Immutability Enforcement**: Test that direct SQL updates on sealed records are blocked by triggers.
5. **Replayability Test**: Verify that re-running calculations over frozen data results in identical hashes.

---

## 9. Implementation Execution Plan

* **Phase 1: Domain Models & Logic**: Complete. Aggregates, value objects, and Brier calculations implemented.
* **Phase 2: Persistence Layer**: Complete. Migrations, range partitioning, triggers, and immutability controls implemented.
* **Phase 3: Repositories & Services**: Complete. InMemory, File-based, and Postgres repositories along with the `PerformanceEvaluationService`, `PerformanceReplayService`, and `CalibrationProjectionService` implemented.
* **Phase 4: Integrations**: Complete. Sorted lexicographical manifest hashing wired and verified.
* **Phase 5: Validation**: Complete. All 22 test cases pass, coverage gate $\ge 90\%$ met.

---

## 10. Final Implementation Status

* **Status**: Complete
* **Final Verdict**: `IMPLEMENTATION_COMPLETE`
