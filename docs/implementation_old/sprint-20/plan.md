# Sprint-20 Governance Engine Foundation Plan

## 1. Context & Scope
Following the frozen architecture of Sprint-20, this sprint implements the **Governance Engine Foundation** as the central policy authority (PDP/PEP) for Karsa.
Objectives:
- Intercept capability executions, provider routing, cost checks, and administrative activities.
- Isolate policy decision logic (PDP) from active enforcement points (PEP).
- Implement a local budget cache snapshot model to avoid Attribution Engine downtime coupling.
- Implement a two-layer audit chain model to eliminate write locking contentions.
- Build emergency override abstractions and bypass logs. No real GenAI clients or database DDL changes are generated.

## 2. Objectives
- Domain Layer: Implement `PolicyDefinition`, `GovernanceDecision`, and `GovernanceAuditChain` aggregates, value objects, and mapping entities.
- Application Services: Implement `PolicyRegistryService` (manages policy FSM), `PolicyEvaluationService` (interceptor & PDP logic), and `GovernanceAuditService` (asynchronous Layer B audit chaining).
- Repositories: Implement `InMemory` and `File` persistence with OCC guards.
- Local Budget Cache: Build `GovernanceBudgetCache` with age staleness validation.
- Emergency Override: Build signed token check abstractions and append-only bypass logging.

## 3. Architecture Alignment
The implementation conforms to:
- [10-governance-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/10-governance-engine.md)
- [ADR-022: Governance Engine Ownership and Context Boundaries](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-022-governance-engine-ownership.md)
- [ADR-023: PDP-PEP Interception and Replay Bypass Architecture](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-023-pdp-pep-architecture.md)

## 4. Work Packages
- **WP-20.1**: Domain aggregates, entities, value objects, and FSM.
- **WP-20.2**: Registry, Evaluation, and Audit services.
- **WP-20.3**: Local Budget Cache and freshness check.
- **WP-20.4**: Emergency override bypass logs.
- **WP-20.5**: InMemory and File repositories with OCC checks.
- **WP-20.6**: Testing, audit, and remediation.
