# Sprint-31 Observability Platform Foundation Plan

## 1. Context & Scope
This sprint is designated as **ARCHITECTURE DESIGN ONLY**.
In accordance with Karsa's workflow rules and repository constraints:
- No production code, database migrations, or test suites will be generated or executed.
- The sole objective is to establish the canonical architectural design for the **Observability Platform Foundation**.
- The deliverables consist of architecture blueprints, Architectural Decision Records (ADRs), and status tracking updates.

The Observability Platform is responsible for trace collection, metric aggregation, log ingestion, correlation tracking, and end-to-end lineage visualization for the Virtual Investment Firm (VIF).

## 2. Objectives
- Design a lock-free, zero-OCC append-only telemetry storage model for traces, metrics, logs, and lineage.
- Establish strict propagation rules for `TraceId`, `CorrelationId`, and `CausationId`.
- Resolve the ownership of lineage mapping and define VIF-wide correlation models.
- Author Architectural Decision Records: `ADR-045` (Observability Platform Ownership) and `ADR-046` (Telemetry Lineage and Traceability Model).

## 3. Target Architecture Alignment
The Observability Platform acts as the foundational cross-cutting utility supporting all VIF loops:
**Research → Thesis → Decision → Outcome → Performance → Attribution → Review → Governance → Post-Mortem → Capital Allocation → Learning**.

By providing structured trace propagation, it enables the platform to reconstruct exactly how a proposal moved from a research notebook to a live market trade, and how learning loops (reviews and post-mortems) impacted capital updates.

## 4. Bounded Context Deliverables
- **Telemetry Ingestion Registry**: Interfaces for trace, log, and metric streaming.
- **Lineage Registry**: Mapping of parent-child relationships across all contexts.
- **Trace Context Spec**: Standardized header and context propagation specifications.

## 5. Work Packages (Design-Only)
- **WP-31.1**: Telemetry database schema design (traces, logs, metrics, lineage).
- **WP-31.2**: Correlation, causation, and context propagation rules.
- **WP-31.3**: Lineage reconstruction models and replay validation.
- **WP-31.4**: Authoring ADR-045 and ADR-046.
