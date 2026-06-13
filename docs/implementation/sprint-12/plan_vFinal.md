# Sprint-12: Thesis Engine Foundation Architecture - Final Freeze Revision

## 1. Executive Summary
This document finalizes the Sprint-12 architecture for the Thesis Engine Foundation, addressing the final freeze-review findings regarding co-authorship models, confidence ownership, and review record persistence strategies. By explicitly separating the primary `OriginatorIdentity` from supplementary `ThesisContributor` lists, enriching the `ConfidenceModel` with explicit source ownership, and ensuring `ThesisReviewRecord` remains strictly out-of-aggregate to control aggregate bloat, this revision closes all remaining ambiguity. The architecture strictly adheres to the frozen Sprint-11.5 stabilization baseline and is now fully compatible with the downstream demands of Attribution, Performance, Governance, and Allocation engines.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `Thesis` Aggregate | WP-12 Thesis Engine | Core aggregate managing hypothesis lifecycle. |
| `ThesisContextSnapshot` | `karsa.shared.domain` | Immutable shared VO for replay-grade payload transport. |
| `OriginatorIdentity` | `karsa.shared.domain` | Explicit creator of the thesis. |
| `ThesisContributor` | WP-12 Thesis Engine | VO array detailing secondary contributors. |
| `ThesisReviewRecord` | `karsa.shared.events` | Event payload VO. Not stored in `Thesis` aggregate. |

## 3. Architecture Overview
The Thesis Engine provides the semantic core of the investment firm by maintaining the `Thesis` Aggregate. It uses the `UnitOfWork` and `Outbox` pattern to decouple entirely from downstream consumer processes. Lifecycle progression (Draft -> Proposed -> Active -> Invalidated/Realized) relies purely on Domain Events and Governance Saga orchestration. 

## 4. Domain Model
- **`Thesis` (Aggregate Root)**: Inherits from `VersionedAggregate`. Mutable entity orchestrating state.
- **`ThesisState`**: `DRAFT`, `PROPOSED`, `ACTIVE`, `REJECTED`, `INVALIDATED`, `REALIZED`, `EXPIRED`.
- **`HypothesisStructure`**: `hypothesis_statement`, `bull_case`, `bear_case`, `assumptions`, `expected_outcome`, `invalidation_criteria`, `success_criteria`.

## 5. Aggregate Design
The `Thesis` maintains single-aggregate transactional limits. It encapsulates the `HypothesisStructure`, `ConfidenceModel`, `ResearchReference` arrays, and `ThesisContributor` lists. It does *not* accumulate `ThesisReviewRecord` items in memory to prevent aggregate bloating.

## 6. Value Objects
- **`ThesisIdentity`**: `thesis_id` (UUID).
- **`TimeHorizon`**: Adds `classification` (`SHORT_TERM`, `MID_TERM`, `LONG_TERM`) and explicit dates.
- **`ResearchReference`**: `research_id`, `research_version`, `research_type`.
- **`OriginatorIdentity`**: `originator_id`, `originator_type`, `originator_version`, `originator_worker_id`, `originator_model`, `originator_strategy`. (Creator of thesis).
- **`ThesisContributor`**: `contributor_id`, `contributor_type`, `contribution_role` (`AUTHOR`, `REVIEWER`, `APPROVER`, `REFINER`).
- **`ConfidenceModel`**: `raw_confidence`, `calibrated_confidence`, `confidence_source` (`MANUAL`, `MODEL`, `CALIBRATION`, `GOVERNANCE`), `confidence_updated_at`.
- **`ThesisReviewRecord`**: `review_reason`, `review_type`, `reviewer_id`, `reviewed_at`. (Stored in events only).

## 7. Event Contracts
- `ThesisProposedEvent` 
- `ThesisActivatedEvent`
- `ThesisRejectedEvent`
- `ThesisConfidenceUpdatedEvent`
- `ThesisInvalidatedEvent`
- `ThesisRealizedEvent`
- `ThesisReviewedEvent` (New: Transports `ThesisReviewRecord` independent of aggregate state).

## 8. Application Services
- `propose_thesis(cmd)`
- `add_contributor(cmd)`
- `update_confidence(cmd)`
- `apply_governance_decision(cmd)`
- `invalidate_thesis(cmd)`
- `record_review(cmd)` (Saves `ThesisReviewedEvent` outbox without mutating `Thesis` state).

## 9. Repositories
`ThesisRepository` persists the `Thesis` aggregate natively supporting OCC validation via `VersionedAggregate`.

## 10. Persistence Design
The Postgres mapper converts complex VOs (`HypothesisStructure`, `ConfidenceModel`, lists of `ResearchReference` and `ThesisContributor`) into a flat `JSONB` column on the `thesis` row, preserving atomicity within the UoW boundary.

## 11. Integration Design
Governance interacts with the Thesis Engine primarily via `ThesisProposedEvent` and replies with `DecisionApprovedEvent`/`DecisionRejectedEvent` correlated by `causation_id`. The Allocation/Portfolio engines consume `ThesisActivatedEvent`.

## 12. Sequence Diagrams
*(Saga Flow for Review)*
1. AppService: `record_review()` -> Opens UoW. Saves `Outbox(ThesisReviewedEvent)`. No aggregate mutation. Commits UoW.
2. Institutional Memory: Consumes `ThesisReviewedEvent` -> Persists for historical replay.

## 13. State Diagrams
`DRAFT` -> `PROPOSED` -> `ACTIVE` | `REJECTED`
`ACTIVE` -> `INVALIDATED` | `REALIZED` | `EXPIRED`

## 14. Failure Handling
Standard `ConcurrencyConflictError` on stale `aggregate_version`. All retries occur out-of-band at the application port boundary.

## 15. OCC Strategy
Inherited via `VersionedAggregate`. Update queries strictly append `WHERE id = X AND version = Y`.

## 16. Scalability Analysis
`ThesisReviewRecord` storage is offloaded to the event stream, guaranteeing the `Thesis` aggregate memory footprint never scales linearly with the number of periodic reviews.

## 17. Security Analysis
Expanded `OriginatorIdentity` combined with explicit `ThesisContributor` lists ensure absolute non-repudiation of all parties involved in hypothesis formulation.

## 18. Migration Strategy
Net-new context. Zero data migration required.

## 19. Risks
- Application-layer replay parsing logic required to reconstruct full review history.
- Mitigation: This logic fits naturally into the future Review Engine, abstracting complexity away from the Thesis Domain.

## 20. ADR Decisions
- **ADR-12.2 (Corrected)**: Research lineage is represented strictly through discrete `ResearchReference(research_id, research_version, research_type)` VO lists instead of graph edges. *Rationale*: Maintains the explicit "No Graph Database" stabilization constraint while providing absolute determinism.
- **ADR-12.5**: `ThesisReviewRecord` is decoupled from aggregate state. *Rationale*: Protects `Thesis` from infinite memory growth due to recurring heartbeat-style governance reviews.

## 21. Architecture Challenges
**Challenge**: How to attribute performance to multiple AI agents collaborating on a single thesis?
**Resolution**: Differentiate `OriginatorIdentity` (the primary instigator/strategy) from `ThesisContributor` (the array of specific agents who acted as `REFINER` or `REVIEWER`). Performance engines will query this exact JSON block to assign fractional rewards.

## 22. Architecture Delta Analysis
Compared to Revision v1, the model formally handles co-authorship via `ThesisContributor`, assigns strict source-ownership to confidence fluctuations (`confidence_source`), and significantly optimizes database footprint by moving periodic reviews to the event payload tier.

## 23. Acceptance Criteria
- Co-authorship modeled via `OriginatorIdentity` + `ThesisContributor[]`.
- `ConfidenceModel` explicitly captures ownership and timing metrics.
- `ThesisReviewRecord` resides only within event payloads.
- OCC, Outbox, and Single Aggregate constraints perfectly preserved.

## 24. Final Verdict
**READY_FOR_FREEZE**

---

## Freeze Readiness Verification

### 1. Finding Resolution Check
- **Finding A (Co-Author Model)**: Resolved via `OriginatorIdentity` vs `ThesisContributor` distinction.
- **Finding B (Confidence Ownership)**: Resolved via `confidence_source` and `confidence_updated_at`.
- **Finding C (Review Record Storage)**: Resolved by defining `ThesisReviewRecord` as event-payload only.
- **Finding D (ADR-12.2 Correction)**: Resolved. Replaced with `ResearchReference` DAG representation without graph semantics.

### 2. Compatibility Check
- **Attribution & Performance Compatibility**: PASS. The precise separation of `OriginatorIdentity` and `ThesisContributor` roles combined with `calibrated_confidence` unblocks fractional scoring and historical attribution.
- **Governance Compatibility**: PASS. The addition of the `REJECTED` state and the lightweight `ThesisReviewedEvent` perfectly support Governance sagas.
- **OCC Compatibility**: PASS. OCC preserved natively.
- **Replayability Compatibility**: PASS. History reconstruction explicitly supported via event-payload retention of `ThesisReviewRecord`.
- **Future Allocation Engine Compatibility**: PASS. Contains necessary targets and constraints for mapping logic.

### 3. Architecture Blocker Check
- No remaining architecture blockers.
- No unresolved ownership ambiguity.
- No unresolved lifecycle ambiguity.
- No unresolved replayability ambiguity.

**ARCHITECTURE_FROZEN**
