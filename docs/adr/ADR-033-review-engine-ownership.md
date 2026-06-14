# ADR-033: Review Engine Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires a formal, systematic post-mortem review and qualitative learning mechanism to complete its Virtual Investment Firm learning loop (Research → Thesis → Decision → Outcome → Evaluation → Review → Learning). Historically, qualitative review remarks, human feedback, post-mortem audits, and learning adjustments were entered manually or mixed directly with quantitative performance scorecards or thesis documents.

This mixture creates architectural problems:
1. **Contention & Locking**: Modifying a thesis or performance record to attach a review comment risks locking active trading operations or violating the Single Writer principle.
2. **Qualitative/Quantitative Pollution**: Separating hard mathematical performance scores (Brier, Sharpe) from subjective post-mortems (e.g. LLM reasoning failures, data provider drift) is required to ensure clean model calibration.
3. **Decoupled Asynchronous Learning**: Learning feedback (e.g. a recommendation to deprecate a thesis) must be processed asynchronously, allowing thesis or portfolio managers to apply updates without coupling review execution to real-time risk workflows.

We need a dedicated **Review Engine Bounded Context** with strict context boundaries.

## Decision
We enforce the following bounded context boundaries:

1. **Review Engine Ownership**:
   - The **Review Engine** is the sole writer and authority of:
     - `ReviewSession` (Aggregate Root): Orchestrates the lifecycle of a post-mortem audit of a target.
     - `LearningFeedback` (Aggregate Root): Actionable lessons/modifications proposed by the review loop.
     - `ReviewFinding` (Value Object): Specific qualitative issues identified.
     - `ReviewVerdict` (Value Object): The final outcome judgment of a review session.
   - The Review Engine **does not** compute numerical performance metrics, calculate attribution costs, modify thesis version state directly, or execute risk blocks.
2. **Context Separation Boundaries**:
   - **Performance Engine Separation**: Performance Engine writes `DecisionEvaluation` and `EvaluationSnapshot` records in `db_performance`. Review Engine reads these scorecards for analysis but never modifies them.
   - **Thesis Engine Separation**: Thesis Engine owns `ThesisVersion` models in `db_thesis`. The Review Engine recommends modifications via `LearningFeedback` aggregates in `db_review`, which are consumed and applied by the Thesis Engine asynchronously.
   - **Governance Engine Separation**: Governance owns active PDP/PEP policies. Governance triggers review alerts when policies are breached, but Governance does not write review verdicts.
   - **Attribution Engine Separation**: Attribution owns execution costs. Review Engine reads attribution references to evaluate capital efficiency, but never mutates cost ledgers.
   - **Observability Platform Separation**: Observability tracks spans and traces. Review Engine references `trace_id` values to attach trace graphs as evidence.

## Consequences
- **Loose Coupling**: Downsides and reasoning errors can be audited offline without blocking trading execution or locking thesis databases.
- **Auditable Learning Loop**: Every change to a thesis version or allocation ceiling can be traced directly back to a parent `feedback_id` and `session_id`, closing the learning loop.
- **Zero Cross-Locking**: Inter-context actions are communicated via lightweight asynchronous integration events, guaranteeing lock-free operations.
