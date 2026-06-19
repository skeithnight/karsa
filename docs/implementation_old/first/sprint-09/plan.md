# Sprint 09 Implementation Plan: WP-25 Thesis Engine

## 1. Executive Summary
The WP-25 Thesis Engine establishes the mathematical and logical lifecycle of an active investment thesis. It enforces the boundary between Research (discovery) and Portfolio (execution) by codifying hypotheses into immutable, reviewable, and degradable state machines. This sprint implements the physical codebase for WP-25 exactly according to the Phase 1 Architecture Freeze documented in ADR-010, leveraging the WP-24.5 Institutional Memory substrate constructed in Sprint-08.

## 2. Ownership Boundary Matrix
- **WP-25 Owns**: Thesis state transitions, invalidation rules, dependency tracking, review logging, telemetry evaluation.
- **WP-25 Does Not Own**: Portfolio construction, capital allocation, alpha discovery, attribution generation, execution sequencing.

## 3. Domain Model
The core aggregate roots and entities strictly conform to the frozen architecture:
- `ActiveThesis`: The root aggregate defining the ongoing lifecycle of an approved hypothesis.
- `ThesisVersion`: Immutable historical tracking of modifications via `SUPERSEDES` lineage.
- `ThesisReview`: Entity tracking periodic or trigger-based manual/algorithmic reviews.
- `ThesisDependencyGraph`: Entity tracking upstream assumptions (macro conditions, correlations).
- `ThesisDependencyEdge`: Directed links defining correlation logic and degradation impact.
- `ThesisInvalidationRule`: Threshold conditions that automatically trip invalidation.
- `ThesisMonitoringPolicy`: Telemetry bindings specifying evaluation frequency and sources.

## 4. Thesis Lifecycle
WP-25 enforces a rigid state machine dictating the health and validity of an `ActiveThesis`:
- **ACTIVE**: Nominal state; thesis assumptions hold true.
- **DEGRADED**: Minor invalidations or dependency fractures; requires review but no immediate liquidation.
- **UNDER_REVIEW**: A manual or algorithmic pause initiated via governance or trigger.
- **CONFIRMED**: Resumed nominal operation following a review.
- **INVALIDATED**: Terminal state; core logic breached, forcing WP-18 to unwind positions.
- **RETIRED**: Terminal state; thesis reached maturity or natural expiration.

## 5. Review Lifecycle
A `ThesisReview` encapsulates the transition from `DEGRADED` or periodic schedule to `UNDER_REVIEW`, concluding in either `CONFIRMED`, `INVALIDATED`, or `RETIRED`. Reviews must be persisted via the Institutional Memory Platform.

## 6. Invalidation Framework
The `ThesisInvalidationRule` subsystem continuously evaluates incoming telemetry against defined thresholds. A breached rule automatically triggers a `ThesisInvalidationRuleBreachedEvent` and forces the aggregate into `DEGRADED` or `INVALIDATED`.

## 7. Dependency Framework
The `ThesisDependencyGraph` tracks external dependencies. If an upstream thesis or macro-condition degrades, the `ThesisDependencyEdge` calculates propagation. A degraded dependency triggers a `ThesisDependencyDegradedEvent`.

## 8. Monitoring Framework
The `ThesisMonitoringPolicy` connects the Thesis Engine to external telemetry (price actions, alternative data signals) and controls the evaluation tick rate for Invalidation Rules.

## 9. Institutional Memory Integration
Every state transition, review, and instantiation is bundled as an `ArtifactPublishRequest` to WP-24.5 `Artifacts` API, storing the state snapshot and `DERIVED_FROM` lineage in the Postgres/Blob registry.

## 10. Event Contracts
Published Events:
- `ThesisActivatedEvent`
- `ThesisStateChangedEvent`
- `ThesisInvalidationRuleBreachedEvent`
- `ThesisDependencyDegradedEvent`
- `ThesisReviewCompletedEvent`

## 11. Persistence Design
- **Postgres Persistence**: A relational repository for the `ActiveThesis` state, `ThesisInvalidationRule`, and `ThesisDependencyGraph`.
- **Repository Abstraction**: `ThesisRepository` interface isolating infrastructure from domain logic.
- **Separation of Concerns**: Pure domain models without ORM bleed. Data mappers translate Domain to SQL.

## 12. Testing Strategy
- **Unit Tests**: Full coverage of the State Machine transitions and Invalidation Rule evaluations.
- **State Transition Tests**: Verify invalid transitions raise Domain exceptions.
- **Integration Tests**: Verify database roundtripping and WP-24.5 API artifact creation.
- **Event Mocks**: Verify the correct sequence of Domain Events are emitted on state change.

## 13. Work Package Breakdown
1. **Work Package 1**: Domain Models & State Machine (Aggregates, State logic, Events).
2. **Work Package 2**: Invalidation & Dependency Evaluation (Rules, Graphs, Monitoring).
3. **Work Package 3**: Repository & Postgres Integrations (Migrations, Mappers, `ThesisRepository`).
4. **Work Package 4**: WP-24.5 Integration & Core Service (Snapshot writing, Application Services).

## 14. Acceptance Criteria
1. The system correctly enforces the `ACTIVE -> DEGRADED -> UNDER_REVIEW -> CONFIRMED` state loop.
2. The system correctly enforces the `ACTIVE -> INVALIDATED` terminal transition.
3. Telemetry payloads failing an Invalidation Rule automatically change state and emit `ThesisInvalidationRuleBreachedEvent`.
4. Degraded dependencies propagate state changes through the `ThesisDependencyGraph`.
5. Every state change successfully persists a JSON snapshot via the WP-24.5 `ArtifactRegistry` API.
6. The implementation contains zero boundary leaks into WP-18 (Portfolio) or WP-26 (Allocation).

## 15. Risks
- **Network Resilience to WP-24.5**: If the API is unreachable, thesis transitions must implement compensating transactions, retries, or an Outbox pattern.
- **Complex Dependency Graphs**: Deep dependency chains could cause cascading invalidation loops if cycle detection is absent.

## 16. Final Verdict
This implementation plan strictly complies with the Phase 1 Architecture Freeze. No new domains or cross-boundary aggregations are proposed. The plan is verified ready for physical code execution.