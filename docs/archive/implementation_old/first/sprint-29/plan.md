# Sprint-29 Post-Mortem Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **ARCHITECTURE DESIGN ONLY**.
In accordance with Karsa's workflow rules and repository constraints:
- No production code, database migrations, or test suites will be generated or executed.
- The sole objective is to establish the canonical architectural design for the **Post-Mortem Engine Foundation**.
- The deliverables consist of architecture blueprints, Architectural Decision Records (ADRs), and status tracking updates.

The Post-Mortem Engine is responsible for structured failure analysis, root-cause analysis, outcome classification, lesson capture, and organizational learning. It closed the loop by analyzing trades or operational runs that failed or deviated from expected performance bounds.

## 2. Objectives
- Define boundaries between the Post-Mortem Engine and the Research, Thesis, Performance, Review, Governance, Attribution, and Decision Journal contexts.
- Establish the domain model, detailing the single aggregate root (`PostMortemRecord`) and nested value objects, avoiding aggregate inflation.
- Design a formal Failure Taxonomy and Root Cause weight-contribution model.
- Define event-driven organizational learning loops to propagate lessons to other contexts asynchronously.
- Author Architectural Decision Records: `ADR-041` (Post-Mortem Engine boundaries and ownership) and `ADR-042` (Root cause and organizational learning model).

## 3. Target Architecture Alignment
The Post-Mortem Engine sits at the end of Karsa's Virtual Investment Firm (VIF) execution loop:
**Research → Thesis → Decision → Outcome → Performance → Attribution → Review → Governance → Post-Mortem (Closed Loop) → Learning**.

By analyzing why outcomes deviated from expectations and publishing structured lessons, it drives systemic improvements back to Research, Thesis, Governance, and Capital Allocation contexts.

## 4. Bounded Context Deliverables
- **Post-Mortem Registry**: Persists immutable post-mortem logs.
- **Learning Loop Publisher**: Asynchronously propagates captured lessons downstream.

## 5. Work Packages (Design-Only)
- **WP-29.1**: Domain modeling of Post-Mortem aggregates and failure taxonomy.
- **WP-29.2**: Sequence diagrams mapping failure detection, root-cause analysis, and lesson propagation.
- **WP-29.3**: Authoring ADR-041 and ADR-042.
- **WP-29.4**: System integration interfaces, failure handling, and high-throughput scalability design.
