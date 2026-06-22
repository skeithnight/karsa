# Sprint-23 Thesis Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **DESIGN ONLY**.
In accordance with the repository constraints:
- No production code, database migrations, or test code will be generated or executed.
- The sole objective is to design the architectural foundations for the **Thesis Engine Foundation**.
- The architecture package will stop at the `ARCHITECTURE_FREEZE` transition.

The Thesis Engine Foundation defines the first-class investment hypothesis system of Karsa, serving as the canonical bridge between Research, Thesis, Decision, Outcome, and Review within the Virtual Investment Firm (VIF) target architecture.

## 2. Objectives
- Define boundaries of context ownership between Thesis, Research, Performance, Capital Allocation, and Decision Journal contexts.
- Establish the domain model for Thesis management, separating `ThesisDefinition` and `ThesisVersion` as aggregate roots.
- Establish a version-controlled evolution model (immutable activated versions, new versions created upon change).
- Design a Finite State Machine (FSM) for Thesis lifecycle tracking (`DRAFT` → `REVIEW` → `ACTIVE` → `INVALIDATED` → `ARCHIVED`).
- Design replay paths linking decisions to exact historical `thesis_version_id` values to preserve deterministic audit capability.
- Formulate the Event Contracts, persistence schema, and sequence diagrams.
- Author Architectural Decision Records (ADRs) to lock the design.

## 3. Architecture Alignment
The Thesis Engine exists independently of other platform modules. It links to external boundaries strictly via identifiers (such as `research_run_id`, `thesis_id`, `thesis_version_id`, `outcome_id`, `attribution_id`, and `trace_id`).

Canonical architectural documentation will be stored in:
- [13-thesis-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/13-thesis-engine.md)

Related ADRs:
- [ADR-029: Thesis Engine Bounded Context and Ownership Boundaries](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-029-thesis-engine-ownership.md)
- [ADR-030: Thesis Lifecycle State Machine and Version Evolution](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-030-thesis-lifecycle-and-versioning.md)

## 4. Bounded Context Deliverables
- **Thesis Definition Context**: Governs metadata definitions, description headers, and logical ownership mappings.
- **Thesis Version & Hypothesis Context**: Controls the immutable snapshots of invalidation criteria, risks, assumptions, horizon ranges, and qualitative hypothesis points.
- **Thesis Integration & Reference Context**: Maps structural linkages to performance evaluations, decision journals, research backtests, and capital allocations.

## 5. Work Packages (Design-Only)
- **WP-23.1**: Domain modeling of `ThesisDefinition`, `ThesisVersion`, invalidation value objects, and risk/assumption entities.
- **WP-23.2**: Finite State Machine lifecycle transition policies, validation constraints, and transition audits.
- **WP-23.3**: Replay determinism lookup path, version linkage, and database indexing strategies.
- **WP-23.4**: Event contracts design, publisher/subscriber matrices, and database tables DDL schemas.
- **WP-23.5**: Challenge matrix review and ADR drafting.
