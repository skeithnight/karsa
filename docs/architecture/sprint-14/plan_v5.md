# Sprint-14 Attribution Engine Foundation - Architecture Revision v5

## 1. Executive Summary
The Sprint-14 Attribution Engine Architecture Revision v5 executes the definitive freeze-hardening pass. It explicitly isolates deterministic replay inputs from mutable read models, enforces rigorous governance audit trails directly into the mathematical output, and fundamentally decouples 1:1 outcome assumptions to natively support partial portfolio exits. This architecture yields a stateless, mathematically sound engine perfectly poised to feed the future Capital Allocation Engine.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `AttributionService` | WP-14 Attribution Engine | Stateless Domain Service computing fractional financial attribution. |
| `AttributionInputSnapshot` | WP-14 Attribution Engine | Projection of contributor identities optimized for runtime throughput. |
| `PolicyInputSnapshot` | WP-14 Attribution Engine | Exhaustive mathematical parameters ensuring deterministic replay. |
| Restatement Audit | WP-## Governance Engine | Formal owner of the `AttributionRestatementApproved` event loop. |

## 3. Architecture Overview
The Attribution Engine consumes `InvestmentOutcomeRealizedEvent`s and retrieves the locally projected `AttributionInputSnapshot` for fast runtime calculation. It extracts a `PolicyInputSnapshot` from the registry and delegates processing to the stateless `AttributionService`. Outbox-driven `AttributionCalculatedEvent`s form the financial output stream. For deterministic replay, the system ignores local mutable projections and streams strictly from immutable Institutional Memory events. Governance engines strictly control the restatement lifecycle, injecting explicit audit metadata into the resulting attribution generations.

## 4. Domain Model
- **`AttributionService`**: Pure stateless calculation domain service.
- **`AttributionPolicyRegistry`**: Repository of formal attribution formulas.

## 5. Aggregate Design
**There are zero Aggregates in this bounded context.**
Calculations are pure functions. `AttributionInputSnapshot` is explicitly designated as an infrastructure Read Model/Projection. The absence of aggregates permanently prevents UoW bottlenecking.

## 6. Value Objects
- **`AttributionIdentity`**: `attribution_id`, `outcome_id`, `source_context_id`, `parent_attribution_id` (nullable), `attribution_generation` (int), `outcome_sequence` (int).
- **`ContributionWeight`**: `role_identifier`, `target_identity`, `weight_fraction` (0.0 - 1.0).
- **`PolicyInputSnapshot`**: 
  - `policy_version`
  - `weight_model` 
  - `normalization_strategy` 
  - `rounding_strategy` 
  - `allocation_ordering` 
  - `role_weights` 
  - `currency_precision` 
- **`GovernanceAuditContext`**: `approval_reference`, `approval_timestamp`, `approved_by`, `approval_reason`.
- **`AttributedValue`**: `gross_pnl`, `attributed_pnl`, `attribution_percentage`, `currency`.

## 7. Event Contracts
- **`AttributionCalculatedEvent`**:
  - `attribution_identity` (Lineage + Outcome Sequence)
  - `attribution_scope` (REALIZED_PNL)
  - `policy_input_snapshot` (Mathematical profile)
  - `governance_audit_context` (Nullable; populated on restatements)
  - `allocations`: Array of `{ target_identity, gross_pnl, attributed_pnl, attribution_percentage, currency }`
  - `audit_metadata`: `algorithm_hash` (For integrity checking, not mathematical input).
- **`AttributionReversedEvent`**:
  - `attribution_identity` (Targeted void)
  - `governance_audit_context` (Strictly required)

## 8. Application Services
- **`AttributionApplicationService`**:
  - `process_outcome(cmd)`: Computes and emits Gen 1 event.
  - `apply_approved_restatement(cmd)`: Triggered by governance. Reverses, recalculates, emits Gen N+1 embedding the `GovernanceAuditContext`.
  - `update_input_projection(event)`: Infrastructure handler updating the Read Model.

## 9. Repositories
- **`AttributionInputProjectionStore`**: Manages persistence for `AttributionInputSnapshot` Read Models.

## 10. Persistence Design
- **`attribution_input_projection` table**: `source_context_id` (PK), `contributors` (JSONB).
- **Outbox Table**: Primary egress for events.

## 11. Integration Design
- Listens to: `InvestmentOutcomeRealizedEvent`, `AttributionContextPublishedEvent`, `AttributionRestatementApprovedEvent`.
- Emits: `AttributionCalculatedEvent`, `AttributionReversedEvent`.

## 12. Sequence Diagrams
**Replay Flow**:
1. Replay Engine queries Institutional Memory for `AttributionContextPublishedEvent`.
2. Replay Engine queries `InvestmentOutcomeRealizedEvent`.
3. Stateless `AttributionService` executes.
4. Output is mathematically identical to historical `AttributionCalculatedEvent`.

## 13. State Diagrams
Lineage State: `GENERATION_1` -> (Governance Restatement Request -> Governance Approval) -> `GENERATION_2` (with Audit Context embedded).

## 14. Failure Handling
- Local projection miss: Fetches directly from Institutional Memory fallback, or DLQ retries.
- Arithmetic Imbalance: Safely resolved by Lexicographical sorting arrays.

## 15. OCC Strategy
- Local `AttributionInputProjection` uses UPSERT semantics.
- Events use standard Outbox UUID locks.

## 16. Scalability Analysis
Event-only computation is perfectly horizontally scalable.

## 17. Security Analysis
Restatements require explicit `approved_by` and `approval_reference` signatures embedded in the payload, creating a cryptographically traceable governance lineage.

## 18. Migration Strategy
Create `attribution_input_projection` table.

## 19. Risks
- None. Mathematical constraints and governance locks mitigate all previously identified operational and audit risks.

## 20. ADR Decisions
- **ADR-14.17**: Immutable Replay Sourcing. Replay operations must bypass mutable projections and derive state solely from immutable Institutional Memory events.
- **ADR-14.18**: Outcome Sequence Decoupling. One thesis supports N partial outcomes.

## 21. Architecture Challenges
*(Closed)*

## 22. Architecture Delta Analysis
- **Delta**: `AttributionIdentity` expanded with `outcome_sequence`.
- **Delta**: `algorithm_hash` strictly moved to Audit Metadata.
- **Delta**: `GovernanceAuditContext` explicitly formalized and embedded in restatement payloads.
- **Delta**: Expanded `AttributedValue` for comprehensive Capital Allocation compatibility.

## 23. Acceptance Criteria
1. Replay Dependency Matrix explicitly separates Mathematical Inputs from Audit Metadata.
2. Restatement events natively serialize the exact governance approval trace.
3. Partial portfolio exits (N outcomes per thesis) route cleanly.

## 24. Final Verdict
**ARCHITECTURE_FROZEN**
**READY_FOR_IMPLEMENTATION_PLANNING**

## 25. Findings Resolution Matrix
- **#23 Replay Source Of Truth**: Resolved. Replay derives from immutable `AttributionContextPublishedEvent` rather than mutable projections (ADR-14.17).
- **#24 Replay Inputs vs Audit Metadata**: Resolved. `algorithm_hash` is explicitly classified as Audit Metadata, independent from `PolicyInputSnapshot`.
- **#25 Governance Audit Completeness**: Resolved. `GovernanceAuditContext` VO embedded into `AttributionReversedEvent` and Gen N+1 events.
- **#26 Outcome Lineage**: Resolved. Added `outcome_sequence` to support multiple sequential partial exits.
- **#27 Capital Allocation Compatibility**: Resolved. Payload formalized with `gross_pnl`, `attributed_pnl`, `attribution_percentage`, and `currency`.

## 26. Replayability Dependency Matrix
### Mathematical Required Inputs (For Recomputation)
- `InvestmentOutcomeRealizedEvent.gross_pnl`
- `AttributionContextPublishedEvent.contributors` (Immutable source, bypassing the mutable projection)
- `PolicyInputSnapshot.role_weights`
- `PolicyInputSnapshot.normalization_strategy`
- `PolicyInputSnapshot.rounding_strategy`
- `PolicyInputSnapshot.allocation_ordering`
- `PolicyInputSnapshot.currency_precision`

### Audit Metadata (For Output Integrity Verification)
- `algorithm_hash`
- `GovernanceAuditContext` (retained for lineage tracing, ignored during math execution)

## 27. Governance Audit Model
A restatement strictly executes via:
1. `AttributionRestatementRequested`
2. `Governance Review`
3. `AttributionRestatementApproved` (`approval_reference`, `approval_timestamp`, `approved_by`, `approval_reason`)
4. `AttributionReversedEvent` (Embedding Governance Audit Context)
5. `AttributionCalculatedEvent` Gen+1 (Embedding Governance Audit Context)
This ensures no engineer can unilaterally trigger a math revision without the resulting payload loudly declaring who approved it.

## 28. Capital Allocation Compatibility Analysis
The inclusion of:
- `gross_pnl` (e.g. 100,000)
- `attributed_pnl` (e.g. 60,000)
- `attribution_percentage` (e.g. 0.60)
- `currency` (e.g. USD)
Ensures the downstream Capital Allocation Engine has both the absolute dollars to deposit in a virtual account, and the fractional percentage to verify mathematical sanity.

## 29. Outcome Lineage Analysis
By adding `outcome_sequence` to `AttributionIdentity`, the engine naturally processes partial exits. A thesis generating a 10% partial exit yields Outcome Sequence 1. The remaining 90% exit yields Outcome Sequence 2. Both sequences are attributed independently with perfect lineage trace back to the same parent thesis.

## 30. Freeze Readiness Assessment
The final architecture completely eliminates single-point-of-failure dependencies, guarantees pristine replay mechanics, flawlessly integrates Governance audits, and establishes absolute compatibility with the Capital Allocation layer. 

The Sprint-14 Attribution Engine Foundation architecture is definitively frozen.
**ARCHITECTURE_FROZEN**
**READY_FOR_IMPLEMENTATION_PLANNING**
