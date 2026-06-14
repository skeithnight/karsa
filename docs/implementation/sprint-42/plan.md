# Sprint-42 Attribution Engine Foundation Pre-Implementation Readiness Plan

This report presents Karsa's canonical Pre-Implementation Readiness Plan for the **Attribution Engine Foundation** bounded context in Sprint-42.

---

## 1. Executive Summary

A pre-implementation readiness review was performed on the Sprint-42 Attribution Engine Foundation design definitions. The plan outlines the domain model boundaries, value object calculations (Brinson-Fachler and Brier score), PostgreSQL tables, range partitioning, audit replay sequences, and integration contracts with upstream read-only engines (Portfolio, Execution, Decision Journal, Risk).

The implementation plan complies with Karsa's design standards, providing a detailed roadmap to construct a high-performance, write-once ex-post performance learning loop.

**Verdict**: `IMPLEMENTATION_PLAN_APPROVED`

---

## 2. Architecture Freeze Compliance Matrix

The matrix below checks the consistency of design decisions against Sprint-42 architectural inputs:

| Target Design Decision | Attribution Architecture Document | ADR-057 (Ledger) | ADR-058 (Brinson) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **AttributionSession Aggregate** | Defined as horizon state | Authoritative tracker | Mapped in execution | **PASS** |
| **PerformanceAttributionRecord** | Range partitioned ledger | Cryptographically hashed | Brinson-Fachler split | **PASS** |
| **BrierScore Value Object** | Defined as calibration metric | Logged ex-post | Decoupled check | **PASS** |
| **Carino Compounding Algorithm**| Multi-horizon scaling | Calculation logic | Decoupled check | **PASS** |
| **PostgreSQL Immutability Trigger**| Block UPDATE/DELETE | Ledger protection | Not applicable | **PASS** |

---

## 3. Aggregate Readiness Matrix

The table below checks readiness metrics for the two target aggregates in the Attribution bounded context:

| Aggregate | Ownership Boundary | Lifecycle States | Transaction Boundary | Persistence Model | Replayability Model |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AttributionSession** | Attribution Context | `STAGED` $\to$ `COMPUTING` $\to$ `CALIBRATED` $\to$ `SEALED` | Session-level transaction | Postgres versioned | Unique `session_id` |
| **PerformanceAttributionRecord** | Attribution Context | `RECORDED` | Write-once ledger record | Range-partitioned | Hash-linked to `session_id` and `decision_id` |

---

## 4. Value Objects & Calculation Logic

* **Brinson-Fachler Model**:
  $$\text{Allocation Effect} = (w_{i,p} - w_{i,b}) \times (R_{i,b} - R_b)$$
  $$\text{Selection Effect} = w_{i,b} \times (R_{i,p} - R_{i,b})$$
  $$\text{Execution Effect} = \text{Actual Price Returns} - \text{Decision Price Returns}$$
* **Carino Compounding Algorithm**:
  Adjusts sub-period attribution effects to sum exactly to multi-period total returns:
  $$k_t = \frac{\ln(1 + R_t)}{R_t}$$
  $$K = \frac{\ln(1 + R_P)}{R_P}$$
  Scaling factor: $w_t = \frac{k_t}{K}$
* **Brier Score**:
  $$BS = \frac{1}{N} \sum_{t=1}^{N} (f_t - o_t)^2$$
  Measures accuracy of probabilistic forecasts $f_t$ against binary outcomes $o_t$.

---

## 5. Decision & Horizon Integration Readiness

* **Decision Journal Integration**: Reads ex-ante logged decisions, confidence metrics, and asset tickers over the target horizon bounds.
* **Portfolio Integration**: Reads end-of-period holdings and historical valuation logs.
* **Execution Integration**: Reads fill records, executions, and executed price variables.
* **Failure Behavior**: If any upstream API reads fail, the `AttributionSession` transitions to `STAGED` (rollback). No partial calculations are stored.

---

## 6. Persistence & Immutability Design

* **Tables**:
  - `attribution_sessions` (PK: `session_id` UUID, `aggregate_version` INT)
  - `performance_attribution_records` (PK: `record_id` UUID, partitioned by `calculated_at` TIMESTAMP)
* **Trigger Enforcement**:
  - A PL/pgSQL function `block_mutation()` will raise an exception on `UPDATE` or `DELETE` for sealed performance attribution records.
* **Partitioning**:
  - Range partitioned quarterly on `calculated_at` bounds to support high-throughput writes and isolated archive management.

---

## 7. Event Contract Readiness

Domain events carry standardized metadata (`event_id`, `correlation_id`, `causation_id`, `event_version`):
* `AttributionSessionStagedEvent` (v1)
* `AttributionSessionComputedEvent` (v1)
* `PerformanceAttributionSealedEvent` (v1)
* `BrierScoreCalibratedEvent` (v1)

---

## 8. Testing & Verification Strategy

Mandatory test cases to be implemented under `tests/karsa/attribution/`:
1. **State Machine Transitions**: Validate that sessions cannot bypass states (e.g. `STAGED` $\to$ `SEALED` is blocked).
2. **Brinson-Fachler Decomposition**: Check correct mathematical allocations with edge cases (zero holdings, negative benchmarks).
3. **Carino Smoothing Verification**: Verify that multi-period compound attributions equal the total period return.
4. **Brier Score Calculation**: Validate calculations against pre-computed sets.
5. **Immutability Enforcement**: Test that direct SQL updates on sealed records are blocked by triggers.
6. **Replayability Test**: Verify that re-running calculations over frozen data results in identical hashes.

---

## 9. Implementation Execution Plan

* **Phase 1: Domain Models & Logic**: Create python aggregates, value objects, and Carino calculations in `models.py` and `value_objects.py`.
* **Phase 2: Persistence Layer**: Write migrations creating tables, triggers, and indices.
* **Phase 3: Repositories & Services**: Implement session and record repositories and `PerformanceAttributionService`.
* **Phase 4: Integrations**: Wire up mock client libraries for Portfolio, Decision Journal, and Execution interfaces.
* **Phase 5: Validation**: Verify full suite of tests under `tests/karsa/attribution/`.
