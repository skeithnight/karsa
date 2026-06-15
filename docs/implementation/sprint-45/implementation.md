# Sprint-45 Capital Allocation Engine Foundation Implementation Record

This document records the implementation details for Sprint-45 (Capital Allocation Engine Foundation), detailing the domain model, repositories, and application services developed.

---

## 1. Executive Summary
The Capital Allocation Engine Foundation has been successfully implemented across all four batches.
* **Batch 1**: Domain Layer (Models, Value Objects, Events, Lineage)
* **Batch 2**: Repository Layer (Interfaces, InMemory and File persistence)
* **Batch 3**: Application Services (Calculation, Ranking, Replay, Invalidation, and OCC Conflict Handling)
* **Batch 4**: Persistence Layer (PostgreSQL Repositories, Alembic Migrations, Immutability Triggers, and Integration Tests)

All code paths have been thoroughly tested with 100% statement and branch coverage in both the core application services and the PostgreSQL persistence implementation.

---

## 2. Implemented Services

### 2.1 `AllocationCalculationService`
* **Responsibilities**: Creates new capital allocation decisions, calculates scoring metrics based on ex-post worker data, resolves predecessor record supersedence, and publishes events.
* **OCC Verification**: Employs an optimistic concurrency control loop with a retry limit of 3, catching version conflicts and retrying automatically.
* **Methodology Validation**: Verifies that methodology parameters (URN, policy hash, and strategy version) match the manifest hash before persisting decision records.

### 2.2 `RankingProjectionService`
* **Responsibilities**: Dynamically builds worker rank listings in-memory without persistence.
* **Sorting Determinism**: Implements a strict 5-factor ordering hierarchy:
  1. Allocation Score (Descending)
  2. Brier Score (Ascending)
  3. Selection Return (Descending)
  4. Review Score (Descending)
  5. Worker URN (Alphabetical Ascending)

### 2.3 `AllocationReplayService`
* **Responsibilities**: Validates the historical execution path of a given decision.
* **Validation Mode**: Performs checks strictly against a pinned manifest parameter without querying live tables to prevent runtime drift.
* **Drift Detection**: Detects modifications in methodology URN, policy hash, or strategy version, raising structured exceptions.

### 2.4 `AllocationInvalidationService`
* **Responsibilities**: Disables lineage sequences, marking active records as inactive and tracking the invalidating execution version.

---

## 3. PostgreSQL Persistence & Schema

### 3.1 Repositories
* **`PostgresAllocationSessionRepository`**: Manages session state and version controls.
* **`PostgresAllocationDecisionRecordRepository`**: Enforces OCC, handles record retrieval, keyset pagination sorted alphabetically by `record_urn`, and constructs cycle-safe lineage chains in-memory utilizing indexes on `(worker_urn, horizon_id)`.

### 3.2 Migrations (`45_capital_allocation_init.py`)
An Alembic migration was created implementing:
* Table `allocation_sessions` for storing session runs.
* Table `allocation_decision_records` partitioned by `calculated_at` with range partitioning.
* A default partition table `allocation_decision_records_default`.

### 3.3 Immutability Trigger (`block_allocation_record_mutation`)
A database-level PL/pgSQL trigger function checks mutations:
* **Blocked**: Updates to `allocation_score`, `allocation_weight`, `risk_budget`, `worker_urn`, timestamps, and methodology metadata. Any `DELETE` operation is blocked.
* **Allowed**: Updates to `is_active` (TRUE -> FALSE), `supersedes_record_urn`, `invalidates_record_urn`, and `aggregate_version`.

---

## 4. Test & Coverage Results
All integration and unit tests are successfully validated:
* **`allocation_services.py` Statement Coverage**: 100%
* **`allocation_services.py` Branch Coverage**: 100%
* **`postgres_allocation_repositories.py` Statement Coverage**: 100%
* **`postgres_allocation_repositories.py` Branch Coverage**: 100%

---

## 5. Verification Evidence
All tests run successfully under pytest:
```bash
.venv/bin/pytest --cov=src/karsa/allocation/ --cov-branch --cov-report=term-missing tests/karsa/allocation/
```
Output:
* 63 passed, 1 skipped.
* `allocation_services.py` has 100% coverage.
* `postgres_allocation_repositories.py` has 100% coverage.
