# Sprint-14 Attribution Engine Foundation - Architecture Revision v2

## 1. Executive Summary
The Sprint-14 Attribution Engine Architecture Revision v2 solidifies the foundation for determining investment value distribution by eliminating synchronous runtime dependencies, formalizing role-based contribution weights, and enforcing strict governance around restatements. The architecture fully isolates the Attribution Engine through asynchronous local state caching (`AttributionThesisSnapshot`) and embeds deterministic `PolicyInputSnapshot` structures directly into event contracts. Finally, an explicit lineage model guarantees perfect auditability across multi-generational attribution restatements.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `AttributionService` | WP-14 Attribution Engine | Stateless Domain Service computing fractional attribution using role weights. |
| `AttributionThesisSnapshot` | WP-14 Attribution Engine | Local read-model projection of Thesis contributors built via async events. |
| `PolicyInputSnapshot` | WP-14 Attribution Engine | Immutable record of exact parameters used during a specific calculation. |
| Restatement Approval | WP-## Governance Engine | The formal owner of deciding if a restatement request is legally approved. |

## 3. Architecture Overview
The Attribution Engine operates in a fully decoupled event-driven flow:
1. **Preparation**: It listens to Thesis events to asynchronously build an `AttributionThesisSnapshot` locally.
2. **Execution**: It consumes `InvestmentOutcomeRealizedEvent`, retrieves the local snapshot, reads the `AttributionPolicyRegistry` to extract a `PolicyInputSnapshot`, and delegates calculation to the `AttributionService`.
3. **Distribution**: It emits `AttributionCalculatedEvent` via Outbox.
4. **Correction**: `AttributionRestatementRequested` goes to the Governance Engine, which emits `AttributionRestatementApproved`, triggering the Attribution Engine to execute lineage-tracked reversals.

## 4. Domain Model
- **`AttributionService`**: Pure stateless calculation domain service.
- **`AttributionThesisSnapshot`**: Local, async-replicated read-model of thesis actors.
- **`AttributionPolicyRegistry`**: Repository of formulas and base parameter weights.

## 5. Aggregate Design
**`AttributionThesisSnapshot` (Cache Aggregate)**
- **Identity**: `thesis_id`.
- **State**: Array of `TargetIdentity` coupled with explicit `RoleIdentity` (AUTHOR, REFINER, APPROVER).
- **Justification**: Eliminates synchronous querying to the Thesis Engine. Managed via simple UoW when upstream `ThesisResolvedEvent` is intercepted.

*Note: The canonical `OutcomeAttribution` aggregate remains REMOVED in favor of the stateless service + events defined in v1.*

## 6. Value Objects
- **`AttributionIdentity`**: `attribution_id`, `outcome_id`, `thesis_id`, `parent_attribution_id` (nullable), `attribution_generation` (int).
- **`ContributionWeight`**: `role_identifier`, `target_identity`, `weight_fraction` (0.0 - 1.0).
- **`PolicyInputSnapshot`**: A dictionary-style VO containing exact runtime policy parameters (e.g., `{"AUTHOR_WEIGHT": 0.6, "REFINER_WEIGHT": 0.2, "APPROVER_WEIGHT": 0.2}`).
- **`AttributionScope`**: Enumeration of targeted financial concepts (PNL, RETURN). Baseline for Sprint-14 is `PNL`.
- **`TargetAttribution`**: `target_identity`, `attributed_value` (absolute), `attributed_scope`.

## 7. Event Contracts
- **`AttributionCalculatedEvent`**:
  - `attribution_identity`: Complete lineage object.
  - `attribution_scope`: Explicit array of scopes (PNL, RETURN).
  - `policy_input_snapshot`: Embedded runtime parameters.
  - `allocations`: Exact calculated absolute values per target.
- **`AttributionReversedEvent`**:
  - `attribution_identity`: Target ID being voided.
  - `reason` and `governance_approval_reference`.

## 8. Application Services
- **`AttributionApplicationService`**:
  - `process_outcome(cmd)`: Fetches local snapshot, calculates, emits event.
  - `apply_approved_restatement(cmd)`: Triggered via governance. Reverses lineage parent, recalculates, emits new generation event.
  - `build_thesis_snapshot(cmd)`: Internal async handler creating the `AttributionThesisSnapshot`.

## 9. Repositories
- **`AttributionSnapshotRepository`**: Manages the local UoW persistence for `AttributionThesisSnapshot`.

## 10. Persistence Design
- **`attribution_thesis_snapshot` table**: `thesis_id` (PK), `contributors` (JSONB).
- **Outbox Table**: High-throughput event staging.

## 11. Integration Design
- Listens to: `InvestmentOutcomeRealizedEvent` (from Portfolio), `ThesisResolvedEvent` (from Thesis), `AttributionRestatementApprovedEvent` (from Governance).
- Emits: `AttributionCalculatedEvent`, `AttributionReversedEvent` via Outbox.

## 12. Sequence Diagrams
**Async Thesis Snapshot**:
1. Thesis Engine emits `ThesisResolvedEvent`.
2. Attribution Engine saves `AttributionThesisSnapshot`.

**Outcome Processing**:
1. Portfolio emits `InvestmentOutcomeRealizedEvent`.
2. AppService loads local `AttributionThesisSnapshot` (zero runtime coupling).
3. Registry provides `PolicyInputSnapshot` (e.g., 60/20/20).
4. `AttributionService` computes specific values.
5. Outbox emits `AttributionCalculatedEvent` with generation=1.

## 13. State Diagrams
Lineage State for a specific attribution chain:
`GENERATION_1` -> (Governance Restatement) -> `GENERATION_2` -> (Governance Restatement) -> `GENERATION_3`.

## 14. Failure Handling
- Local snapshot miss (`AttributionThesisSnapshotNotFound`): Forces a retry backoff.
- Fractional validation mismatch: Exception aborts UoW.
- Unauthorized Restatement: AppService rejects requests lacking valid `AttributionRestatementApprovedEvent` signatures.

## 15. OCC Strategy
- Local `AttributionThesisSnapshot` relies on OCC.
- Restatement logic relies on strictly sequential lineage IDs preventing fork conditions (e.g., creating Gen 3 twice from Gen 2).

## 16. Scalability Analysis
The introduction of `AttributionThesisSnapshot` transforms what was an O(N) runtime remote bottleneck into an O(1) local read, enabling massive concurrent processing of `InvestmentOutcomeRealizedEvent`s.

## 17. Security Analysis
Governance approval bounds Restatement workflows. The Attribution Application Service structurally refuses to restate any chain without an embedded cryptographically-safe Governance approval signature.

## 18. Migration Strategy
Create `attribution_thesis_snapshot` local table schema.

## 19. Risks
- **Snapshot Race Conditions**: If an outcome arrives before the local snapshot is written.
- **Mitigation**: The command bus enforces exponential backoff DLQ retries when snapshots are temporarily absent.

## 20. ADR Decisions
- **ADR-14.8**: Asynchronous Thesis Snapshots eliminate synchronous runtime coupling.
- **ADR-14.9**: Role-Weighted Baseline. Equal-weighting is replaced with explicit configuration-driven role weighting.
- **ADR-14.10**: Explicit Policy Input Snapshots. Events must carry the exact parameters used, isolating replayability from external code changes.
- **ADR-14.11**: Strict Governance Restatement. Attribution lacks authority to trigger its own revisions.
- **ADR-14.12**: Lineage Tracking. All attributions are recursively linked via `parent_attribution_id` and `generation`.

## 21. Architecture Challenges
**Q: Why store the inputs rather than just the policy version?**
A: Hardcoded definitions in the registry might shift over years. By embedding `PolicyInputSnapshot` (the 60/20/20 split values) into the event, the event becomes entirely mathematically self-describing and independently reproducible.

## 22. Architecture Delta Analysis
- **Delta**: Added local `AttributionThesisSnapshot` aggregate read-model.
- **Delta**: Shifted baseline policy to Role-Weighted calculations.
- **Delta**: Governance explicitly bound as a gateway to restatements.
- **Delta**: Scope definition natively bounded to PNL.

## 23. Acceptance Criteria
1. Architecture removes synchronous queries across bounded contexts.
2. Role-weights dynamically apply mathematical distribution based on snapshot roles.
3. Event contracts explicitly contain generation lineage and exact parameters.
4. Restatement operates via purely compensating asynchronous flows overseen by Governance.

## 24. Final Verdict
**READY_FOR_ARCHITECTURE_REVIEW**

## 25. Findings Resolution Matrix
- **#9 Synchronous Dependency**: Resolved. Async local cache via `AttributionThesisSnapshot` isolates runtime execution.
- **#10 Contribution Weight**: Resolved. Introduced `ContributionWeight` and adopted Role-Weighted baseline.
- **#11 Policy Input Snapshot**: Resolved. Exact mathematical inputs embedded as VOs inside `AttributionCalculatedEvent`.
- **#12 Attribution Scope**: Resolved. `AttributionScope` VO defines baseline (PNL, RETURN) guaranteeing explicit capital targeting.
- **#13 Replayability Validation**: Resolved. The dependency matrix defines `InvestmentOutcomeRealizedEvent`, Local Snapshot, and Embedded Inputs as the sole components, securing 100% determinism.
- **#14 Governance Ownership**: Resolved. Restatement triggers pushed to the Governance Engine. Attribution Engine acts as executioner only.
- **#15 Lineage Model**: Resolved. Added `parent_attribution_id` and `attribution_generation` to identity signatures.

## 26. Rejected Alternatives
- **Synchronous GRPC/REST queries to Thesis Engine**: Rejected due to latency and availability cascading risks.
- **Mutable Policy Versions**: Rejected. Once an event is fired, its historical mathematical parameters must be baked entirely into the `PolicyInputSnapshot`.

## 27. Tradeoff Analysis
The local cache strategy introduces "eventual consistency" risks where an outcome arrives before the Thesis snapshot is processed. The accepted tradeoff is to rely on transient retries rather than tightly coupling the monolith services via RPC.

## 28. Future Compatibility Assessment
Explicit lineage generation guarantees that future Review Engines and Capital Allocation algorithms can smoothly rollback virtual accounts by applying inverse calculations to previous generations safely.

## 29. Replayability Assessment
100% deterministic capability achieved. By storing the *exact mathematical constants* in the event (`PolicyInputSnapshot`), any downstream consumer or auditing replay can reconstruct the math without touching the codebase registry.

## 30. Freeze Readiness Assessment
Revision v2 successfully hardens the Attribution boundaries, solidifies event autonomy, enforces strict lineage security, and completely severs inter-service availability dependencies. Architecture is robust and ready for freeze.
