# Sprint-30 Capital Allocation Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **ARCHITECTURE DESIGN ONLY**.
In accordance with Karsa's workflow rules and repository constraints:
- No production code, database migrations, or test suites will be generated or executed.
- The sole objective is to establish the canonical architectural design for the **Capital Allocation Engine Foundation**.
- The deliverables consist of architecture blueprints, Architectural Decision Records (ADRs), and status tracking updates.

The Capital Allocation Engine is responsible for allocating virtual capital across workers, strategies, theses, and future portfolios using objective historical evidence. It acts as the coordinator of system funding, balancing exploration and exploitation to maximize firm-wide alpha.

## 2. Objectives
- Define boundaries and Single Writer rules between the Capital Allocation Engine and the Research, Thesis, Performance, Review, Governance, Attribution, Decision Journal, Post-Mortem, and future CIO Agent contexts.
- Design the domain model, utilizing `AllocationPolicy` as the sole mutable aggregate root and `AllocationRecord` as the write-once ledger entry.
- Implement strategies to prevent survivorship bias and capital concentration (exploration floor, probation funding, diversification rules).
- Author Architectural Decision Records: `ADR-043` (Capital Allocation Engine ownership and boundaries) and `ADR-044` (Capital allocation and evidence weighting model).

## 3. Target Architecture Alignment
The Capital Allocation Engine sits at the optimization phase of Karsa's Virtual Investment Firm (VIF) loop:
**Research → Thesis → Decision → Outcome → Performance → Attribution → Review → Governance → Post-Mortem → Capital Allocation (Optimization) → Learning**.

By dynamically reallocating capital based on quantitative performance, attribution weights, and governance constraints, it optimizes the portfolio weights without executing trades directly.

## 4. Bounded Context Deliverables
- **Allocation Registry**: Persists immutable allocation calculation records and target recommendations.
- **Allocation Policy Store**: Manages policy limits and exploration parameters.

## 5. Work Packages (Design-Only)
- **WP-30.1**: Domain modeling of Capital Allocation ledger and policy aggregates.
- **WP-30.2**: Sequence diagrams mapping evidence collection, calibration, and allocation adjustment recommendations.
- **WP-30.3**: Authoring ADR-043 and ADR-044.
- **WP-30.4**: Integration contracts for Governance, Performance, Attribution, and the future CIO Agent.
