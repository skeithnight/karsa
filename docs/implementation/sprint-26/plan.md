# Sprint-26 Governance Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **ARCHITECTURE DESIGN ONLY**.
In accordance with Karsa's workflow rules and repository constraints:
- No production code, database migrations, or test suites will be generated or executed.
- The sole objective is to establish the canonical architectural design for the **Governance Engine Foundation**.
- The deliverables consist of architecture blueprints, Architectural Decision Records (ADRs), and status tracking updates.

The Governance Engine is the authoritative context responsible for policy definitions, policy evaluations, real-time risk controls, exceptions workflow management, and human override auditing. It evaluates VIF operations against defined compliance limits and enforces risk containment policies.

## 2. Objectives
- Define boundaries between the Governance Engine and the Thesis, Performance, Review, and Capital Allocation contexts.
- Establish the domain model for the Governance Engine, detailing aggregates (`GovernancePolicy`, `PolicyDecision`, `PolicyViolation`, `ExceptionRequest`) and value objects.
- Design real-time and asynchronous policy evaluation sequence loops.
- Challenge and resolve enforcement authority, human-in-the-loop approvals, replayability, policy versioning, and exception workflows.
- Author Architectural Decision Records: `ADR-035` (Governance boundaries) and `ADR-036` (Policy evaluation and enforcement model).

## 3. Architecture Alignment
The Governance Engine completes the active runtime guard rail of Karsa's Virtual Investment Firm (VIF) loop:
**Research → Thesis → Decision → Outcome → Performance → Review → Governance → Learning**.

Governance differs from Review in that it operates in near-real-time to enforce immediate operations halts (e.g. stopping workers or thesis version capital access), whereas Review conducts retrospective, qualitative audits offline.

## 4. Bounded Context Deliverables
- **Policy Registry**: Defines compliance conditions, target limits, and enforcement actions.
- **Evaluation Engine**: Near-real-time execution validator that logs violations and updates policy decisions.
- **Exception Registry**: Orchestrates approval sign-offs and active override timeframes.

## 5. Work Packages (Design-Only)
- **WP-26.1**: Domain modeling of Governance aggregates and value objects.
- **WP-26.2**: Sequence diagrams mapping Policy Evaluation, Violation Detection, and Exception Approval flows.
- **WP-26.3**: Authoring ADR-035 and ADR-036.
- **WP-26.4**: System integration interfaces, failure handling, and scalability design for 100M+ evaluations.
