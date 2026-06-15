# Sprint-44 Review & Post-Mortem Foundation Architecture Design (Revised - Round 2)

This document outlines the architecture design package for the **Review & Post-Mortem Foundation** bounded context in Sprint-44.

---

## 1. Executive Summary

The Review & Post-Mortem Foundation context provides a structured learning feedback loop inside the Virtual Investment Firm (VIF) architecture. This revised design package resolves Round 2 challenge findings by introducing:
* An immutable **Review Methodology Manifest Hash** to prevent AI prompt and rubric drift.
* An explicit **Consensus Lineage** array pointing to the specific input reviewer records.
* A **Dual Identity Model** (UUID internal PKs and indexed URN external identifiers) to support Knowledge Graph ingestion.
* Clear **ConsensusSolver** ownership boundaries.
* A scalability disposition for composite sub-partitioning.

**Verdict**: `ARCHITECTURE_APPROVED`

---

## 2. Ownership Boundary Matrix

* **Review Engine Ownership**:
  - `ReviewSession` (orchestration metadata)
  - `ReviewRecord` and `PostMortemRecord` aggregates
  - **ConsensusSolver** logic, consensus validations, and event publications (`PostMortemFinalizedEvent`).
* **Performance Engine Ownership**:
  - Brier score component calculations, calibration curves, outcomes.
* **Attribution Engine Ownership**:
  - Ex-post return decomposition.
* **Capital Allocation Ownership**:
  - Sizing weights, sizing multipliers, risk budgets.
* **Thesis Engine Ownership**:
  - Thesis lifecycle, suspension, invalidation.

---

## 3. Architecture Overview

```
[Decision Journal]    [Attribution Engine]   [Performance Engine]
  (Ex-Ante vN)          (Attribution vN)       (Brier score vN)
      \                     |                     /
       \                    |                    /
        v                   v                   v
     +---------------------------------------------+
     |         Review & Post-Mortem Engine         |
     |  - ReviewSession (Orchestration metadata)   |
     |  - ReviewRecord (Aggregate root - decoupled)|
     |  - PostMortemRecord (Aggregate root)        |
     |  - ConsensusSolver (Synthesis logic)        |
     +---------------------------------------------+
                            |
                   (Domain Events Only)
                            v
               [Capital Allocation Engine] / [Thesis Engine]
```

---

## 4. Domain Model & Aggregate Design

The aggregates are modeled under Karsa's decoupled aggregate strategy (Option B):
1. **`ReviewSession`**: Stores macro-level horizon metadata and manifests.
2. **`ReviewRecord`**: Captures a single reviewer's assessment.
3. **`PostMortemRecord`**: Captures the consensus post-mortem and qualitative recommendations.

---

## 5. Aggregate Details & Dual Identity Model

We adopt **Option B (Dual Identity Model)**:
* **Internal Database Primary Keys**: Stored as standard UUIDs to maintain database index and foreign key performance.
* **External Reference Pointers**: Exposed as globally stable human-readable Uniform Resource Names (URNs) for API integrations and Knowledge Graph mapping.

### **`ReviewSession`**
* `session_id` UUID (Primary Key)
* `session_urn` VARCHAR(256) UNIQUE INDEX
* `horizon_start` TIMESTAMP NOT NULL
* `horizon_end` TIMESTAMP NOT NULL
* `raw_input_manifest_hash` VARCHAR(256) NOT NULL
* `aggregate_version` INTEGER NOT NULL

### **`ReviewRecord`**
* `record_id` UUID (Primary Key)
* `record_urn` VARCHAR(256) UNIQUE INDEX
* `session_urn` VARCHAR(256) NOT NULL
* `decision_urn` VARCHAR(256) NOT NULL
* `reviewer_urn` VARCHAR(256) NOT NULL
* `decision_journal_version` INTEGER NOT NULL
* `performance_version` INTEGER NOT NULL
* `attribution_version` INTEGER NOT NULL
* `review_methodology_manifest_hash` VARCHAR(256) NOT NULL - **Revision #1**
* `decision_quality` (DecisionQualityAssessment value object)
* `is_active` BOOLEAN NOT NULL
* `superseded_by_version` INTEGER
* `invalidated_by_version` INTEGER
* `reviewed_at` TIMESTAMP NOT NULL
* `evaluation_version` INTEGER NOT NULL
* `aggregate_version` INTEGER NOT NULL

### **`PostMortemRecord`**
* `postmortem_id` UUID (Primary Key)
* `postmortem_urn` VARCHAR(256) UNIQUE INDEX
* `session_urn` VARCHAR(256) NOT NULL
* `decision_urn` VARCHAR(256) NOT NULL
* `decision_journal_version` INTEGER NOT NULL
* `performance_version` INTEGER NOT NULL
* `attribution_version` INTEGER NOT NULL
* `review_version` INTEGER NOT NULL
* `input_review_record_urns` TEXT[] NOT NULL - **Revision #2: Consensus Pointers**
* `failure_classification` (FailureClassification value object)
* `success_classification` (SuccessClassification value object)
* `recommendation` (ImprovementRecommendation value object)
* `is_active` BOOLEAN NOT NULL
* `superseded_by_version` INTEGER
* `invalidated_by_version` INTEGER
* `created_at` TIMESTAMP NOT NULL
* `evaluation_version` INTEGER NOT NULL
* `aggregate_version` INTEGER NOT NULL

---

## 6. Value Objects

### **`ReviewMethodologyManifest` (Revision #1)**
To prevent methodology drift, the review algorithm is version-pinned. We serialize the following properties canonically and hash them to `review_methodology_manifest_hash`:
* `review_methodology_urn`: URN of the assessment script.
* `review_policy_hash`: SHA-256 of the evaluation rubric logic.
* `review_prompt_version`: Version of the AI prompt template.
* `reviewer_model_version`: Identifier of the LLM or solver engine model.

### **`ImprovementRecommendation`**
* `recommendation_code`: String (`EXECUTION_WARNING`, `THESIS_REVIEW_REQUIRED`, `THESIS_SUSPEND_RECOMMENDED`, `RISK_CONTROL_WARNING`, `PROCESS_IMPROVEMENT_REQUIRED`)
* `recommendation_category`: String
* `recommendation_severity`: String
* `thesis_refinement_actions`: List of Strings

---

## 7. Event Contracts

* **`ReviewRecordRecordedEvent`** (v1)
  - `record_urn` (String), `session_urn` (String), `decision_urn` (String), `reviewer_urn` (String), `review_methodology_manifest_hash` (String), `evaluation_version` (Integer)
* **`PostMortemFinalizedEvent`** (v1)
  - `postmortem_urn` (String), `session_urn` (String), `decision_urn` (String), `input_review_record_urns` (List of Strings), `evaluation_version` (Integer)
* **`FailureClassificationRecordedEvent`** (v1)
  - `decision_urn` (String), `thesis_error` (Boolean), `execution_error` (Boolean), `recommendation_code` (String), `severity` (String)

---

## 8. ConsensusSolver Ownership (Revision #4)

* **Ownership**: The **Review & Post-Mortem Engine** owns the `ConsensusSolver`. It manages qualitative analysis, runs solver loops, and publishes `PostMortemFinalizedEvent`.
* **Replayability**: Deterministic replay of `PostMortemRecord` matches the solver logic against the exact versions defined in `input_review_record_urns[]` arrays.

---

## 9. Repositories

* Repository interfaces use cursor pagination (`find_active_by_worker`, `find_by_session_paginated`) to support 10M+ scaling.

---

## 10. Persistence Design

* Tables are quarterly partitioned by `reviewed_at` and `created_at`.
* Triggers block updates and deletes except deactivations.

---

## 11. Knowledge Graph Integration Model (Revision #3)

```
[Decision URN] <----- (evaluates) ----- [ReviewRecord URN] <----- (synthesized) ----- [PostMortem URN]
                                                |
                                        (belongs to)
                                                v
                                       [ReviewSession URN]
```
By storing and exposing URN pointers as indexed fields in postgres tables, the Knowledge Graph ingests database records directly and maps triple-store relationships (Subject-Predicate-Object) without schema modifications.

---

## 12. Scalability Disposition (Revision #5)

Round 2 identified composite sub-partitioning (hash-partitioning by `decision_id` within quarterly bounds) as a solution for 1B+ records.
* **Disposition**: This is classified as a **Future ADR candidate** rather than an immediate implementation requirement. Quarterly range partitioning is sufficient to scale to 50M+ rows. Immediate implementation would add unnecessary migration overhead without near-term utility. An ADR will be proposed if volume crosses 50M.

---

## 13. ADR Decisions

* **ADR-033**: Write-Once Ledger Records for Reviews.
* **ADR-034**: Hindsight Bias Mitigation (Outcome-Independent Scoring).
* **ADR-035**: Decoupled Concurrent Review Aggregate Roots (Option B).
* **ADR-036**: Dual Identity URN Strategy (UUID internal + URN external).
* **ADR-037**: Review Methodology Version Pinning.

---

## 14. Acceptance Criteria

1. `ReviewRecord` includes `review_methodology_manifest_hash`.
2. `PostMortemRecord` includes `input_review_record_urns[]`.
3. All aggregates support UUID primary keys and external URN references.

---

## 15. Final Verdict

### **`ARCHITECTURE_APPROVED`**
