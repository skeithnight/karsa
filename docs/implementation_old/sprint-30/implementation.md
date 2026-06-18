# Sprint-30 Capital Allocation Engine Foundation - Architectural Implementation

This document summarizes the architectural design artifacts generated during Sprint-30.

## 1. Design Deliverables

The following canonical documents have been authored and checked into the repository:

1. **System Architecture Definition**:
   - [docs/architecture/20-capital-allocation-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/20-capital-allocation-engine.md)
   - Defines the domain model (zero mutable aggregates, two write-once ledger tables), calibrated return and confidence formulas, SQL schemas, sequence diagrams, and scalability designs.

2. **Architectural Decision Records (ADRs)**:
   - [docs/adr/ADR-043-capital-allocation-engine-ownership.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-043-capital-allocation-engine-ownership.md)
     - Defines boundaries, single-writer rules, and integration triggers with Governance, Performance, Attribution, and CIO contexts.
   - [docs/adr/ADR-044-capital-allocation-and-evidence-weighting-model.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-044-capital-allocation-and-evidence-weighting-model.md)
     - Establishes evidence calibration, survivorship bias prevention parameters, and write-once ledger patterns.

3. **Consolidated Roadmap & Dashboard**:
   - [docs/roadmap/ROADMAP.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/roadmap/ROADMAP.md)
     - Updated to reflect Sprint-30 closed (Architecture Design Only) and total active ADR count of 44.

## 2. Review Activities

- Aggressive architecture challenges on allocation ownership, aggregate boundaries, replay determinism, confidence calibration, and scalability were conducted.
- Removed policy OCC and version contention by converting `AllocationPolicy` to a write-once ledger table.
- Standardized calibrated confidence bounds and frozen attribution snapshots inside the object-store context payload to prevent replay drift.
