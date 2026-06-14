# Sprint-35 Portfolio Engine Foundation Implementation Plan

This document defines the implementation plan for the **Portfolio Engine Foundation** bounded context.

---

## 1. Objectives
* Implement the Portfolio Engine as the authoritative Real-Time Book of Record (RTBOR).
* Build versioned aggregates: `PortfolioAggregate`, `PositionAggregate`, `CashLedgerAggregate`, `ValuationAggregate`.
* Build standard in-memory and file-backed repositories supporting OCC and valuation immutability.
* Develop services for fill ingestion, NAV valuation, and sector exposure calculations.
* Verify 100% boundary isolation via unit and integration tests.

---

## 2. Dependencies
* Consumption of `OrderFilledEvent` and `OrderRejectedEvent` emitted by the Execution Engine.
* Delivery of NAV valuation snapshots and history to the Performance Engine.

---

## 3. Scope
* `src/karsa/portfolio/` flat package modules.
* Core unit, integration, and architecture tests under `tests/karsa/portfolio/`.
