# Sprint-11.5 Final Implementation Planning Review

## 1. Executive Summary
This document concludes the Sprint-11.5 Architecture Revision cycle, establishing the final, locked implementation blueprint for the stabilization of the Virtual Investment Firm platform. Stripping away all scope creep related to Knowledge Graphs and universal registries, this plan aggressively hardens the mechanical plumbing of the system: UnitOfWork, Outbox, Optimistic Concurrency Control, and standard Event Envelopes. By formally isolating Governance lifecycles via async Sagas and cementing the exact schemas for `DecisionIdentity`, `OriginatorIdentity`, and the future `ExecutionOutcome`, Sprint-11.5 mathematically guarantees future compatibility with Attribution and Performance engines without expanding current business capabilities.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Justification |
|---------|-----------------|---------------|
| `PlatformEventEnvelope` | Shared Infrastructure | Used by all engines to normalize event buses. |
| `UnitOfWork` & `Outbox` | Shared Infrastructure | Mechanical persistence isolation. |
| `VersionedAggregate` | Shared Infrastructure | Standardizes OCC tracking globally. |
| `DecisionContextSnapshot` | Shared Domain Value Object | Transported in event payloads; not an aggregate. |
| `OriginatorIdentity` | Shared Domain Value Object | Performance tracking metadata on decisions. |
| Portfolio Rebalancing | WP-18 Portfolio Engine | Core engine functionality. |
| Artifact WORM Storage | WP-24.5 Institutional Memory | Re-scoped to strictly flat event archiving. |

## 3. Domain Model
- **`VersionedAggregate`**: Abstract class providing `aggregate_version: int` for OCC.
- **`Portfolio`**: Inherits `VersionedAggregate`. Exclusively mutates state locally.
- **`PortfolioDecision`**: A value object representing proposed Trade Intents. Contains `OriginatorIdentity` and `DecisionIdentity`.

## 4. Shared Infrastructure Design
- **OutboxRecord**: Table storing `envelope_id`, `payload (JSONB)`, `published_status`.
- **Dispatcher**: Python daemon polling `OutboxRecord` using Postgres `SELECT FOR UPDATE SKIP LOCKED` and publishing to Kafka/HTTP.
- **Why**: Decouples network I/O from database commits. 
- **Alternatives**: Dual-writes (rejected for data loss), Change Data Capture / Debezium (rejected for infrastructure complexity).

## 5. UnitOfWork Design
- **Contract**: `__enter__`, `__exit__`, `commit()`, `rollback()`.
- **Rule**: A UoW operates on exactly *one* Aggregate Root per block, plus *N* Outbox event insertions.
- **Why**: Prevents hidden cross-aggregate deadlocks and enforces strict DDD boundaries.
- **Tradeoffs**: Requires Sagas to orchestrate changes spanning multiple aggregates.

## 6. PlatformEventEnvelope Specification
- `event_id`, `event_type`
- `correlation_id`, `causation_id`
- `aggregate_type`, `aggregate_id`, `aggregate_version`
- `occurred_at`, `schema_version`, `payload`
- **Why**: Enforces causal tracing without relying on payload inspection.
- **Alternatives**: Custom schemas per engine (rejected for bus incompatibility).

## 7. OriginatorIdentity Specification
- `originator_id`, `originator_type`, `originator_version`
- **Ownership**: Shared Domain Value Object. Belongs in Decision/Thesis payloads, NOT at the `PlatformEventEnvelope` global envelope level.
- **Why**: Performance Engine must evaluate who/what generated the decision. Pushing it to the envelope breaks encapsulation of non-decision events (e.g., `PortfolioCreated`).

## 8. DecisionIdentity Specification
- `decision_id`: System-generated UUID.
- `decision_fingerprint`: SHA-256 hash of targets, constraints, and inputs.
- **Why**: Future engines (Attribution) must reconcile intents against executions. The fingerprint prevents tampering.
- **Alternatives**: Pure UUIDs (rejected; lack deterministic verification).

## 9. DecisionContextSnapshot Design
- **Type**: Shared Domain Value Object (JSON payload).
- **Behavior**: Emitted as an event payload. NOT synchronously persisted as an Aggregate.
- **Why**: Saves database I/O on WP-18. WP-24.5 natively stores the JSON.
- **Tradeoffs**: WP-18 cannot query past contexts natively; it relies entirely on the WORM store for audits.

## 10. Governance Integration Design
- **Workflow**: `DecisionProposedEvent` -> (Governance Review) -> `DecisionApprovedEvent` -> Portfolio executes target shift.
- **Why**: Prevents WP-18 from owning compliance logic or `WAITING` states.
- **Tradeoffs**: WP-18 must handle async updates gracefully via event listeners.

## 11. ExecutionOutcome Contract Definition
- `decision_id`, `intent_id`
- `execution_status`, `requested_quantity`, `filled_quantity`
- `requested_price`, `average_fill_price`, `fees`, `slippage`, `executed_at`, `broker_reference`
- **Why**: Defines the boundary for the future WP-14 Execution Engine. Attribution computes the delta between `Decision` and `ExecutionOutcome`.

## 12. Event Contracts
- `PortfolioDecisionProposed` (Contains DecisionPayload + ContextSnapshot + OriginatorIdentity)
- `PortfolioDecisionApproved` (Governance authorization)
- `PortfolioTargetUpdated` (Final state change applied)

## 13. Scalability Analysis
Moving network calls (Memory Platform HTTP/Kafka) to the Outbox Dispatcher removes blocking I/O from the UoW. Database throughput becomes the sole scaling constraint, horizontally solvable via sharding on `portfolio_id`.

## 14. Architecture Challenges
**Challenge**: Domain Leakage into Infrastructure.
**Resolution**: The `UnitOfWork` knows nothing about Portfolios or Decisions; it only knows about `Repository` and `Outbox` interfaces. 

**Challenge**: Infrastructure Leakage into Domain.
**Resolution**: `VersionedAggregate` acts as a pure integer counter in the domain. The Infrastructure Mapper converts this to `WHERE version = X`. No SQL leaks.

## 15. Architecture Delta Analysis
Against the Virtual Investment Firm target:
This stabilization sprint completely eliminates the "lost causation" risk. By forcing single-aggregate transactions and establishing strict `causation_id` propagation in the envelope, the resulting WORM storage inherently represents the exact mathematical DAG required by future Attribution and Capital Allocation engines.

## 16. Migration Strategy
1. Build `WP-Core` Shared Infra (UoW, OCC, Event Envelope).
2. Refactor WP-18 to emit `DecisionContextSnapshot` strictly via Outbox rather than direct repository saving.
3. Migrate WP-25 and WP-26 Application Services to UoW syntax (eliminating legacy DB commits).

## 17. Work Package Breakdown
- **WP-1**: Shared Transaction Foundations (UoW, Outbox, Dispatcher, OCC base classes).
- **WP-2**: Event Schemas (`PlatformEventEnvelope`, `ExecutionOutcomeContract`, `OriginatorIdentity`).
- **WP-3**: WP-18 Refactor (Migrate to UoW, Asynchronous Governance Saga).
- **WP-4**: WP-25/WP-26 UoW Backporting.

## 18. Acceptance Criteria
1. Application Services throw an error if multiple distinct aggregate roots are saved in one UoW block.
2. `PlatformEventEnvelope` strictly validates all 10 required fields.
3. WP-18 emits `DecisionContextSnapshot` payload exclusively via Outbox.
4. Concurrent updates to `Portfolio` trigger OCC retry loops without corrupting state.

## 19. Risks
- Backporting UoW to WP-25 and WP-26 introduces regression risk to frozen domains. (Mitigation: Extensive integration testing mimicking the previous synchronous repository behavior).
- The async Governance saga temporarily decouples Rebalancing from Execution, meaning UI components cannot synchronously display "Rebalance Complete". (Mitigation: Future UX must listen for WebSockets / polling).

## 20. Final Verdict
**READY_FOR_IMPLEMENTATION**

**Rationale**: The blueprint perfectly aligns with stabilization mandates. It rigorously enforces single-aggregate consistency, guarantees causality tracing, and defines the structural contracts required for future engines without prematurely building their domain logic. Scope boundaries are tight, safe, and ready for engineering execution.
