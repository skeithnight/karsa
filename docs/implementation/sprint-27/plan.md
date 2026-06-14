# Sprint-27 Attribution Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **ARCHITECTURE DESIGN ONLY**.
In accordance with Karsa's workflow rules and repository constraints:
- No production code, database migrations, or test suites will be generated or executed.
- The sole objective is to establish the canonical architectural design for the **Attribution Engine Foundation**.
- The deliverables consist of architecture blueprints, Architectural Decision Records (ADRs), and status tracking updates.

The Attribution Engine is the canonical causal analysis subsystem for the Virtual Investment Firm (VIF). It determines outcome attribution and causal contributions across workers, theses, research artifacts, market regimes, execution pipelines, and strategies. It explains performance outcomes to enable risk-adjusted capital reallocation.

## 2. Objectives
- Define boundaries between the Attribution Engine and the Research, Thesis, Performance, Review, Governance, and Capital Allocation contexts.
- Establish the domain model for the Attribution Engine, detailing aggregates (`AttributionAnalysis`, `AttributionSnapshot`) and value objects.
- Design real-time and asynchronous calculation and recalculation sequence loops.
- Challenge and resolve aggregate inflation, replay determinism over 5-year periods, and high-throughput write scalability (100M+ evaluations/day).
- Author Architectural Decision Records: `ADR-037` (Attribution boundaries and ownership) and `ADR-038` (Causal attribution and contribution model).

## 3. Architecture Alignment
The Attribution Engine completes the feedback phase of Karsa's Virtual Investment Firm (VIF) loop:
**Research → Thesis → Decision → Outcome → Performance → Attribution → Review → Governance → Learning**.

Attribution works closely with Capital Allocation (routing alpha/risk contributions to adjust capital limits) and Performance (consuming scorecards to establish causal drivers of success/failure).

## 4. Bounded Context Deliverables
- **Attribution Registry**: Tracks analysis runs, causal factors, and contribution scorecards.
- **Attribution Calculator**: Evaluates factor weights and computes contribution vectors.
- **Attribution Snapshot Store**: Saves immutable historical attribution records for auditability.

## 5. Work Packages (Design-Only)
- **WP-27.1**: Domain modeling of Attribution aggregates, value objects, and dimensions.
- **WP-27.2**: Sequence diagrams mapping Attribution Calculation, Recalculation, and Replay flows.
- **WP-27.3**: Authoring ADR-037 and ADR-038.
- **WP-27.4**: System integration interfaces, failure handling, and high-throughput scalability design.
