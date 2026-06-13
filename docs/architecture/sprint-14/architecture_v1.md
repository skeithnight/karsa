# Sprint-14 Attribution Engine Foundation - Architecture Package

## 1. Executive Summary
The Sprint-14 Attribution Engine Foundation establishes the canonical layer for determining "Who generated value?" within the Karsa Virtual Investment Firm. While the Performance Engine tracks prediction accuracy and empirical hits/misses, the Attribution Engine distributes actual realized financial value (gains and losses) proportionally across the Originators, Workers, and Strategies that contributed to the underlying Thesis. This architecture defines the immutable `OutcomeAttribution` aggregate, ensuring 100% fractional allocation of value, strict auditability, and deterministic recalculation via versioned attribution policies.

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `OutcomeAttribution` | WP-14 Attribution Engine | Core aggregate. Represents the fractional distribution of a single realized investment outcome. |
| `AttributionPolicyRegistry` | WP-14 Attribution Engine | Static rule dictionary ensuring deterministic calculation of attribution fractions. |
| `ThesisContributionSnapshot` | WP-14 Attribution Engine | Immutable snapshot of all actors (Originators, Workers, Strategies) attached to a Thesis at the time of resolution. |

## 3. Architecture Overview
The Attribution Engine acts as a bridge between the Thesis/Performance layers and the future Capital Allocation/Portfolio layers. 
1. The future Portfolio Engine will publish `InvestmentOutcomeRealizedEvent`s containing financial gains/losses.
2. The Attribution Engine consumes these events, fetches the `ThesisContributionSnapshot` (or retrieves the historical actors from the Thesis Engine), and applies a versioned `AttributionPolicy`.
3. The engine generates an `OutcomeAttribution` aggregate representing how the value is split.
4. It publishes `AttributionCalculatedEvent`s, which will eventually inform the Capital Allocation Engine how to distribute rewards/capital.

## 4. Domain Model
- **`OutcomeAttribution`**: The canonical record of how a specific financial outcome was divided.
- **`AttributionFraction`**: A value object representing a percentage of the total outcome mapped to a specific `TargetIdentity`.
- **`AttributedValue`**: The absolute financial representation (e.g., dollars, alpha) assigned to a fraction.

## 5. Aggregate Design
**`OutcomeAttribution` (Aggregate Root)**
- **Identity**: `outcome_id` (corresponds to a realized trade/investment closure).
- **State**:
  - `thesis_id`: The driving thesis.
  - `total_value_realized`: Total gain/loss.
  - `allocations`: List of `TargetAttribution` VOs.
  - `policy_version`: The formula hash used.
- **Invariants**: 
  - The sum of all percentage fractions must equal exactly 1.0 (100%).
  - Cannot be mutated once finalized. Revisions require an explicit compensation action or a new `version` bump reflecting a formal restatement.

## 6. Value Objects
- **`TargetIdentity`**: `target_id`, `target_type` (Originator, Worker, Strategy).
- **`FinancialOutcome`**: `currency`, `amount`, `outcome_type` (GAIN, LOSS, YIELD).
- **`TargetAttribution`**: `target_identity`, `fraction` (0.0 - 1.0), `attributed_amount`.
- **`ContributionGraph`**: Represents the network of actors involved in the thesis.

## 7. Event Contracts
- **`AttributionCalculatedEvent`**:
  - `outcome_id`
  - `thesis_id`
  - `total_value`
  - `allocations`: Map of `target_id` -> `attributed_amount`
  - `policy_version`
- **`AttributionRestatedEvent`**: Used when a historical error is corrected and an attribution is recalculated.

## 8. Application Services
- **`OutcomeAttributionService`**:
  - `attribute_outcome(cmd: AttributeOutcomeCommand)`: Opens UoW, runs policy, saves `OutcomeAttribution`, fires Outbox event.
  - `restate_attribution(cmd: RestateAttributionCommand)`: Opens UoW, runs new policy, bumps aggregate version, fires Restated event.

## 9. Repositories
- **`AttributionRepository`**:
  - `get_by_outcome(outcome_id: str) -> OutcomeAttribution`
  - `save(attribution: OutcomeAttribution)`

## 10. Persistence Design
**`outcome_attribution` table**:
- `outcome_id` (PK)
- `thesis_id`
- `version` (OCC)
- `total_amount`
- `currency`
- `allocations` (JSONB)
- `policy_version`
- `created_at`, `updated_at`

## 11. Integration Design
- Listens to: `InvestmentOutcomeRealizedEvent` (future mock) and `ThesisEvaluatedEvent` (to cache contribution snapshots if necessary).
- Emits: `AttributionCalculatedEvent` via Outbox.
- Strictly single UoW per outcome.

## 12. Sequence Diagrams
**Standard Flow**:
1. External System (Portfolio) emits `InvestmentOutcomeRealizedEvent`.
2. `AttributionSaga` translates to `AttributeOutcomeCommand`.
3. `OutcomeAttributionService` fetches thesis context.
4. `AttributionPolicyRegistry` calculates 100% fractional spread.
5. Aggregate `OutcomeAttribution` is saved (OCC checked).
6. Outbox writes `AttributionCalculatedEvent`.
7. UoW Commits.

## 13. State Diagrams
`OutcomeAttribution` is essentially an Append-Only immutable record.
State: `CALCULATED` -> (Optional) `RESTATED`.

## 14. Failure Handling
- **Missing Thesis Context**: Fails the command. Retry via Dead Letter Queue (DLQ).
- **Fractional Remainder Errors**: Policy validation throws `AttributionImbalanceException` if fractions do not equal exactly 1.0. Prevents database commit.
- **OCC Conflicts**: Standard `ConcurrencyConflictError` during restatements.

## 15. OCC Strategy
Updates (restatements) to an `OutcomeAttribution` enforce `UPDATE ... WHERE outcome_id=%s AND version=%s`.

## 16. Scalability Analysis
Unlike Performance Profiles which suffer from temporal hotspotting, `OutcomeAttribution` aggregates are perfectly horizontally sharded by `outcome_id`. Write contention is naturally zero for new outcomes.

## 17. Security Analysis
Immutable ledgers prevent arbitrary assignment of financial value to malicious internal workers. Policy hashes guarantee that the exact mathematical rules used for distribution are cryptographically traceable.

## 18. Migration Strategy
Create `outcome_attribution` table. No legacy data to backfill since Capital/Portfolio layers do not yet exist.

## 19. Risks
- **Upstream Ambiguity**: Since the Portfolio engine doesn't exist, the exact schema of a "Financial Outcome" is theoretical.
- **Mitigation**: Isolate the `FinancialOutcome` VO so it can be easily adapted to the future Portfolio Engine's specific event schemas.

## 20. ADR Decisions
- **ADR-14.1**: `OutcomeAttribution` represents a single Realized Outcome, not a rolling ledger. Rolling totals belong in the future Capital Allocation Engine.
- **ADR-14.2**: Policy-Driven Fractional Math. Mathematical allocations must sum to 1.0 and are stored in a deterministic `AttributionPolicyRegistry` (mirroring Sprint-13 MetricRegistry).
- **ADR-14.3**: Separation of Performance and Attribution. Performance measures predictive accuracy; Attribution divides financial PnL. They are inherently decoupled.

## 21. Architecture Challenges
**Q: How are multiple contributors handled?**
A: `TargetAttribution` arrays allow unlimited actors, provided the `AttributionPolicy` guarantees their fractions sum to 100%.

**Q: How is attribution linked to future Capital Allocation?**
A: The future Capital engine will consume `AttributionCalculatedEvent`s and credit virtual bank accounts or allocation pools accordingly.

**Q: How are attribution reversals handled?**
A: Through `restate_attribution()`, which generates a new version of the Aggregate and fires an `AttributionRestatedEvent` for downstream engines to apply compensatory math.

## 22. Architecture Delta Analysis
This introduces a new bounded context `WP-14 Attribution Engine` but perfectly preserves all infrastructure foundations (UoW, Outbox, OCC, PlatformEventEnvelope) defined in Sprint-11.5.

## 23. Acceptance Criteria
1. The engine successfully converts a gross financial outcome into a 100% fractional distribution.
2. The UoW and Outbox patterns are maintained.
3. The design handles multiple originators and strategies correctly.
4. Replayability is guaranteed via policy hashes.

## 24. Final Verdict
**READY_FOR_ARCHITECTURE_REVIEW**
