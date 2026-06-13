# Sprint-12: Thesis Engine Foundation Architecture v2

## 1. Executive Summary
This document presents the revised Sprint-12 architecture for the Thesis Engine Foundation, incorporating resolutions for the 10 findings from the Architecture Revision v1 phase. It solidifies the `Thesis` as a fully-structured, future-ready Domain Aggregate capable of capturing deep semantic meaning—bull/bear cases, invalidation criteria, and calibrated confidence—without prematurely implementing the execution or evaluation engines. The architecture strictly adheres to the Sprint-11.5 stabilization framework (Single Aggregate UoW, OCC, Outbox Pattern) while ensuring total compatibility with the target Virtual Investment Firm roadmap.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `Thesis` Aggregate | WP-12 Thesis Engine | Core aggregate managing hypothesis lifecycle. |
| `ThesisContextSnapshot` | `karsa.shared.domain` | Immutable shared VO for replay-grade payload transport. |
| `OriginatorIdentity` | `karsa.shared.domain` | Expanded VO tracking author/model granularity. |
| `ThesisReviewRecord` | WP-12 Thesis Engine | Immutable VO recording governance/periodic reviews. |
| `PlatformEventEnvelope` | `karsa.shared.events` | System-wide event envelope. |

## 3. Architecture Overview
The Thesis Engine acts as the definitive system of record for structured investment hypotheses. It relies purely on the async Governance Saga for authorization (adding a `REJECTED` state to handle failures) and explicitly formalizes its inputs via `ResearchReference` DAGs. It publishes lifecycle events (`ThesisProposedEvent`, `ThesisActivatedEvent`, `ThesisInvalidatedEvent`) for downstream consumers like the Portfolio and future Allocation Engines to react.

## 4. Domain Model
- **`Thesis` (Aggregate Root)**: Inherits from `VersionedAggregate`. Mutable entity orchestrating state transitions.
- **`ThesisState`**: `DRAFT`, `PROPOSED`, `ACTIVE`, `REJECTED`, `INVALIDATED`, `REALIZED`, `EXPIRED`.
- **`HypothesisStructure` (Value Object)**: Contains `hypothesis_statement`, `bull_case`, `bear_case`, `assumptions`, `expected_outcome`, `invalidation_criteria`, `success_criteria`.

## 5. Aggregate Design
The `Thesis` aggregate enforces single-aggregate transactional limits. All confidence updates, state transitions, or metadata additions increment the `aggregate_version`. The thesis owns its nested value objects (`HypothesisStructure`, `ConfidenceModel`, `ResearchReference` lists) and validates invariants before saving.

## 6. Value Objects
- **`ThesisIdentity`**: `thesis_id` (UUID).
- **`TimeHorizon`**: Adds `classification` (`SHORT_TERM`, `MID_TERM`, `LONG_TERM`) alongside explicit dates.
- **`ConfidenceModel`**: Contains `raw_confidence: float` and `calibrated_confidence: float` for future algorithmic weighting.
- **`ResearchReference`**: `research_id`, `research_version`, `research_type`.
- **`ThesisReviewRecord`**: `review_reason`, `review_type`, `reviewer_id`, `reviewed_at`.
- **`OriginatorIdentity`**: Expanded to include `originator_id`, `originator_type`, `originator_version`, `originator_strategy`, `originator_worker_id`, `originator_model`.

## 7. Event Contracts
All events map directly into `PlatformEventEnvelope.payload`.
- `ThesisProposedEvent` (Includes full `ThesisContextSnapshot`)
- `ThesisActivatedEvent`
- `ThesisRejectedEvent` (Added per Finding #5)
- `ThesisConfidenceUpdatedEvent`
- `ThesisInvalidatedEvent`
- `ThesisRealizedEvent`

## 8. Application Services
- `propose_thesis(cmd)`
- `update_confidence(cmd)`
- `apply_governance_decision(cmd)` -> Transitions to `ACTIVE` or `REJECTED`.
- `invalidate_thesis(cmd)` -> Transitions to `INVALIDATED`.
All persist changes inside `with self.uow:`.

## 9. Repositories
`ThesisRepository` persists the `Thesis` aggregate. The repository respects `aggregate_version` for OCC, rejecting stale writes with `ConcurrencyConflictError`.

## 10. Persistence Design
The Postgres mapper flattens nested value objects (`HypothesisStructure`, `ConfidenceModel`) into strict JSONB columns attached to the `thesis` row to guarantee single-table atomicity and avoid cross-table locking deadlocks within the UoW.

## 11. Integration Design
Governance decoupling relies solely on the `ThesisProposedEvent`. The Governance Engine emits a `DecisionApprovedEvent` or `DecisionRejectedEvent` correlated by `causation_id`, which the Thesis Engine consumes to transition to `ACTIVE` or `REJECTED`.

## 12. Sequence Diagrams
*(Saga Flow)*
1. AppService: `Thesis` -> `PROPOSED`. Save Outbox `ThesisProposedEvent`. Commit.
2. Governance Engine: Consume -> Review -> Publish `DecisionRejectedEvent`.
3. AppService: `apply_governance_decision()` -> `Thesis` -> `REJECTED`. Save Outbox `ThesisRejectedEvent`. Commit.

## 13. State Diagrams
`DRAFT` -> `PROPOSED` -> `ACTIVE` | `REJECTED`
`ACTIVE` -> `INVALIDATED` | `REALIZED` | `EXPIRED`

## 14. Failure Handling
Uses OCC to detect simultaneous edits (e.g., automated confidence update racing against a human review). The transaction rolls back, and `ConcurrencyConflictError` directs the caller to re-evaluate the latest thesis state.

## 15. OCC Strategy
Inherited via `VersionedAggregate`. The UoW executes `UPDATE thesis SET ... WHERE id = X AND version = Y`. If 0 rows updated, it throws `ConcurrencyConflictError`.

## 16. Scalability Analysis
Flat JSONB persistence for deep Value Objects prevents JOIN overhead. Outbox Dispatcher guarantees that Kafka/HTTP I/O never blocks the Postgres pool.

## 17. Security Analysis
Expanded `OriginatorIdentity` provides strict non-repudiation down to the exact worker ID and model hash, ensuring malicious AI workers or compromised human accounts can be audited precisely.

## 18. Migration Strategy
Net-new context. Zero data migration required.

## 19. Risks
- Deep JSONB nesting makes structured SQL querying difficult. Mitigation: The future Review Engine will ingest `PlatformEventEnvelope` feeds into an analytical datastore; operational queries remain simple point-reads.

## 20. ADR Decisions
- **ADR-12.3**: Adopt AI+Human co-authorship by allowing multiple `OriginatorIdentity` entries per Thesis. (Addresses Finding #7).
- **ADR-12.4**: Implement `calibrated_confidence` as an optional float. (Addresses Finding #4).

## 21. Architecture Challenges
The `REJECTED` state required formalizing a return trip from the Governance Engine. We resolved this by standardizing `DecisionRejectedEvent` just as we standardized `DecisionApprovedEvent` in Sprint-11.5.

## 22. Architecture Delta Analysis
Compared to Revision v1, the Domain Model is significantly richer. It natively understands *why* a thesis exists (`bull_case`, `invalidation_criteria`) rather than just holding arbitrary metadata. This completely unblocks the future Attribution Engine.

## 23. Acceptance Criteria
- `Thesis` aggregate captures `HypothesisStructure` natively.
- `ThesisState` includes `REJECTED`.
- `ResearchReference` tracks specific versions of upstream research.
- Full compatibility with the frozen Sprint-11.5 `UnitOfWork` and `Outbox`.

## 24. Final Verdict
**READY_FOR_FINAL_FREEZE_REVIEW**

---

## Architecture Review Findings Resolution

### Finding #1: Missing Hypothesis Structure
**Decision**: Adopted. Implemented as `HypothesisStructure` Value Object.
**Rationale**: Required for future Attribution and Review engines to structurally validate outcomes.
**Tradeoffs**: Increases payload size.
**Rejected**: Storing structure as generic JSON `metadata`. (Rejected due to lack of type safety and schema validation).

### Finding #2: Snapshot Ambiguity
**Decision**: Clarified. 
- `Thesis` (Mutable Aggregate).
- `ThesisSnapshot` (Removed concept, redundant).
- `ThesisContextSnapshot` (Immutable VO, lives in event payloads for replayability).
**Rationale**: Eliminates overlapping vocabulary.

### Finding #3: Originator Identity Insufficient
**Decision**: Expanded to include `originator_strategy`, `originator_worker_id`, `originator_model`.
**Rationale**: Performance Engine must differentiate between distinct AI agents utilizing the same overarching strategy.
**Tradeoffs**: Requires shared domain refactoring.
**Rejected**: Creating separate `AIIdentity` and `HumanIdentity`. (Rejected to maintain polymorphic compatibility).

### Finding #4: Confidence Model
**Decision**: Adopted `ConfidenceModel(raw_confidence, calibrated_confidence)`.
**Rationale**: Future performance engines will adjust raw confidence based on historical accuracy. The domain must support this structure now.
**Tradeoffs**: `calibrated_confidence` will remain `null` during this sprint.

### Finding #5: Missing REJECTED State
**Decision**: Added `REJECTED` to `ThesisState`.
**Rationale**: Fixes lifecycle gap when Governance denies a proposal.
**Tradeoffs**: Requires handling terminal states early in the lifecycle.

### Finding #6: Weak Research Lineage
**Decision**: Adopted `ResearchReference(research_id, research_version, research_type)`.
**Rationale**: A string list lacks version determinism.
**Rejected**: Universal Artifact Graph linkages. (Rejected to preserve stabilization constraints).

### Finding #7: Ownership Model
**Decision**: Support multiple owners (AI + Human co-authorship).
**Rationale**: Research flows often involve an AI generating a baseline and a Human refining it. Performance attribution requires tracking both.
**Rejected**: Single owner limitation.

### Finding #8: Missing Thesis Review Record
**Decision**: Adopted `ThesisReviewRecord` Value Object.
**Rationale**: Captures periodic governance reaffirmations without requiring state transitions.
**Rejected**: Implementing a separate `Review` Aggregate. (Deferred to future Review Engine).

### Finding #9: Time Horizon Classification
**Decision**: Adopted explicit enum: `SHORT_TERM`, `MID_TERM`, `LONG_TERM`.
**Rationale**: Allows coarse-grained querying and portfolio alignment prior to exact date calculation.
**Rejected**: Relying strictly on datetimes.

### Finding #10: Allocation Compatibility
**Decision**: Adopted `allocation_constraints` and `risk_budget_reference` inside `Thesis`.
**Rationale**: The Allocation Engine must eventually map a thesis to portfolio limits.
**Rejected**: Implementing Allocation logic now.

---

### Sprint Scope Alignment
**Changes from Revision v1**: Domain depth drastically increased via rich Value Objects (`HypothesisStructure`, `ConfidenceModel`, `ResearchReference`).
**Deferred to Future Sprints**: Calibration logic, Attribution calculation, Allocation translation, Graph linkages.
**Becomes Architecture-Frozen**: The `Thesis` aggregate shape, lifecycle (`REJECTED` inclusion), and Value Object schemas.