# Sprint-22 Attribution Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **DESIGN ONLY**.
In accordance with the repository constraints:
- No production code, database migrations, or test code will be generated or executed.
- The sole objective is to design the architectural foundations for the **Attribution Engine Foundation**.
- The architecture package will stop at the `ARCHITECTURE_FREEZE` transition.

## 2. Objectives
- Define the core Attribution Engine domain model, establishing `AttributionRecord` and `AttributionAdjustment` as immutable, append-only aggregate roots.
- Demote `CostLedgerProjection` to a read-side projection to eliminate database Optimistic Concurrency Control (OCC) lock contention.
- Design the hybrid multi-dimensional cost attribution model separating typed core Virtual Investment Firm dimensions (`research_run_id`, `thesis_id`, `worker_id`, `portfolio_id`, `strategy_id`) from dynamic JSONB `extended_dimensions`.
- Establish indexing and query strategies to support high-velocity analytical queries on 100M+ records.
- Address provider pricing drift, cost corrections, and historical cost preservation using immutable append-only adjustments.
- Formulate Architecture Decision Records (ADRs) to lock core design decisions.

## 3. Architecture Alignment
The Attribution Engine is the authoritative financial ledger of Karsa. It consumes provider telemetry completion events, calculates actual dollar costs, and attributes them across platform dimensions.

Canonical architectural documentation will be stored in:
- [12-attribution-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/12-attribution-engine.md)

Related ADRs:
- [ADR-027: Attribution Engine Context Ownership and Boundaries](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-027-attribution-engine-ownership.md)
- [ADR-028: Multi-Dimensional Cost Attribution Model](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-028-cost-attribution-model.md)

## 4. Bounded Context Deliverables
- **Cost Calculation Context**: Ingests provider execution events, fetches pricing, and calculates actual dollar costs.
- **Attribution Ledger Context**: Records immutable `AttributionRecord` entries, appends `AttributionAdjustment` corrections, and publishes events to update downstream projections.
- **Query & Reporting Context**: Exposes read-only financial summaries and cumulative metrics from the `CostLedgerProjection` for portfolio engines and dashboards.

## 5. Work Packages (Design-Only)
- **WP-22.1**: Domain modeling of `AttributionRecord` and append-only `AttributionAdjustment` aggregates.
- **WP-22.2**: Read-side `CostLedgerProjection` schema and asynchronous update/upsert SQL design.
- **WP-22.3**: Hybrid multi-dimensional context tags, schema validation, and B-Tree/GIN database indexing design.
- **WP-22.4**: Replay historical data loading, pricing drift isolation, and currency normalization (Decimal USD) design.
- **WP-22.5**: Challenge matrix review and ADR drafting.

## 6. Sprint Closure
- **Architecture Completed**: Core domains, value objects, read-side projections, and Postgres database schemas defined and frozen under [12-attribution-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/12-attribution-engine.md).
- **Implementation Completed**: Verified domain models, repositories, application services, events, and projection rebuilding routines in the code namespace `karsa.attribution`.
- **Audit Completed**: Verification of frozen specifications, aggregate boundaries, replay determinism, and 100% test coverage (16 test cases passing).
- **Remediation Completed**: Consolidated all artifacts, aligned ROADMAP.md, and documented deprecation warnings as technical debt.


