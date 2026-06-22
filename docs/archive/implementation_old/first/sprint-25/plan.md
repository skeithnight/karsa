# Sprint-25 Review Engine Foundation Plan

## 1. Context & Scope
This sprint is designated as **ARCHITECTURE DESIGN ONLY**.
In accordance with the repository constraints:
- No production code, database migrations, or test code will be generated or executed.
- The sole objective is to design the architectural foundations for the **Review Engine Foundation**.
- The architecture package will stop at the `ARCHITECTURE_FREEZE` transition.

The Review Engine is the authoritative subsystem responsible for qualitative evaluation, post-mortem audits, learning feedback generation, and feedback loop routing. It consumes performance scores, attribution costs, governance logs, and observability traces, and outputs reviews and learning feedback without directly mutating execution records or thesis assets.

## 2. Objectives
- Define context boundaries between Review, Performance, Thesis, Attribution, and Governance contexts.
- Establish the domain model for Review management, defining `ReviewSession` and `LearningFeedback` as aggregate roots.
- Design value objects: `ReviewTarget`, `ReviewFinding`, `ReviewEvidence`, and `ReviewVerdict`.
- Design integration contracts to safely consume `DecisionEvaluation`, `EvaluationSnapshot`, `ThesisVersion`, and `ExecutionOutcome` records.
- Challenge and resolve lifecycle, replayability, evidence storage, and scalability boundary issues.
- Author Architectural Decision Records (ADRs) to lock the design.

## 3. Architecture Alignment
The Review Engine sits at the final stage of Karsa's Virtual Investment Firm learning loop:
Research → Thesis → Decision → Outcome → Evaluation → **Review** → **Learning**.

Canonical architectural documentation will be stored in:
- [15-review-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/15-review-engine.md)

Related ADRs:
- [ADR-033: Review Engine Context Boundaries and Ownership](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-033-review-engine-ownership.md)
- [ADR-034: Qualitative Review Session and Learning Feedback Model](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-034-qualitative-review-and-learning-feedback-model.md)

## 4. Bounded Context Deliverables
- **Review Session Management**: Orchestrates post-mortem review runs, records qualitative findings and verdicts.
- **Learning Feedback Registry**: Holds suggested modifications (e.g. invalidations, limit updates) and routes them asynchronously to other engines.

## 5. Work Packages (Design-Only)
- **WP-25.1**: Domain modeling of `ReviewSession` and `LearningFeedback` aggregates.
- **WP-25.2**: Integration interface design mapping to Performance, Thesis, and Governance engines.
- **WP-25.3**: State transitions, lifecycles, and event contract definition.
- **WP-25.4**: Challenge matrix and ADR drafting.
