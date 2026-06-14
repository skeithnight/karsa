# Sprint-37 Decision Journal Foundation Implementation Report

This document presents the details of the **Decision Journal Foundation** implementation for the Virtual Investment Firm (VIF) in Sprint-37, incorporating value objects and Alembic migration remediation.

---

## 1. Executive Summary

The Decision Journal has been successfully implemented under the flat package structure `src/karsa/decision_journal/` as the authoritative, immutable, write-once reasoning ledger of the VIF. It provides hindsight-prevention controls and pre-outcome reasoning capture before execution outcomes are realized.

The implementation:
* Offloads bulk JSON telemetry and prompt context snapshots to an external immutable object store, while indexing lightweight metadata, checksum hashes (SHA-256), and URIs in a relational PostgreSQL database.
* Employs strictly append-only database schemas. Database mutations are blocked by trigger functions that prevent `UPDATE` and `DELETE` queries.
* Removes primitive obsession by wrapping reasoning arguments, expected bounds, and probability projections into explicit domain value objects (`DecisionRationale`, `DecisionHypothesis`, and `DecisionConfidence`).
* Hardens confidence projections by rejecting `NaN`, infinite, and invalid bounds.
* Moves database schema initialization and trigger configuration out of repository runtime startup code and registers them under Alembic migration tracks.

---

## 2. Directory & Module Inventory

The implementation contains the following modules under [decision_journal/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/):

* [__init__.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/__init__.py): Exposes aggregates, value objects, events, ports, repositories, services, and projections.
* [exceptions.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/exceptions.py): Context-specific exception classes including `ImmutabilityViolationException` and `HindsightValidationException`.
* [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/value_objects.py): Implements immutable value objects for dataset references, prompts, telemetry spans, artifacts, context snapshots, rationales, hypotheses, and confidence values.
* [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/models.py): Implements the base `ImmutableAggregate` and aggregates `DecisionJournalAggregate`, `DecisionRevisionAggregate`, and `DecisionEvidenceAggregate`.
* [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/events.py): Declares domain events including `DecisionJournalCreatedEvent` and `DecisionRevisionCreatedEvent`.
* [ports.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/ports.py): Defines boundary interface ports for object storage offloading (`ObjectStorePort`) and event publishing (`EventPublisherPort`).
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/repositories.py): Contains PostgreSQL repository adapters enforcing daily partitioned range/hash layouts and active leaf projection lookups.
* [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/services.py): Implements core capabilities: `DecisionJournalService`, `JournalLineageResolver`, and `ReplayService`.
* [projections.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/projections.py): Defines read-side projections including `ActiveLeafProjection` and `ReasoningLineageProjection`.
* [api.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/api.py): Exposes presentation endpoints using FastAPI for creating, revising, retrieving active leaves/lineage, and replaying decisions.

---

## 3. Aggregate Designs

* **DecisionJournalAggregate**: Represents the primary, write-once reasoning ledger entry. Immutability is enforced at the application layer by raising an exception on any property modifications. Exposes `rationale`, `hypothesis`, and `confidence` value objects.
* **DecisionRevisionAggregate**: Links a corrected decision context to a parent and root decision. Exposes convenience properties to access value objects.
* **DecisionEvidenceAggregate**: Represents post-trade attachment of trace evidence or artifacts to a specific decision URN.

---

## 4. Value Object Hardening Rationale

Investment decisions are highly sensitive to probability boundaries and variance distributions. Storing raw floats or dictionaries risks silent truncation or math errors. The [DecisionConfidence](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/decision_journal/value_objects.py#L57) class is hardened to validate the following invariants:
* **Reject NaN**: Statistical calculations involving empty values or divisions by zero generate `NaN`. If persisted, these values break Brier scores and Sharpe calculations downstream.
* **Reject +Inf / -Inf**: Infinite values represent mathematical boundaries that distort calibration integrals.
* **Enforce Probability Bounds**: Strictly asserts $0.0 \le p \le 1.0$.
* **Reject Negative Standard Deviation**: Standard deviation represents volatility and must be non-negative.

---

## 5. Event Contracts

All events include unique event IDs, correlation/causation tracking, and timestamp metadata:
* `DecisionJournalCreatedEvent`: Emitted upon successful entry of a new journal record.
* `DecisionRevisionCreatedEvent`: Emitted when a revision is appended to an existing lineage.
* `DecisionEvidenceAttachedEvent`: Published when execution audit traces are attached post-outcome.

---

## 6. Persistence & OCC Strategy

* **PostgreSQL Schema**: Range partitioned by `created_at` (daily tables) and hash sub-partitioned by `root_decision_id` across 16 shards to prevent write hotspots.
* **Alembic Migrations**: Schema creation and PG triggers are migrated to `alembic/versions/37_decision_journal_init.py`. No DDL code resides in repository classes.
* **Triggers**: PostgreSQL triggers execute `block_journal_mutation()` raising exceptions on any UPDATE or DELETE operations.
* **OCC Verification**: `PostgresActiveLeafProjectionRepository` manages the mutable `active_leaf_projections` table. Updates verify version increments to resolve race conditions.

---

## 7. Architecture Compliance Matrix

| Target Invariant | Compliance Mechanism | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Hindsight Prevention** | Appends are blocked if trade execution has started. | Test `test_hindsight_prevention_on_revision` validates exception. | **COMPLIANT** |
| **Immutability Invariant** | Relational triggers throw exceptions on updates/deletes. | Test `test_postgres_exceptions` validates `ImmutabilityViolationException`. | **COMPLIANT** |
| **Active Leaf OCC** | Version numbers are verified on projection updates. | Test `test_active_leaf_projection_occ` asserts concurrency error. | **COMPLIANT** |
| **Replay & Hash Verification** | SHA-256 hashes of snapshots are validated. | Test `test_replay_checksum_verification` validates verification. | **COMPLIANT** |
| **Hexagonal Isolation** | Bounded imports are enforced. | Code verification confirms clean dependency directions. | **COMPLIANT** |
| **Value Object Hardening** | Rejects NaN, Inf, and invalid bounds on confidence. | Test `test_confidence_rejects_nan_probability` asserts validation error. | **COMPLIANT** |
| **Alembic Schema Setup** | DDL initialization moved to migrations. | Inspected repository code and ran pytest suite. | **COMPLIANT** |

---

## 8. Technical Debt Register

* **DEBT-37.1 (utcnow warnings)**: Datetime values use `datetime.utcnow()` which is deprecated. Refactoring to timezone-aware UTC objects is deferred.
