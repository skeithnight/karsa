# Sprint-44 Review & Post-Mortem Foundation Pre-Implementation Readiness Plan

This report presents Karsa's canonical Pre-Implementation Readiness Plan for the **Review & Post-Mortem Foundation** bounded context in Sprint-44.

---

## 1. Executive Summary

A pre-implementation readiness review was performed on the revised Sprint-44 Review & Post-Mortem Foundation design definitions. The plan outlines the domain model boundaries, decoupled aggregates, dual identity models (UUID + URN), methodology version-pinned manifests, postgres tables, triggers, and execution phases.

**Verdict**: `ARCHITECTURE_APPROVED`

---

## 2. Architecture Freeze Compliance Matrix

| Target Design Component | Design Blueprint Reference | ADR-035 (Aggregate Root) | ADR-036 (Dual Identity) | ADR-037 (Methodology Pin) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ReviewSession Aggregate** | docs/architecture/43-review-postmortem-design.md Section 5 | Orchestration metadata | Dual identity URN | Not applicable | **PASS** |
| **ReviewRecord Aggregate** | docs/architecture/43-review-postmortem-design.md Section 5 | Decoupled Record | Dual identity URN | methodology hash | **PASS** |
| **PostMortemRecord Aggregate**| docs/architecture/43-review-postmortem-design.md Section 5 | Decoupled PostMortem| Dual identity URN | consensus pointer | **PASS** |
| **Immutability Trigger** | docs/architecture/43-review-postmortem-design.md Section 10 | Ledger protection | Not applicable | Not applicable | **PASS** |

---

## 3. Aggregate Readiness Matrix

All aggregates are structured under the dual-identity strategy:

| Aggregate | Ownership Boundary | Lifecycle States | Transaction Boundary | Persistence Model | Replayability Model |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ReviewSession** | Review & PM Context | `INITIATED` $\to$ `CONDUCTING` $\to$ `COMPLETED` $\to$ `ARCHIVED` | Session state save | UUID PK, URN index | Unique `session_urn` |
| **ReviewRecord** | Review & PM Context | `RECORDED` | Record-level transaction | UUID PK, URN index | Pinned versions + URN |
| **PostMortemRecord** | Review & PM Context | `FINALIZED` | PostMortem-level transaction | UUID PK, URN index | `input_review_record_urns[]` |

---

## 4. Value Objects & Calculation Logic

* **DecisionQualityAssessment**: Holds outcome-independent score, outcome-dependent score, and hindsight bias deviation.
* **FailureClassification**: Holds boolean flags for thesis, execution, timing, sizing, and calibration errors.
* **ImprovementRecommendation**: Holds qualitative codes (`EXECUTION_WARNING`, `THESIS_REVIEW_REQUIRED`) and severities.
* **ReviewMethodologyManifest**: Holds `review_methodology_urn`, `review_policy_hash`, `review_prompt_version`, and `reviewer_model_version`, hashed deterministically to `review_methodology_manifest_hash`.

---

## 5. Review & Post-Mortem Integration Readiness

* **Decision Journal Integration**: Reads ex-ante reasoning.
* **Performance Integration**: Reads Brier score outcomes.
* **Attribution Integration**: Reads return decompositions.
* **Thesis Integration**: Subscribes to events. Review Engine publishes event flags, and Thesis Engine handles self-mutations.
* **ConsensusSolver**: Housed inside Review context; runs syntheses and asserts outputs match `PostMortemRecord` inputs.
* **Knowledge Graph Integration**: Exposes URN fields natively as indexed database columns to simplify graph node mapping.

---

## 6. Persistence & Immutability Design

* **Tables**:
  - `review_sessions`
  - `review_records` (Partitioned quarterly on `reviewed_at`)
  - `postmortem_records` (Partitioned quarterly on `created_at`)
* **Trigger Enforcement**: PL/pgSQL function `block_review_record_mutation()` raises exceptions on UPDATE and DELETE queries except deactivations.
* **Sub-partitioning**: Scalability checks identify hash sub-partitioning as a future ADR candidate when table rowcount exceeds 50M.

---

## 7. Event Contract Readiness

Events carry URN indicators:
* `ReviewRecordRecordedEvent` (v1)
* `PostMortemFinalizedEvent` (v1) - contains list of `input_review_record_urns`
* `FailureClassificationRecordedEvent` (v1)

---

## 8. Testing & Verification Strategy

Mandatory test cases to be implemented under `tests/karsa/review_postmortem/`:
1. **Methodology Drift**: Validate that changing LLM prompts or rubrics updates `review_methodology_manifest_hash` and catches anomalies.
2. **Consensus Lineage**: Verify that replaying the `ConsensusSolver` with `input_review_record_urns[]` produces identical classifications.
3. **Dual Identity**: Verify database lookups succeed using both internal UUIDs and external URN strings.
4. **Trigger Immutability**: Verify triggers block direct updates and deletes on review tables.

---

## 9. Implementation Execution Plan

* **Phase 1: Domain Models & Value Objects**: Implement aggregates, value objects, and events.
* **Phase 2: Persistence Layer**: Write migrations for partitioned tables, triggers, and indices.
* **Phase 3: Repositories & Services**: Implement paginated repository contracts and consensus/replay services.
* **Phase 4: Integrations**: Setup events, URN mappings, and subscribers.
* **Phase 5: Validation**: Verify statement and branch coverage $\ge 90\%$.
