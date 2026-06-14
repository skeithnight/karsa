# Sprint-37 Decision Journal Foundation Implementation Report

This document presents the details of the **Decision Journal Foundation** implementation for the Virtual Investment Firm (VIF) in Sprint-37.

---

## 1. Executive Summary

The Decision Journal has been successfully implemented under the flat package structure `src/karsa/decision_journal/` as the authoritative, immutable, write-once reasoning ledger of the VIF. It provides hindsight-prevention controls and pre-outcome reasoning capture before execution outcomes are realized.

The implementation offloads bulk JSON telemetry and prompt context snapshots to an external immutable object store, while indexing lightweight metadata, checksum hashes (SHA-256), and URIs in a relational PostgreSQL database. Database mutation checks via trigger functions block all update and delete actions, enforcing a strictly append-only ledger model. Active leaf tracking and corrections lineage traversal are supported, with Optimistic Concurrency Control (OCC) applied to projection updates.

All tests pass successfully, confirming 100% boundary isolation compliance.

---

## 2. Directory & Module Inventory

The implementation contains the following new modules under [decision_journal/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/):

* [__init__.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/__init__.py): Exposes all aggregates, value objects, events, ports, repositories, services, and projections.
* [exceptions.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/exceptions.py): Context-specific exception classes including `ImmutabilityViolationException` and `HindsightValidationException`.
* [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/value_objects.py): Implements immutable value objects for dataset references, prompts, telemetry spans, artifacts, and context snapshots.
* [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/models.py): Implements the base `ImmutableAggregate` and aggregate roots `DecisionJournalAggregate`, `DecisionRevisionAggregate`, and `DecisionEvidenceAggregate`.
* [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/events.py): Declares domain events including `DecisionJournalCreatedEvent` and `DecisionRevisionCreatedEvent`.
* [ports.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/ports.py): Defines boundary interface ports for object storage offloading (`ObjectStorePort`) and event publishing (`EventPublisherPort`).
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/repositories.py): Contains in-memory and PostgreSQL repository adapters enforcing partitioned layouts and mutation-blocking triggers.
* [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/services.py): Implements core capabilities: `DecisionJournalService`, `JournalLineageResolver`, and `ReplayService`.
* [projections.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/projections.py): Defines read-side projections including `ActiveLeafProjection` and `ReasoningLineageProjection`.
* [api.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/api.py): Exposes presentation endpoints using FastAPI for creating, revising, retrieving active leaves/lineage, and replaying decisions.

---

## 3. Aggregate Designs

* **DecisionJournalAggregate**: Represents the primary, write-once reasoning ledger entry. Immutability is enforced at the application layer by raising an exception on any property modifications.
* **DecisionRevisionAggregate**: Links a corrected decision context to a parent and root decision. This forms a correction lineage path before order checkout occurs.
* **DecisionEvidenceAggregate**: Represents post-trade attachment of trace evidence or artifacts to a specific decision URN.

---

## 4. Event Contracts

All events include unique event IDs, correlation/causation tracking, and timestamp metadata:
* `DecisionJournalCreatedEvent`: Emitted upon successful entry of a new journal record.
* `DecisionRevisionCreatedEvent`: Emitted when a revision is appended to an existing lineage.
* `DecisionEvidenceAttachedEvent`: Published when execution audit traces are attached post-outcome.

---

## 5. Persistence & OCC Strategy

* **PostgreSQL Schema**: Range partitioned by `created_at` (daily tables) and hash sub-partitioned by `root_decision_id` across 16 shards to prevent write hotspots.
* **Triggers**: PostgreSQL triggers execute `block_journal_mutation()` raising exceptions on any UPDATE or DELETE operations on `decision_journals`, `decision_revisions`, or `decision_evidences`.
* **OCC Verification**: `PostgresActiveLeafProjectionRepository` manages the mutable `active_leaf_projections` table. Updates verify version increments (`existing_version == incoming_version - 1`) to resolve race conditions.
* **Subtransactions**: PostgreSQL tests wrap failing insert assertions inside `conn.transaction()` savepoint contexts to prevent overall transaction abortion.

---

## 6. Architecture Compliance Matrix

| Target Invariant | Compliance Mechanism | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Hindsight Prevention** | Appends are blocked if trade execution has started. | Test `test_hindsight_prevention_on_revision` validates exception. | **COMPLIANT** |
| **Immutability Invariant** | Relational triggers throw exceptions on updates/deletes. | Test `test_postgres_exceptions` validates `ImmutabilityViolationException`. | **COMPLIANT** |
| **Active Leaf OCC** | Version numbers are verified on projection updates. | Test `test_active_leaf_projection_occ` asserts concurrency error. | **COMPLIANT** |
| **Replay & Hash Verification** | SHA-256 hashes of snapshots are validated. | Test `test_replay_checksum_verification` validates verification. | **COMPLIANT** |
| **Hexagonal Isolation** | Bounded imports are enforced. | Code verification confirms clean dependency directions. | **COMPLIANT** |

---

## 7. Technical Debt Register

* **DEBT-37.1 (utcnow warnings)**: Datetime values use `datetime.utcnow()` which is deprecated. Refactoring to timezone-aware UTC objects is deferred.
* **DEBT-37.2 (Alembic Migration scripts)**: Relational schemas and triggers are set up dynamically in repositories. Alembic integration migrations will be registered in the next evolution sprint.
