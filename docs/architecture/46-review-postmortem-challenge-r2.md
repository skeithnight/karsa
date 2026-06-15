# Sprint-44 Review & Post-Mortem Foundation Architecture Challenge Round 2 Report

This report presents the findings of the Round 2 Architecture Challenge for the **Review & Post-Mortem Foundation** bounded context in Sprint-44.

---

## 1. Executive Summary

An aggressive Round 2 Architectural Challenge was performed on the revised Sprint-44 Review & Post-Mortem Foundation design blueprints. While Option B (Decoupled Aggregates) successfully resolves the session OCC lock bottlenecks under concurrent AI reviewer loads, three critical architectural vulnerabilities were identified:
1. **Methodology Drift Flaw**: Pinning upstream database versions is insufficient for deterministic replay; any changes to LLM prompts, model weights, or evaluation rubrics over time will result in different review scores.
2. **Consensus Lineage Gap**: The consensus `PostMortemRecord` lacks an explicit reference array to the specific reviewer aggregates it synthesizes.
3. **Knowledge Graph Incompatibility**: Pointers use local UUIDs instead of standardized global URNs, which prevents seamless graph ingestion.

**Verdict**: `ARCHITECTURE_REQUIRES_REVISION`

---

## 2. ReviewSession Challenge

* **Option Evaluation**:
  - *Option A (Persisted Aggregate)*: Rejected. Creates write locks on session saves during concurrent writes.
  - *Option C (No Session)*: Rejected. Fails to define horizon-wide boundaries (e.g. "2026-Q2 Review"), meaning there is no way to audit when all reviews for a quarter are finished or to enforce manifest constraints.
  - *Option B (Orchestration Metadata)*: Selected. The session persists to store lifecycle state (`INITIATED` $\to$ `CONDUCTING` $\to$ `COMPLETED`) and the manifest hash, but does not lock concurrent writes to individual `ReviewRecord`s.

---

## 3. PostMortem Boundary Challenge

* **Option Evaluation**:
  - *Option B (Child Ledger)*: Rejected. Fails to support multi-reviewer systems. A consensus post-mortem must synthesize *all* competing reviews for a decision.
  - *Option C (Projection)*: Rejected. Does not allow human managers to manually override or finalize the post-mortem.
  - *Option A (Separate Aggregate Root)*: Selected. It represents the finalized consensus verdict (with qualitative improvement recommendations) and references the reviewer records it combines.

---

## 4. Replayability Challenge

* **Methodology Drift Vulnerability**: If an AI reviewer prompt is updated or the underlying LLM model is upgraded from `gpt-4o` to `gpt-5`, replaying the review 5 years later will produce different results.
* **Remediation**: The manifest must contain:
  - `review_methodology_urn` (String/Integer identifying the algorithm)
  - `review_policy_hash` (SHA-256 of the evaluation rubric rules)
  - `review_prompt_version` (identifying the prompt template version)
  - `reviewer_model_version` (identifying the specific LLM engine version)

---

## 5. Multi-Reviewer Challenge

* **Consensus Synthesis**: The `PostMortemRecord` must be compiled by a `ConsensusSolver` (e.g., majority vote or reputation-weighted averaging).
* **Consensus Lineage**: To guarantee auditability, `PostMortemRecord` must store:
  - `input_review_record_urns` (an array of URN:version pointers identifying the exact reviews summarized).

---

## 6. Knowledge Graph Compatibility

* **Local IDs vs Global URNs**: To support future Knowledge Graph queries, all aggregates must expose standardized global URN identifiers.
* **Graph Pointers**: Pointers must be modeled as URN fields (`urn:karsa:decision:...`, `urn:karsa:reviewer:...`, `urn:karsa:review-record:...`).

---

## 7. Scalability Challenge

* At 1B records, single-column range partitions will lead to excessively large partition slices.
* **Sub-partitioning**: Database schemas must support composite sub-partitioning (hash-partitioned on `decision_id` within the quarterly `reviewed_at` bounds).

---

## 8. Ownership Boundary Verification

* The review context does not store ratings or capital allocations, respecting the boundary of the Capital Allocation Engine.

---

## 9. Closed Sprint Protection Verification

* Sprints 41, 42, and 43 remain completely unchanged.

---

## 10. Architecture Delta Analysis

* **Delta**: **`NONE`**.
* All proposed corrections are confined strictly to the new Sprint-44 models.

---

## 11. Required Revisions

1. **Add Methodology Metadata**: Include `review_methodology_urn`, `review_policy_hash`, `review_prompt_version`, and `reviewer_model_version` in the `ReviewRecord` schema.
2. **Consensus Pointers**: Add `input_review_record_urns` to `PostMortemRecord` to trace consensus lineage.
3. **URN-based Identifiers**: Convert all UUID primary keys and relationship pointers to global URN fields.
4. **Sub-partitioning**: Map hash sub-partitioning in the database design for 1B scale.

---

## 12. Final Verdict

### **`ARCHITECTURE_REQUIRES_REVISION`**
