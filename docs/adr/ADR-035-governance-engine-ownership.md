# ADR-035: Governance Engine Context Boundaries and Ownership

## Status
Approved

## Date
2026-06-14

## Context
Karsa requires a formal, centralized, and audited compliance evaluation and risk management subsystem to complete the Virtual Investment Firm (VIF) lifecycle:
**Research → Thesis → Decision → Outcome → Performance → Review → Governance → Learning**.

Historically, compliance limits (e.g., maximum daily worker spend, maximum portfolio drawdowns) were hardcoded in separate scripts or evaluated inline within execution planners. This mixture introduces significant architectural liabilities:
1. **Tight Coupling and Lock Contention**: Direct database updates (such as a risk script locking a thesis version table to halt it) violate the Single Writer rule and block runtime operations.
2. **Lack of Human-in-the-Loop Audits**: Overrides and exceptions were undocumented or un-auditable, presenting security risks and making retrospective compliance tracing impossible.
3. **Quantitative Pollution**: Mixing policy evaluation (compliance thresholds) with mathematical evaluations (Sharp ratio scores in the Performance Engine) pollutes clean bounded contexts.

We need a dedicated **Governance Engine Bounded Context** with strict boundaries and ownership rules.

## Decision
We enforce the following bounded context boundaries and design decisions:

1. **Governance Engine Ownership**:
   - The **Governance Engine** is the sole writer and authoritative subsystem for:
     - `GovernancePolicy` (Aggregate Root): Defines active compliance conditions and actions.
     - `PolicyDecision` (Aggregate Root): Stores compliance status per target and version.
     - `PolicyViolation` (Aggregate Root): Logs breach occurrences and resolution tracking.
     - `ExceptionRequest` (Aggregate Root): Orchestrates override workflow requests, signature collections, and validations.
   - The Governance Engine **does not** manage live execution states directly, modify active thesis parameters, or control trade routing.

2. **Decoupled Asynchronous Enforcement**:
   - **Thesis Engine Separation**: Thesis Engine owns `ThesisVersion` models. Governance evaluates compliance and emits `PolicyViolationDetectedEvent`. Thesis Engine listens to the event bus and suspends the version.
   - **Execution / Worker Separation**: Worker status is owned by the Execution or Provider Registry. Governance publishes worker suspension events, which the Execution context consumes to stop routing queries.
   - **Review Engine Separation**: Review Engine conducts qualitative post-mortems and proposes learning feedback. Governance reads review verdicts asynchronously to evaluate policy compliance (e.g. checking if a target has reached its critical verdict limit).
   - **Performance Engine Separation**: Performance Engine calculates numerical evaluations. Governance consumes performance scorecard events (`DecisionEvaluatedEvent`) to validate compliance.
   - **Capital Allocation Separation**: Capital allocation limits are evaluated by Governance, and limit reductions are executed by the Capital Allocation Engine asynchronously.

3. **Exception Verification**:
   - Exception requests require cryptographic signature collections from authorized user roles (e.g., `RISK_OFFICER`). Once validated, active overrides temporarily disable specific policy conditions.

## Consequences
- **Decoupled lock-free operations**: Downstream contexts process compliance violations asynchronously without database cross-locking.
- **Traceable Override Auditing**: Every human override and exception is permanently recorded and cryptographically signed, preventing unauthorized privilege escalation.
- **Single Source of Compliance**: All VIF policies are declared in one location, allowing simple audits.
