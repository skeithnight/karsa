# Sprint-37 Plan: Decision Journal Foundation Pre-Implementation Readiness Audit

This document presents the Pre-Implementation Readiness Audit for Sprint-37, verifying that the frozen architecture can safely move into the implementation phase.

---

## 1. Executive Summary

A comprehensive pre-implementation readiness audit has been conducted on the frozen Sprint-37 Decision Journal architecture. No fatal design blockers or architectural gaps were discovered. The package boundaries, domain interfaces, PostgreSQL database schemas, Object Storage mapping, and event contracts are fully specified and aligned with VIF principles.

The VIF control loop is secured by prioritizing the Decision Journal in Sprint-37, which resolves the `BLOCKING_GAP` in pre-outcome auditing. The project is cleared to proceed directly to the implementation phase.

**Readiness Verdict**: `IMPLEMENTATION_PLAN_APPROVED`

---

## 2. Architecture-to-Code Mapping Matrix

The frozen architecture maps to the following package structure:

| Approved Component | Package Name | Module Path | Domain Entity / Class Name |
| :--- | :--- | :--- | :--- |
| **Aggregate Root** | `karsa.decision_journal` | `domain/models.py` | `DecisionJournal` |
| **Value Objects** | `karsa.decision_journal` | `domain/value_objects.py` | `DecisionRationale`, `DecisionEvidence`, `DecisionHypothesis`, `DecisionConfidence` |
| **Domain Events** | `karsa.decision_journal` | `domain/events.py` | `DecisionJournalCreatedEvent`, `DecisionJournalCorrectedEvent` |
| **Repository Ports** | `karsa.decision_journal` | `domain/repositories.py` | `DecisionJournalRepository` |
| **Infrastructure Adapter**| `karsa.decision_journal` | `infrastructure/storage/postgres_repository.py` | `PostgresDecisionJournalRepository` |
| **Object Storage Adapter** | `karsa.decision_journal` | `infrastructure/storage/s3_object_store.py` | `S3ObjectStoreAdapter` |
| **Application Services** | `karsa.decision_journal` | `application/services.py` | `DecisionJournalApplicationService`, `JournalLineageResolver` |
| **Projections** | `karsa.decision_journal` | `domain/projections.py` | `ActiveLeafProjection` |
| **API Presentation** | `karsa.decision_journal` | `presentation/api.py` | `DecisionJournalRouter` (FastAPI) |
| **Exception Hierarchy** | `karsa.decision_journal` | `presentation/exceptions.py` | `HindsightValidationException`, `ImmutabilityViolationException` |

---

## 3. Package Structure Validation

The code files will reside under the following directory hierarchy:

```
src/karsa/decision_journal/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── models.py          # DecisionJournal write-once aggregate
│   ├── value_objects.py   # Rationale, Evidence, Hypothesis, Confidence
│   ├── events.py          # Created and Corrected event models
│   ├── repositories.py    # Domain interface for repositories
│   └── projections.py     # Active leaf projection structures
├── application/
│   ├── __init__.py
│   ├── services.py        # Service orchestrating validation & offloading
│   └── ports.py           # ObjectStore and EventPublisher abstractions
├── infrastructure/
│   ├── __init__.py
│   └── storage/
│       ├── __init__.py
│       ├── postgres_repository.py  # Psycopg3 repository adapter
│       ├── s3_object_store.py      # Boto3/S3 object lock adapter
│       ├── mappers.py              # Domain-to-DB record mappings
│       └── records.py              # DB schema mapping records
└── presentation/
    ├── __init__.py
    ├── api.py             # FastAPI router definition
    └── exceptions.py      # Custom exception handlers
```

---

## 4. Aggregate Validation

* **Aggregate Root**: [DecisionJournal](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/implementation/sprint-37/architecture.md#L70) is the sole aggregate root representing a write-once ledger entry.
* **Transaction Boundaries**: Each database transaction commits a single `DecisionJournal` record. Row modifications or updates are blocked, eliminating locking write hotspots.
* **Immutability Guarantees**: Class properties are frozen. Any `__setattr__` calls on instantiated aggregates raise a `TypeError` at runtime.
* **Append-Only Enforcement**: Enforced at the database level using a PostgreSQL trigger function that blocks `UPDATE` and `DELETE` queries.

---

## 5. Persistence Design Validation

### Persistence Matrix
| Database / Store | Table / Bucket Name | Partition Strategy | Indexing Strategy |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `decision_journals` | Range partitioned by `created_at` (Daily chunks). Hash partitioned by `root_decision_id` (16 partitions). | B-Tree index on `(root_decision_id, created_at)`, B-Tree on `parent_decision_id`. |
| **Object Storage** | `karsa-decision-journal-payloads` | S3 Prefix structure: `contexts/YYYY-MM-DD/` | Object key matching URN (`dec-123.json`). |

* **Triggers**: PostgreSQL trigger function raises an exception on updates and deletes, preventing administrative tampering.
* **Object Lock**: S3/GCS buckets configured with Object Lock in Compliance Mode for a retention period of 7 years.

---

## 6. Event Contract Validation

* **`DecisionJournalCreatedEvent`**:
  - **Producer**: `DecisionJournalApplicationService`
  - **Consumers**: CIO Engine, Execution PEP, Performance Engine, Review Engine, Post-Mortem Engine.
  - **Versioning**: Version 1 (JSON Schema verified).
  - **Replayability**: Provides the chronological record to rebuild performance projections.
* **`DecisionJournalCorrectedEvent`**:
  - **Producer**: `DecisionJournalApplicationService`
  - **Consumers**: Performance Engine, Review Engine, Post-Mortem Engine.
  - **Versioning**: Version 1.
  - **Replayability**: Declares the linked lineage trace of correction branches.

---

## 7. Projection Validation

* **Active Leaf Projection**: 
  - Tracks the finalized active leaf URN of a correction chain before trade execution checkout.
  - **OCC Strategy**: Since multiple corrections can theoretically be submitted concurrently, the `active_leaf_projection` read-side cache in Redis checks a monotonically increasing version number (`OCC Required`) before updating leaf references.
* **Reasoning Lineage Projection**: Reconstructs the complete parent-child Directed Acyclic Graph (DAG) for audit reports.

---

## 8. Object Store Validation

To prevent database bloating and ensure compliance with context boundaries, the Decision Journal behaves as a **reference-only registry**:

* **Datasets**: Research datasets are stored in the Research Engine. The journal stores only the SHA-256 checksum and URN of the dataset.
* **Telemetry**: Trace spans are stored in the Observability Platform. The journal stores only the `telemetry_span_id` reference URN.
* **Model Binaries**: Models are stored in the Thesis Engine. The journal stores only the URN and weight parameters hash.

---

## 9. Security Validation

* **Hindsight Prevention Check**: Downstream consumers (Performance, Attribution) reject any journal entries whose `created_at` timestamp is not strictly prior to the trade execution's `started_at` timestamp.
* **Hash Verification**: Downstream auditors read the `context_hash` from PostgreSQL, download the payload from S3, compute its SHA-256 checksum, and assert an exact match to verify that no out-of-band editing occurred.
* **Lineage Integrity**: The database-level foreign key on `parent_decision_id` guarantees that parent records cannot be orphaned or deleted.

---

## 10. Testing Strategy Validation

The test suite will verify the implementation against 90%+ branch coverage:

1. **Unit Tests** (`tests/karsa/decision_journal/domain/test_models.py`):
   - Verify immutability of `DecisionJournal` (fails on property set).
   - Verify confidence boundary constraints ($0.0 \le p \le 1.0$).
2. **Repository Tests** (`tests/karsa/decision_journal/infrastructure/test_postgres_repository.py`):
   - Verify that database trigger blocks `UPDATE` and `DELETE` operations.
   - Verify partition routing for daily range tables.
3. **Replay Tests** (`tests/karsa/decision_journal/application/test_replay.py`):
   - Verify that replaying a decision retrieves the S3 context blob and reconstructs active model parameters.
4. **Integration Tests** (`tests/karsa/decision_journal/test_integration.py`):
   - Verify end-to-end FastAPI router execution, S3 bucket writes, and event bus publishing.

---

## 11. Migration Strategy Validation

1. **Alembic DB Migrations**:
   - Create tables, partition hierarchies, indexes, and Pl/pgSQL trigger function.
2. **Object Store Setup**:
   - Provision S3 bucket with Object Lock enabled via localstack or cloud templates.
3. **Rollback Strategy**:
   - Drops partition tables and trigger functions. Note: S3 Object Lock configuration cannot be disabled once enabled in Compliance Mode; rollback is limited to deleting database reference indexes.

---

## 12. Acceptance Criteria

1. **Immutability Invariant**: Any SQL update or delete query targeting `decision_journals` must fail with an SQL error code `P0001` (Raise Exception).
2. **Validation Invariant**: Creating a journal with confidence `p = -0.1` or `p = 1.1` must raise a `ValueError`.
3. **PEP Enforcement Invariant**: The Execution PEP must validate that the `decision_id` exists in the database and was created before the order execution started.

---

## 13. Production Readiness Risk Assessment

### Risk Register
| Risk | Severity | Operational Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Object Store Latency** | `Medium` | S3 synchronous writes could block trade staging for 10-50ms. | Execute S3 uploads asynchronously in parallel threads, and wait for confirmation only at the CIO signature authorization checkout. |
| **Index DB Growth** | `Low` | Large transaction numbers could bloat database indexes. | Use daily range partitions and drop old indexes on partitions older than 90 days (archived to read-only cold stores). |

---

## 14. Readiness Findings

* **Dependencies**: All read-only dependencies (Thesis URN, active worker status URNs) are fully defined.
* **Blockers**: No blockers. All systems are ready for implementation.

---

## 15. Documentation Delta Analysis

* **ROADMAP.md**: Sprints re-prioritized to place Decision Journal in Sprint-37.
* **Traceability Matrix**: Updated to include Sprint-37.

---

## 16. Final Readiness Verdict

### **IMPLEMENTATION_PLAN_APPROVED**
