# Sprint-42 Performance Attribution Engine Foundation Remediation Plan

This document presents Karsa's canonical **Remediation Plan** for the **Attribution Engine Foundation** context in Sprint-42.

---

## 1. Executive Summary

Following the post-implementation audit of Sprint-42, which returned `AUDIT_REQUIRES_REMEDIATION`, this plan maps out the specific scope of remediation required before Sprint-42 can be closed. 

Remediation targets:
1. **Model & Schema Updates**: Implementing the required versioning lineage attributes: `superseded_by_version` and `invalidated_by_version`.
2. **Coverage Hardening**: Adding target test coverage to satisfy the mandatory $\ge 90.0\%$ statement and branch coverage constraints.
3. **Unused File Deletion**: Safe removal of the duplicate event definition file `attribution_events.py`.

---

## 2. Versioning Verification Report

* **Mandatory Architecture Requirements**:
  * Direct evidence from the frozen architecture documents ([33-attribution-engine-design.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/33-attribution-engine-design.md) through [38-attribution-engine-closure.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/38-attribution-engine-closure.md)) shows that `superseded_by_version` and `invalidated_by_version` are **NOT** referenced or defined in the frozen architecture specification. The architecture specifies a simplified versioning system mapping URNs and using a boolean `is_active` flag.
  * However, these two fields are **required by the explicitly stated task scope** in the Sprint-42 implementation requirements.
* **Verdict**: `NOT_REQUIRED_BY_ARCHITECTURE` (but required by task-level implementation scope specifications).

---

## 3. Architecture Delta Report

The omission of the lineage fields is classified as an **Implementation Defect**:
* *Justification*: The frozen architecture is frozen and was not modified. The omission is not a delta in the design, nor documentation drift between design papers. It is a defect in the implementation's adherence to the explicitly requested task deliverables (which requested `superseded_by_version` and `invalidated_by_version` to support deep query auditing).

---

## 4. Replayability Impact Report

* **Deterministic Replay**: **No impact**. Deterministic replay relies entirely on matching ex-post inputs against `session.raw_input_manifest_hash` and running compounding math. Linear history does not alter this validation.
* **Invalidation Reconstruction**: **High impact**. Without `invalidated_by_version`, tracing the exact invalidation timeline requires parsing event logs rather than querying database state.
* **Superseding Reconstruction**: **High impact**. The absence of `superseded_by_version` makes traversing the parent-child lineage tree difficult for downstream query engines, forcing them to infer lineage sequentially by sorting on URNs.

---

## 5. Repository Classification Report

* **File Repositories**: Classified as **development adapters** and **testing adapters**. They are not intended for multi-process production execution.
* **Missing File Locking**: Classified as **Technical Debt**. Since they are not production adapters, missing lock primitives is not a release blocker, but must be documented as technical debt.

---

## 6. Duplicate File Assessment

* **Imported References**: None (found only inside the generator script `create_attribution.py`).
* **Runtime References**: None.
* **Migration References**: None.
* **Test References**: None.
* **Verdict**: Deletion of [attribution_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/attribution_events.py) is **completely safe** and will be performed during remediation.

---

## 7. Coverage Gap Matrix

| File Target | Missing Branch / Line Range | Remediation Test Strategy |
| :--- | :--- | :--- |
| [service.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/application/service.py) | ValueError checks in `_get_strategy` (Lines 38, 40, 155-159); session not found errors (Lines 63, 118, 170, 282, 310); manifest hash short-circuiting (Line 175); recomputation limits (Line 181); and replay mismatches (Lines 338-346). | Add error-path unit tests inside `tests/karsa/attribution/application/test_attribution_services.py`. |
| [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/models.py) | Session validation errors (Lines 31-45); invalid transitions (Lines 53, 55); Record validation errors (Lines 131-147); and attribute deletion checks (Lines 167-169). | Add validation exception tests inside `tests/karsa/attribution/domain/test_attribution_domain.py`. |
| [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/value_objects.py) | Benchmark validation (Lines 22, 32); Carino compounding and scaling math (Lines 101-156); and manifest serialization sorting edge cases (Lines 237-241). | Add target mathematical unit tests inside `tests/karsa/attribution/domain/test_attribution_domain.py`. |
| [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/infrastructure/repositories.py) | File repository list/clear branches (Lines 130-148, 230-231) and Postgres list/clear methods (Lines 342-363, 527-560). | Add detailed repository cleanup tests inside `tests/karsa/attribution/infrastructure/test_attribution_repositories.py`. |

---

## 8. Remediation Scope

1. **Schema Update**: Update `PerformanceAttributionRecord` models and PostgreSQL tables to include `superseded_by_version` (Integer) and `invalidated_by_version` (Integer), defaulting to `NULL`.
2. **Deactivation Logic**: Update `deactivate_old_versions` and `deactivate_by_session` to populate these columns upon record invalidations.
3. **Event Serialization**: Support serialization/deserialization of these new columns.
4. **Delete Unused Files**: Remove [attribution_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/attribution_events.py).
5. **Coverage Hardening**: Add targeted tests to raise branch and statement coverage above $90.0\%$.

---

## 9. Findings

1. `superseded_by_version` and `invalidated_by_version` were omitted from the implementation.
2. Code coverage falls below the mandatory $90.0\%$ target.
3. [attribution_events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/attribution_events.py) is a duplicate schema file and is safe to delete.

---

## 10. Final Verdict

### **`REMEDIATION_PLAN_APPROVED`**
