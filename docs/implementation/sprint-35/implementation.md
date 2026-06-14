# Sprint-35 Portfolio Engine Foundation Implementation Report

This document presents the details of the **Portfolio Engine Foundation** implementation for VIF.

---

## 1. Executive Summary

The Portfolio Engine has been successfully implemented under the flat package structure `src/karsa/portfolio/` as the authoritative Real-Time Book of Record (RTBOR). It consumes executions fills directly from the Execution Engine and generates cash ledger state updates, position units, Net Asset Value (NAV) valuations, exposures, and benchmark reference valuations.

All tests pass successfully, confirming 100% boundary isolation compliance.

---

## 2. Directory & Module Inventory

The implementation contains the following new modules under [portfolio/](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/):

* [__init__.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/__init__.py): Exposes all models, value objects, repositories, events, and integration ports.
* [exceptions.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/exceptions.py): Domain-specific exceptions including `ConcurrencyConflictError` and `DatabaseImmutabilityError`.
* [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/value_objects.py): Implements immutable data structures: `Money`, `HoldingLot`, `AssetExposure`, `BenchmarkReference`, and `PortfolioSnapshot`.
* [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/models.py): Implements the four required versioned aggregates: `PortfolioAggregate`, `PositionAggregate`, `CashLedgerAggregate`, and `ValuationAggregate`.
* [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/events.py): Implements the six required event contract schemas with full correlation and causation metadata tracking.
* [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/repositories.py): Implements memory-backed and file-backed database storage with strict OCC concurrency validations and immutability invariants.
* [services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/services.py): Implements `PortfolioProjectionService` (fill ingestion), `PortfolioValuationService` (NAV calculation), `ExposureCalculationService`, and `BenchmarkRegistryService`.
* [projections.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/projections.py): Defines read-side projections for assets and valuations.
* [ports.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/ports.py): Defines integration boundary ports for Execution, Performance, and Risk engines.
* [api.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/api.py): Exposes presentation services for trade fills and state valuations.

---

## 3. Aggregate Designs

* **PortfolioAggregate**: Tracks ownership and portfolio lifecycle.
* **PositionAggregate**: Decoupled from the root portfolio aggregate. Manages specific asset units, average cost basis, and purchase tax lot history ([HoldingLot](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/portfolio/value_objects.py#L18)).
* **CashLedgerAggregate**: Tracks currency balances, cash adjustment checks, and available funds.
* **ValuationAggregate**: Immutable snapshot containing asset valuations, exposures, cash levels, and reference benchmark levels at calculation time.

---

## 4. Event Contracts

All events inherit standard VIF attributes (`event_version`, `correlation_id`, `causation_id`, and `timestamp`) and support serialization:
* `HoldingsUpdatedEvent`: Published on position balance mutations.
* `CashUpdatedEvent`: Published on cash ledger balance adjustments.
* `PositionOpenedEvent`: Emitted when units transition from 0 to positive.
* `PositionClosedEvent`: Emitted when position units reach 0, detailing realized PnL.
* `PortfolioValuationCalculatedEvent`: Emitted after cash/position valuation calculation completes, publishing Net Asset Value (NAV).
* `ExposureCalculatedEvent`: Emitted to publish current sector/asset weight exposures.

---

## 5. Persistence & OCC Strategy

* **In-Memory Repositories**: Utilize `copy.deepcopy` to simulate transactional memory isolation and prevent reference-sharing issues during aggregate modifications.
* **File-Backed Repositories**: Write state JSON objects under `.karsa/portfolio/`.
* **OCC Verification**: Saves verify that the incoming aggregate version matches the database record version plus one:
  ```python
  if existing and existing.aggregate_version != incoming.aggregate_version - 1:
      raise ConcurrencyConflictError("OCC Conflict")
  ```
* **Immutability Invariant**: Valuation saves verify that the `valuation_id` does not exist. Any attempt to update or overwrite an existing valuation raises a `DatabaseImmutabilityError`.

---

## 6. Architecture Compliance Matrix

| Target Invariant | Compliance Mechanism | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Sole NAV Ownership** | Portfolio is the single context writing NAV to a database. | Check that Performance and Execution contain zero NAV calculations or holdings write code. | **COMPLIANT** |
| **No Predictive Risk** | Portfolio calculates only linear, deterministic exposures. | Code analysis confirms zero VaR or predictive scenarios in `services.py`. | **COMPLIANT** |
| **OCC Validation** | Repos check aggregate versions on write. | Test `test_in_memory_repository_occ` raises OCC errors on version conflicts. | **COMPLIANT** |
| **Immutability** | Valuations raise errors on update/delete actions. | Test `test_file_repository_immutability` raises errors on duplicate inserts. | **COMPLIANT** |
| **Hexagonal Isolation** | Imports are restricted. | Test `test_architecture_import_isolation` asserts zero imports of `karsa.performance`, `karsa.risk`, or `karsa.governance` modules. | **COMPLIANT** |

---

## 7. Technical Debt Register

* **DEBT-35.1 (PostgreSQL Migrations)**: SQL schemas exist in design drafts only. Production requires migration scripts and raw DB drivers integration in the next evolution sprint.
* **DEBT-35.2 (utcnow warnings)**: Services use `datetime.utcnow()` which is deprecated. These should be refactored to use timezone-aware datetime wrappers.
