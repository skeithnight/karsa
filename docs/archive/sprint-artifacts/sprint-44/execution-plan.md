# Sprint-44 Review & Post-Mortem Foundation Implementation Execution Plan

This document outlines the **Implementation Execution Plan** for the **Review & Post-Mortem Foundation** bounded context in Sprint-44.

---

## 1. Executive Summary

This execution plan defines the detailed implementation roadmap for the Review & Post-Mortem bounded context. The architecture is frozen and approved. This plan specifies the class structures, state rules, database schema designs, consensus algorithms, event structures, repository contracts, and testing strategies required for implementation.

**Verdict**: `READY_FOR_IMPLEMENTATION`

---

## 2. Implementation Scope

The implementation phase will create and modify the following files:

### **Files to be Created**:
* [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/domain/model/models.py) - Aggregate roots (`ReviewSession`, `ReviewRecord`, `PostMortemRecord`).
* [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/domain/model/value_objects.py) - Value objects (`DecisionQualityAssessment`, `FailureClassification`, `SuccessClassification`, `ImprovementRecommendation`, `ReviewMethodologyManifest`).
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/domain/model/repositories.py) - Abstract repository interfaces.
* [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/events/events.py) - Domain event classes.
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/infrastructure/repositories.py) - Repository implementations (`InMemory`, `File-based`, `Postgres-based`).
* [service.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/application/service.py) - Services (`ReviewOrchestrationService`, `ReviewReplayService`, `ReviewLineageService`, `ConsensusSolver`).
* [projections.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/domain/projections.py) - Dynamically calculated read-only projections.
* [__init__.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/review_postmortem/__init__.py) - Package entry point exporting clean public interfaces.
* `alembic/versions/44_review_postmortem_init.py` - Database migration script for partitioned tables, indexes, and immutability triggers.
* [test_review_postmortem.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/review_postmortem/test_review_postmortem.py) - Complete test suite with 90%+ statement/branch coverage.

### **Files to be Modified**:
* [ROADMAP.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/roadmap/ROADMAP.md) - Update Sprint-44 baseline status after implementation closure.

---

## 3. Aggregate Implementation Plan

All aggregates derive from `VersionedAggregate` to support standard optimistic concurrency control (OCC).

### **`ReviewSession`**
* **Class Design**:
  * Inherits from `VersionedAggregate`.
  * Attributes:
    * `session_id`: `UUID` (Internal Primary Key)
    * `session_urn`: `str` (External URN, e.g., `urn:karsa:review:session:<uuid>`)
    * `horizon_start`: `datetime` (UTC timestamp)
    * `horizon_end`: `datetime` (UTC timestamp)
    * `raw_input_manifest_hash`: `str` (SHA-256 string representing the source dataset)
    * `status`: `ReviewSessionStatus` (Enum: `INITIATED`, `CONDUCTING`, `COMPLETED`, `ARCHIVED`)
    * `aggregate_version`: `int` (Incremental version number for OCC)
  * Methods:
    * `start_reviews()`: Transitions status from `INITIATED` to `CONDUCTING`.
    * `complete()`: Transitions status from `CONDUCTING` to `COMPLETED`.
    * `archive()`: Transitions status from `COMPLETED` to `ARCHIVED`.
* **State Transitions**:
  * `INITIATED` $\to$ `CONDUCTING` $\to$ `COMPLETED` $\to$ `ARCHIVED`.
  * Direct transitions are unidirectional. Any backward transitions or skipping states will raise a `StateTransitionError`.
  * Every state transition increments `aggregate_version` by 1.
* **Validation Rules**:
  * `horizon_start` must be strictly before `horizon_end`.
  * `raw_input_manifest_hash` must be a valid 64-character hexadecimal SHA-256 string.
  * URN must follow format `urn:karsa:review:session:[a-f0-9\-]{36}`.
* **Persistence Mapping**:
  * Table: `review_sessions`
  * PK: `session_id` UUID
  * Constraints: `session_urn` is `VARCHAR(256) UNIQUE` and `NOT NULL`.

### **`ReviewRecord`**
* **Class Design**:
  * Inherits from `VersionedAggregate`.
  * Attributes:
    * `record_id`: `UUID` (Internal Primary Key)
    * `record_urn`: `str` (External URN, e.g., `urn:karsa:review:record:<uuid>`)
    * `session_urn`: `str` (URN link to ReviewSession)
    * `decision_urn`: `str` (URN link to ex-ante Decision)
    * `reviewer_urn`: `str` (URN link to Evaluated Worker)
    * `decision_journal_version`: `int` (Pinned version of decision journal)
    * `performance_version`: `int` (Pinned version of performance evaluation)
    * `attribution_version`: `int` (Pinned version of attribution record)
    * `review_methodology_manifest_hash`: `str` (SHA-256 of review methodology)
    * `decision_quality`: `DecisionQualityAssessment` (Value Object)
    * `is_active`: `bool` (Toggled FALSE if superseded or invalidated)
    * `superseded_by_version`: `Optional[int]` (Version pointer to superseding record)
    * `invalidated_by_version`: `Optional[int]` (Version pointer to invalidating process)
    * `reviewed_at`: `datetime` (Partition column, UTC timestamp)
    * `evaluation_version`: `int` (Sequential increment of evaluation counts for this decision)
    * `aggregate_version`: `int` (OCC tracker)
  * Methods:
    * `__setattr__(self, name, value)`: Custom override to enforce write-once immutability. If any field other than `is_active`, `superseded_by_version`, `invalidated_by_version`, and `aggregate_version` is modified after initialization, raise `ImmutabilityViolationError`.
    * `supersede(self, new_version: int)`: Sets `is_active = False` and `superseded_by_version = new_version`. Increments `aggregate_version`.
    * `invalidate(self, invalidating_version: int)`: Sets `is_active = False` and `invalidated_by_version = invalidating_version`. Increments `aggregate_version`.
* **State Transitions**:
  * Created in `active` state (`is_active = True`).
  * Transitions to `inactive` (`is_active = False`) via either `supersede()` or `invalidate()`. Once inactive, it cannot be reactivated.
* **Validation Rules**:
  * Versions (`decision_journal_version`, `performance_version`, `attribution_version`, `evaluation_version`, `aggregate_version`) must be positive integers ($\ge 1$).
  * URN prefixes must start with `urn:karsa:review:record:`.
  * `reviewed_at` must not be a future timestamp.
* **Persistence Mapping**:
  * Table: `review_records` (Partitioned by RANGE on `reviewed_at`).
  * PK: `(record_id, reviewed_at)`.
  * FK: `session_urn` references `review_sessions(session_urn)`.

### **`PostMortemRecord`**
* **Class Design**:
  * Inherits from `VersionedAggregate`.
  * Attributes:
    * `postmortem_id`: `UUID` (Internal Primary Key)
    * `postmortem_urn`: `str` (External URN, e.g., `urn:karsa:postmortem:record:<uuid>`)
    * `session_urn`: `str` (URN link to ReviewSession)
    * `decision_urn`: `str` (URN link to ex-ante Decision)
    * `decision_journal_version`: `int` (Pinned version of decision journal)
    * `performance_version`: `int` (Pinned version of performance evaluation)
    * `attribution_version`: `int` (Pinned version of attribution record)
    * `review_version`: `int` (Pinned version of review outputs)
    * `input_review_record_urns`: `List[str]` (URN pointers to reviewer records used in synthesis)
    * `failure_classification`: `FailureClassification` (Value Object)
    * `success_classification`: `SuccessClassification` (Value Object)
    * `recommendation`: `ImprovementRecommendation` (Value Object)
    * `is_active`: `bool` (Toggled FALSE if superseded or invalidated)
    * `superseded_by_version`: `Optional[int]`
    * `invalidated_by_version`: `Optional[int]`
    * `created_at`: `datetime` (Partition column, UTC timestamp)
    * `evaluation_version`: `int`
    * `aggregate_version`: `int`
    * `consensus_methodology_urn`: `str` (URN mapping of the solver code version)
    * `consensus_policy_hash`: `str` (SHA-256 hash of the solver parameters)
  * Methods:
    * `__setattr__(self, name, value)`: Override to enforce write-once immutability. If any field other than `is_active`, `superseded_by_version`, `invalidated_by_version`, and `aggregate_version` is modified after initialization, raise `ImmutabilityViolationError`.
    * `supersede(self, new_version: int)`: Sets `is_active = False` and `superseded_by_version = new_version`. Increments `aggregate_version`.
    * `invalidate(self, invalidating_version: int)`: Sets `is_active = False` and `invalidated_by_version = invalidating_version`. Increments `aggregate_version`.
* **State Transitions**:
  * Created in active state. Toggles to inactive via supersession or invalidation.
* **Validation Rules**:
  * `input_review_record_urns` must contain at least 1 string and all elements must follow `urn:karsa:review:record:` format.
  * `consensus_methodology_urn` must be a valid URN.
  * `consensus_policy_hash` must be a valid 64-character SHA-256 hash.
* **Persistence Mapping**:
  * Table: `postmortem_records` (Partitioned by RANGE on `created_at`).
  * PK: `(postmortem_id, created_at)`.
  * FK: `session_urn` references `review_sessions(session_urn)`.

---

## 4. Value Object Implementation Plan

All value objects are modeled as Python `@dataclass(frozen=True)` to guarantee absolute structural immutability.

* **`DecisionQualityAssessment`**:
  * Attributes:
    * `outcome_independent_score`: `float` (Ex-ante reasoning score, e.g., sizing discipline, evidence check)
    * `outcome_dependent_score`: `float` (Ex-post score, factoring Brier scores and realized returns)
    * `hindsight_bias_deviation`: `float` (Difference between ex-post and ex-ante score components)
  * Validation:
    * Scores must be within range $[0.0, 1.0]$.
    * Deviation must be equal to `outcome_dependent_score - outcome_independent_score` (validated to $10^{-4}$ decimal precision).
* **`FailureClassification`**:
  * Attributes:
    * `thesis_error`: `bool` (Was the investment thesis mathematically/fundamentally flawed?)
    * `execution_error`: `bool` (Was there a trade entry/exit execution error?)
    * `timing_error`: `bool` (Was the trade execution timing wrong?)
    * `sizing_error`: `bool` (Was sizing inappropriate, though the thesis was correct?)
    * `calibration_error`: `bool` (Did worker overestimate their prediction confidence?)
* **`SuccessClassification`**:
  * Attributes:
    * `alpha_generation`: `bool` (Did prediction produce idiosyncratic returns?)
    * `execution_efficiency`: `bool` (Did execution beat benchmark implementation shortfall?)
    * `risk_mitigation`: `bool` (Did risk sizing protect capital during drawdowns?)
* **`ImprovementRecommendation`**:
  * Attributes:
    * `recommendation_code`: `str` (Enum values: `EXECUTION_WARNING`, `THESIS_REVIEW_REQUIRED`, `THESIS_SUSPEND_RECOMMENDED`, `RISK_CONTROL_WARNING`, `PROCESS_IMPROVEMENT_REQUIRED`)
    * `recommendation_category`: `str`
    * `recommendation_severity`: `str` (Enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
    * `thesis_refinement_actions`: `List[str]` (Specific qualitative action points)
  * Validation:
    * `recommendation_code` and `recommendation_severity` must match defined options.
* **`ReviewMethodologyManifest`**:
  * Attributes:
    * `review_methodology_urn`: `str` (Assessment solver script URN)
    * `review_policy_hash`: `str` (SHA-256 hash of the rubric rules)
    * `review_prompt_version`: `str` (Version tag of prompt templates)
    * `reviewer_model_version`: `str` (Model version tag)
  * Hashing algorithm:
    * Convert object fields to dict, sort keys alphabetically, serialize to JSON string using UTF-8, and compute SHA-256:
      ```python
      def compute_hash(self) -> str:
          payload = {
              "review_methodology_urn": self.review_methodology_urn,
              "review_policy_hash": self.review_policy_hash,
              "review_prompt_version": self.review_prompt_version,
              "reviewer_model_version": self.reviewer_model_version
          }
          serialized = json.dumps(payload, sort_keys=True)
          return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
      ```

---

## 5. Event Contract Implementation Plan

Domain events are defined as immutable classes that serialize to standardized JSON payloads for pub/sub message brokers.

### **`ReviewRecordRecordedEvent`** (v1)
* **Payload Fields & Types**:
  * `event_id`: `str` (UUID)
  * `event_urn`: `str` (URN: `urn:karsa:event:review:record:recorded:<uuid>`)
  * `timestamp`: `str` (ISO 8601 UTC string)
  * `record_urn`: `str`
  * `session_urn`: `str`
  * `decision_urn`: `str`
  * `reviewer_urn`: `str`
  * `review_methodology_manifest_hash`: `str`
  * `evaluation_version`: `int`

### **`PostMortemFinalizedEvent`** (v1)
* **Payload Fields & Types**:
  * `event_id`: `str` (UUID)
  * `event_urn`: `str` (URN: `urn:karsa:event:postmortem:finalized:<uuid>`)
  * `timestamp`: `str` (ISO 8601 UTC string)
  * `postmortem_urn`: `str`
  * `session_urn`: `str`
  * `decision_urn`: `str`
  * `input_review_record_urns`: `List[str]`
  * `evaluation_version`: `int`
  * `consensus_methodology_urn`: `str`
  * `consensus_policy_hash`: `str`

### **`FailureClassificationRecordedEvent`** (v1)
* **Payload Fields & Types**:
  * `event_id`: `str` (UUID)
  * `event_urn`: `str` (URN: `urn:karsa:event:failure:classification:recorded:<uuid>`)
  * `timestamp`: `str` (ISO 8601 UTC string)
  * `decision_urn`: `str`
  * `thesis_error`: `bool`
  * `execution_error`: `bool`
  * `timing_error`: `bool`
  * `sizing_error`: `bool`
  * `calibration_error`: `bool`
  * `recommendation_code`: `str`
  * `severity`: `str`

---

## 6. Repository Implementation Plan

Each aggregate has an abstract repository interface declaring paginated query operations.

### **Common Query Contracts**
* `save(aggregate: Aggregate) -> None`
* `find_by_urn(urn: str) -> Optional[Aggregate]`
* `find_by_session_paginated(session_urn: str, limit: int, cursor: Optional[str]) -> PaginatedResult[Aggregate]`
* `find_active_by_reviewer(reviewer_urn: str, limit: int, cursor: Optional[str]) -> PaginatedResult[Aggregate]`
* `find_active_by_decision(decision_urn: str) -> Optional[Aggregate]`

### **`InMemory` Adapter**
* Uses internal dictionaries (`Dict[str, dict]`) mapping URNs to copies of domain state.
* **Aggregate Isolation**: Uses `copy.deepcopy` upon every save and retrieve operation to ensure memory references are completely isolated from the domain code.
* **Pagination**:
  1. Retrieve all matching records (e.g., matching `session_urn`).
  2. Sort elements lexicographically by URN string.
  3. If `cursor` (URN string) is provided, slice the list starting from the first element greater than the cursor.
  4. Yield up to `limit` items.
  5. The `next_cursor` is the URN of the last element returned in the slice, or `None` if no further elements remain.

### **`File` Adapter**
* Stores serialized JSON representations in directory `.karsa/review_postmortem/` under subdirectories `sessions/`, `records/`, and `postmortems/`.
* Writes are atomic using a temp-file write followed by an OS-level rename.
* **Pagination**:
  1. Scan files in target subdirectory to compile filenames.
  2. Sort filenames/URNs alphabetically.
  3. Filter filenames greater than the provided `cursor`.
  4. Read, parse, and instantiate the first `limit` records.
  5. Set `next_cursor` as the URN of the last loaded file.

### **`PostgreSQL` Adapter**
* Uses raw SQL queries executing via connection cursors.
* **Pagination**:
  * Implements **Keyset Pagination** (No offsets used to avoid performance degradation at 10M+ scale).
  * If cursor is provided:
    ```sql
    SELECT * FROM review_records 
    WHERE session_urn = :session_urn AND record_urn > :cursor 
    ORDER BY record_urn ASC 
    LIMIT :limit
    ```
  * If cursor is omitted:
    ```sql
    SELECT * FROM review_records 
    WHERE session_urn = :session_urn 
    ORDER BY record_urn ASC 
    LIMIT :limit
    ```

---

## 7. PostgreSQL Migration Plan

Alembic script `44_review_postmortem_init.py` will establish the target database schema.

### **Table Schemas & Columns**
1. **`review_sessions`**:
   * `session_id` `UUID` NOT NULL,
   * `session_urn` `VARCHAR(256)` NOT NULL,
   * `horizon_start` `TIMESTAMP WITHOUT TIME ZONE` NOT NULL,
   * `horizon_end` `TIMESTAMP WITHOUT TIME ZONE` NOT NULL,
   * `raw_input_manifest_hash` `VARCHAR(64)` NOT NULL,
   * `status` `VARCHAR(32)` NOT NULL,
   * `aggregate_version` `INTEGER` NOT NULL,
   * PRIMARY KEY (`session_id`),
   * CONSTRAINT `uq_review_sessions_urn` UNIQUE (`session_urn`)
2. **`review_records`**:
   * `record_id` `UUID` NOT NULL,
   * `record_urn` `VARCHAR(256)` NOT NULL,
   * `session_urn` `VARCHAR(256)` NOT NULL,
   * `decision_urn` `VARCHAR(256)` NOT NULL,
   * `reviewer_urn` `VARCHAR(256)` NOT NULL,
   * `decision_journal_version` `INTEGER` NOT NULL,
   * `performance_version` `INTEGER` NOT NULL,
   * `attribution_version` `INTEGER` NOT NULL,
   * `review_methodology_manifest_hash` `VARCHAR(64)` NOT NULL,
   * `outcome_independent_score` `NUMERIC(5,4)` NOT NULL,
   * `outcome_dependent_score` `NUMERIC(5,4)` NOT NULL,
   * `hindsight_bias_deviation` `NUMERIC(5,4)` NOT NULL,
   * `is_active` `BOOLEAN` NOT NULL DEFAULT TRUE,
   * `superseded_by_version` `INTEGER` NULL,
   * `invalidated_by_version` `INTEGER` NULL,
   * `reviewed_at` `TIMESTAMP WITHOUT TIME ZONE` NOT NULL,
   * `evaluation_version` `INTEGER` NOT NULL,
   * `aggregate_version` `INTEGER` NOT NULL,
   * PRIMARY KEY (`record_id`, `reviewed_at`)
3. **`postmortem_records`**:
   * `postmortem_id` `UUID` NOT NULL,
   * `postmortem_urn` `VARCHAR(256)` NOT NULL,
   * `session_urn` `VARCHAR(256)` NOT NULL,
   * `decision_urn` `VARCHAR(256)` NOT NULL,
   * `decision_journal_version` `INTEGER` NOT NULL,
   * `performance_version` `INTEGER` NOT NULL,
   * `attribution_version` `INTEGER` NOT NULL,
   * `review_version` `INTEGER` NOT NULL,
   * `input_review_record_urns` `TEXT[]` NOT NULL,
   * `thesis_error` `BOOLEAN` NOT NULL,
   * `execution_error` `BOOLEAN` NOT NULL,
   * `timing_error` `BOOLEAN` NOT NULL,
   * `sizing_error` `BOOLEAN` NOT NULL,
   * `calibration_error` `BOOLEAN` NOT NULL,
   * `alpha_generation` `BOOLEAN` NOT NULL,
   * `execution_efficiency` `BOOLEAN` NOT NULL,
   * `risk_mitigation` `BOOLEAN` NOT NULL,
   * `recommendation_code` `VARCHAR(64)` NOT NULL,
   * `recommendation_category` `VARCHAR(64)` NOT NULL,
   * `recommendation_severity` `VARCHAR(32)` NOT NULL,
   * `thesis_refinement_actions` `TEXT[]` NOT NULL,
   * `is_active` `BOOLEAN` NOT NULL DEFAULT TRUE,
   * `superseded_by_version` `INTEGER` NULL,
   * `invalidated_by_version` `INTEGER` NULL,
   * `created_at` `TIMESTAMP WITHOUT TIME ZONE` NOT NULL,
   * `evaluation_version` `INTEGER` NOT NULL,
   * `aggregate_version` `INTEGER` NOT NULL,
   * `consensus_methodology_urn` `VARCHAR(256)` NOT NULL,
   * `consensus_policy_hash` `VARCHAR(64)` NOT NULL,
   * PRIMARY KEY (`postmortem_id`, `created_at`)

### **Partitioning Scheme**
* `review_records` and `postmortem_records` tables are quarterly partitioned by range based on `reviewed_at` and `created_at` respectively.
* A default catch-all partition (e.g., `review_records_default` and `postmortem_records_default`) will be created to process fall-through dates.
* Initial active partitions `review_records_2026_q2`, `review_records_2026_q3`, `postmortem_records_2026_q2`, and `postmortem_records_2026_q3` will be defined covering 2026-04-01 through 2026-10-01.

### **Indexes**
* Index on `review_records(record_urn, reviewed_at)` to guarantee uniqueness constraint.
* Index on `review_records(session_urn)` for paginated queries.
* Index on `review_records(decision_urn)` for lookups.
* Index on `postmortem_records(postmortem_urn, created_at)` for uniqueness.
* Index on `postmortem_records(decision_urn)` for lookups.

### **Immutability Triggers**
To enforce ADR-033 ledger guarantees, PL/pgSQL database triggers will block modifications on all core columns:
```sql
CREATE OR REPLACE FUNCTION block_review_record_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Deletes on review_records are prohibited.';
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.record_id <> NEW.record_id OR
           OLD.record_urn <> NEW.record_urn OR
           OLD.session_urn <> NEW.session_urn OR
           OLD.decision_urn <> NEW.decision_urn OR
           OLD.reviewer_urn <> NEW.reviewer_urn OR
           OLD.decision_journal_version <> NEW.decision_journal_version OR
           OLD.performance_version <> NEW.performance_version OR
           OLD.attribution_version <> NEW.attribution_version OR
           OLD.review_methodology_manifest_hash <> NEW.review_methodology_manifest_hash OR
           OLD.outcome_independent_score <> NEW.outcome_independent_score OR
           OLD.outcome_dependent_score <> NEW.outcome_dependent_score OR
           OLD.hindsight_bias_deviation <> NEW.hindsight_bias_deviation OR
           OLD.reviewed_at <> NEW.reviewed_at OR
           OLD.evaluation_version <> NEW.evaluation_version THEN
            RAISE EXCEPTION 'Updates to immutable review_records fields are prohibited.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```
* A similar function `block_postmortem_record_mutation()` will block all updates on `postmortem_records` except transitions on `is_active`, `superseded_by_version`, `invalidated_by_version`, and `aggregate_version`.
* Triggers will be attached to each partition table.

---

## 8. Replayability Implementation Plan

`ReviewReplayService` executes byte-for-byte reproducibility assertions.

* **Manifest Hashing**:
  * To replay ex-post inputs: fetches ex-ante decision journal, ex-post performance, and attribution outputs based on URN version pointers.
  * Serializes properties alphabetically in a JSON payload and generates a SHA-256 hash.
  * Asserts this matches `ReviewSession.raw_input_manifest_hash`.
* **Methodology Hashing**:
  * Instantiates a `ReviewMethodologyManifest` with the historical properties.
  * Recomputes the manifest hash.
  * Asserts it matches `ReviewRecord.review_methodology_manifest_hash`. If not, raises a `MethodologyDriftException`.
* **Consensus Lineage Verification**:
  * Fetches the `PostMortemRecord` to verify.
  * Queries the exact versions of the `ReviewRecord`s specified in `input_review_record_urns[]`.
  * Runs the solver script linked in `consensus_methodology_urn` with the policy configuration hash matching `consensus_policy_hash`.
  * Asserts the reconstructed `FailureClassification`, `SuccessClassification`, and `ImprovementRecommendation` match the persisted record.

---

## 9. ConsensusSolver Implementation Plan

The `ConsensusSolver` executes deterministic syntheses.

* **Inputs**:
  * List of active `ReviewRecord` objects for a given `decision_urn`.
  * Optional reputation weight mapping (`Dict[str, float]`) for reviewer URNs. (If omitted, defaults to $1.0$ for each reviewer).
* **Consensus Logic**:
  * **Boolean Classifications** (`thesis_error`, `execution_error`, etc.):
    * Sum the reputation weights of reviewers asserting `True`.
    * Sum the reputation weights of reviewers asserting `False`.
    * Assert `True` if:
      $$\frac{\sum_{\text{True}} w_i}{\sum_{\text{All}} w_j} > 0.5$$
    * Otherwise, resolve to `False`.
  * **Qualitative Recommendation Code** (`EXECUTION_WARNING`, etc.):
    * Accumulate weights for each code.
    * The recommendation code with the highest accumulated weight is selected.
    * *Tie-Breaker Rule*: In case of a tie, select the code with the highest severity:
      `THESIS_SUSPEND_RECOMMENDED` (5) > `THESIS_REVIEW_REQUIRED` (4) > `RISK_CONTROL_WARNING` (3) > `EXECUTION_WARNING` (2) > `PROCESS_IMPROVEMENT_REQUIRED` (1).
  * **Consensus Lineage Logging**:
    * Piles the input reviewer record URNs into a lexicographically sorted list and sets `input_review_record_urns`.
    * Resolves and records the active `consensus_methodology_urn` and `consensus_policy_hash`.
    * Creates and saves a new `PostMortemRecord` aggregate.

---

## 10. Projection Implementation Plan

Read-only projections are dynamically compiled from historical records to expose up-to-date metrics:

* **`WorkerReviewSummaryProjection`** (Review-focused):
  * Dynamic calculation from active `ReviewRecord`s for a reviewer URN:
    * `total_reviews_conducted`: Count of records.
    * `average_outcome_independent_score`: Mean of independent scores.
    * `average_outcome_dependent_score`: Mean of dependent scores.
    * `average_hindsight_bias_deviation`: Mean of deviations.
    * `thesis_errors_flagged`: Count of reviews asserting `thesis_error = True`.
* **`ThesisFailureRateProjection`** (Calibration-focused):
  * Ingests active `PostMortemRecord`s for a particular investment thesis URN:
    * `total_evaluations`: Count of finalized post-mortem records evaluating decisions based on this thesis.
    * `thesis_error_count`: Count of records with `thesis_error = True`.
    * `failure_rate`: Ratio of `thesis_error_count` to `total_evaluations`.

---

## 11. Testing Strategy

Complete verification requires executing 20+ test scenarios across multiple boundaries.

### **Unit Tests**
* **Aggregate State Machine**: Validate `ReviewSession` status transitions and OCC version updates. Test that invalid status jumps raise `StateTransitionError`.
* **Value Object Limits**: Validate `DecisionQualityAssessment` range checks ($[0.0, 1.0]$ bounds). Verify that invalid scoring weights trigger `ValueError`.
* **Immutability Enforcement**: Instantiation checks verifying that python modifications to `ReviewRecord` fields raise `AttributeError`.

### **Repository Tests**
* **Save & Fetch Isolation**: Verify `InMemory` and `File` adapters save and load states accurately. Assert that modifying a loaded object does not affect internal repository state without calling `save()`.

### **Replayability Tests**
* **Drift Detection**: Assert that updating the prompt version in `ReviewMethodologyManifest` yields a different hash and causes `ReviewReplayService` to raise `MethodologyDriftException`.

### **Consensus Tests**
* **Algorithm Execution**: Test solver with uniform and varying reputation weights. Assert that tie-breakers correctly choose the higher severity code. Assert that consensus lineage traces match inputs.

### **Postgres Tests**
* **Schema Integrity**: Assert tables can be created and queried. Verify that PK and FK constraints prevent corrupt mappings.

### **Trigger Tests**
* **Mutation Protection**: Run SQL scripts attempting to run `DELETE` or `UPDATE` on immutable columns (e.g., scoring or version hashes). Assert that psycopg raises trigger exceptions. Assert that updates to mutable columns (`is_active`, `superseded_by_version`) succeed.

### **Pagination Tests**
* **Cursor Walk**: Seed a session with 10 records. Query with `limit=3` and trace URN cursors. Assert all 10 records are fetched across 4 paginated calls, and `next_cursor` resolves to `None` on the final page.

---

## 12. Coverage Plan

* **Target Statement Coverage**: $\ge 90\%$
* **Target Branch Coverage**: $\ge 90\%$
* **Compliance Checks**:
  * Verification runs via `pytest --cov=src/karsa/review_postmortem --cov-branch --cov-fail-under=90`.
  * The codebase must contain no `pragma: no cover` statements or exclusions. All code lines must be evaluated.

---

## 13. Risk Assessment

* **Methodology Drift**: Changing prompting strategies changes evaluation criteria over time.
  * *Mitigation*: The `review_methodology_manifest_hash` binds models, policies, and prompts, allowing older records to be replayed against historical rubrics.
* **OCC Lock Contention**: Running many parallel reviews could block updates on a single session.
  * *Mitigation*: The Option B design isolates `ReviewRecord` and `PostMortemRecord` into independent aggregate roots, avoiding write lock conflicts on the parent session.

---

## 14. Acceptance Criteria

1. 100% test suite completion with $\ge 90\%$ statement and branch coverage in `review_postmortem`.
2. Database migration executes and builds range-partitioned tables.
3. PostgreSQL triggers block updates on all columns of `review_records` and `postmortem_records` except deactivation/lineage markers.
4. `ConsensusSolver` executes and returns identical outputs during replays using URN lineage walks.
5. All repository queries are paginated with cursor limits.

---

## 15. Final Verdict

### **`READY_FOR_IMPLEMENTATION`**
