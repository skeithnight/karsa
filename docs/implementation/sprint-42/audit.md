# Sprint-42 Performance Attribution Engine Foundation Post-Implementation Audit Report

This report presents the post-implementation audit for the ex-post **Performance Attribution Engine Foundation** context in Sprint-42.

---

## 1. Executive Summary

A repository-level implementation audit was performed on the completed Sprint-42 codebase. While the core calculations, PostgreSQL triggers, and range partitioning are correctly implemented, two major issues were found:
1. **Coverage Target Deficit**: Total statement coverage is $72.4\%$ and branch coverage is $68.7\%$, both below the mandatory $90.0\%$ threshold.
2. **Missing Versioning Fields**: The required lineage fields `superseded_by_version` and `invalidated_by_version` were not implemented in the models or PostgreSQL schema.

Due to these deficits, the audit verdict is `AUDIT_REQUIRES_REMEDIATION`.

---

## 2. Architecture Compliance Matrix

| Target Design Decision | Frozen Architecture Specification | Implementation Artifact | Status |
| :--- | :--- | :--- | :---: |
| **AttributionSession** | Stage/Computing/Calibrated/Sealed | [AttributionSession](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/models.py#L7) | **PASS** |
| **PerformanceAttributionRecord** | Write-once ledger entries | [PerformanceAttributionRecord](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/models.py#L88) | **PASS** |
| **Frongello Compounding Floor** | Capped returns at $-99.9999\%$ | [FrongelloCompounding](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/value_objects.py#L72) | **PASS** |
| **Canonical Serializer** | Standardised sorted UTF-8 JSON hashing | [CanonicalManifestSerializer](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/value_objects.py#L173) | **PASS** |
| **PostgreSQL Partitioning** | Range partitioned by calculated_at | [42_attribution_init.py](file:///Users/dwiki.nugraha/dwikicode/karsa/alembic/versions/42_attribution_init.py#L61) | **PASS** |
| **Immutability Trigger** | Trigger blocking delete/update on returns | [42_attribution_init.py](file:///Users/dwiki.nugraha/dwikicode/karsa/alembic/versions/42_attribution_init.py#L13) | **PASS** |
| **Versioning Lineage URNs** | `superseded_by_version` / `invalidated_by_version` | [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/models.py#L88) | **FAIL** |

---

## 3. Aggregate Compliance Report

* **AttributionSession**:
  * Fully complies with state machine transition checks (`STAGED` $\to$ `COMPUTING` $\to$ `CALIBRATED` $\to$ `SEALED`). State bypasses (e.g. `STAGED` $\to$ `SEALED`) are successfully blocked.
* **PerformanceAttributionRecord**:
  * Implements write-once immutability via Python `__setattr__` block, rejecting any mutations on all keys except the transitional `is_active` flag, which is permitted to change strictly from `True` to `False`.
* **Additional Aggregates**: No unexpected aggregates were introduced, keeping bounded context boundaries clean.

---

## 4. Event Contract Assessment

Events defined in [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/events.py) correctly carry correlation and causation IDs:
* `AttributionCalculatedEvent` (v1)
* `AttributionSupersededEvent` (v1)
* `AttributionInvalidatedEvent` (v1)
* `AttributionRecomputedEvent` (v1)

*Gap*: An unused duplicate event schema file [attribution_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/attribution_events.py) exists in the repository with $0\%$ coverage.

---

## 5. Repository Assessment

* **InMemory repositories** support OCC validation and thread-safe deepcopy isolation.
* **File repositories** serialize entities to local JSON files but lack concurrent locking mechanisms.
* **Postgres repositories** integrate with raw SQL transactions.

---

## 6. Persistence Assessment

* **Schema**: Table definitions map to UUID keys and decimals with fixed scale.
* **Triggers**: PL/pgSQL function `block_attribution_record_mutation()` successfully executes `BEFORE UPDATE OR DELETE` checks, raising exception on modifications to return columns.
* **Partitions**: Partitioning range on `calculated_at` bounds correctly maps to default catch-all partitions.

---

## 7. Replayability Assessment

Replays follow the deterministic sequence:
$$\text{Transaction} \to \text{AttributionSession} \to \text{PerformanceAttributionRecord} \to \text{BenchmarkSnapshot} \to \text{ManifestHash}$$
The [AttributionReplayService](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/application/service.py#L301) regenerates input manifest hashes via the [CanonicalManifestSerializer](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/value_objects.py#L173), compares it with the saved manifest hash, and cross-validates results against persisted values.

---

## 8. Versioning Assessment

* **Fields Assessment**:
  * `attribution_version`: **Implemented**.
  * `superseded_by_version`: **Missing**.
  * `invalidated_by_version`: **Missing**.
* **Lineage**: The aggregate relies on the simplified `is_active` boolean rather than storing detailed pointer links to superseding versions.
* **Mutation Mode**: The implementation uses **UPDATE-based deactivation** for old record version deactivation rather than an append-only lineage table.
  * *Evidence in Postgres Repository*:
    ```sql
    UPDATE performance_attribution_records
    SET is_active = FALSE, aggregate_version = aggregate_version + 1
    WHERE decision_id = %s AND attribution_version != %s AND is_active = TRUE
    ```
  * *Frozen Architecture Check*: Matches the architecture design (ADR-063 / Revision Round 2), but misses the specific fields outlined in the implementation scope.

---

## 9. Coverage Assessment

Run Command: `uv run pytest --cov=src/karsa/attribution --cov-report=term-missing --cov-branch tests/karsa/attribution`

* **Statement Coverage**: $72.4\%$ (Covered: 614, Total Statements: 848)
* **Branch Coverage**: $68.7\%$ (Covered: 180, Total Branches: 262)
* **Total Statements**: 848
* **Total Branches**: 262
* **Uncovered Branches**: 82
* **Target Assessment**: Both statement and branch coverage targets ($90.0\%$) are **NOT** met.

---

## 10. Technical Debt Register

* **Code Coverage Debt**: Large branches inside repositories and compounding strategy value objects lack test scenarios.
* **Unused Code**: Duplicate event definitions in [attribution_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/attribution_events.py) remain in the codebase.
* **Deprecation Warnings**: Code paths utilize `datetime.utcnow()` instead of timezone-aware UTC datetime stamps.

---

## 11. Architecture Delta Analysis

* **Delta**: **Minor**.
  1. Omission of `superseded_by_version` and `invalidated_by_version` attributes on the [PerformanceAttributionRecord](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/models.py#L88) aggregate and database schemas.
  2. Addition of a utility method `deactivate_by_session` to the [PerformanceAttributionRepository](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/repositories.py#L23) interface and implementations to support clean invalidations.

---

## 12. Release Blocker Assessment

* **Blocker 1**: Coverage is below the $90\%$ threshold for release verification.
* **Blocker 2**: Versioning fields `superseded_by_version` and `invalidated_by_version` are missing.

---

## 13. Production Readiness Assessment

The Performance Attribution Engine Foundation is **NOT** ready for production due to the identified coverage deficit and missing attributes.

---

## 14. Findings

1. `superseded_by_version` and `invalidated_by_version` fields are missing from the `PerformanceAttributionRecord` aggregate class and alembic initialization migration.
2. The overall statement coverage is $72.4\%$ (missing target by $17.6\%$) and branch coverage is $68.7\%$ (missing target by $21.3\%$).

---

## 15. Remediation Requirements

1. **Implement Missing Fields**: Update the `PerformanceAttributionRecord` aggregate, postgres schema, and JSON serializers to support `superseded_by_version` and `invalidated_by_version`.
2. **Increase Code Coverage**: Add target unit and integration tests covering missed branches in repositories, compounding algorithms, and calculation error branches to raise statement and branch coverage to $\ge 90.0\%$.
3. **Remove Unused Files**: Delete the duplicate file [attribution_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/attribution_events.py).

---

## 16. Final Verdict

### **`AUDIT_REQUIRES_REMEDIATION`**
