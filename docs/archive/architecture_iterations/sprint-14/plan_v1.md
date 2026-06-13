# Sprint-14 Attribution Engine Foundation - Architecture Revision v1

## 1. Executive Summary
The Sprint-14 Attribution Engine Architecture Revision v1 refines the canonical attribution layer by removing unnecessary persistence aggregates in favor of a pure, stateless domain service. It addresses prior review findings by introducing `ThesisContributionSnapshot` to avoid knowledge graphs, explicitly defining the `AttributionPolicy` value object, and using compensating events instead of mutable aggregate state for restatements. The Attribution Engine serves as the bridge between realized financial outcomes and the future Capital Allocation Engine, rigorously defining "who generated value."

## 2. Ownership Boundary Matrix
| Concept | Bounded Context | Description |
|---------|-----------------|-------------|
| `AttributionService` | WP-14 Attribution Engine | Stateless Domain Service computing fractional financial attribution. |
| `AttributionPolicyRegistry` | WP-14 Attribution Engine | Source of truth for versioned deterministic attribution formulas. |
| `ThesisContributionSnapshot` | WP-14 Attribution Engine | Immutable flat list of contributing identities at the time of resolution. |

## 3. Architecture Overview
The Attribution Engine abandons persistence-heavy aggregates. Instead, the `AttributionApplicationService` consumes external `InvestmentOutcomeRealizedEvent` messages, delegates calculation to the stateless `AttributionService`, and immediately emits `AttributionCalculatedEvent` payloads via the standard Outbox pattern. Institutional Memory acts as the durable ledger for these events, while future engines (e.g., Capital Allocation) will project them into temporal profiles.

## 4. Domain Model
- **`AttributionService`**: Pure function service calculating the value spread.
- **`AttributionPolicyRegistry`**: Hardcoded dictionary of `AttributionPolicy` objects.
- **`AttributionPolicy`**: Defines the fractional distribution rules.

## 5. Aggregate Design
**OutcomeAttribution (Aggregate)** has been **REMOVED**.
*Justification*: Attribution is a mathematical derivative of an outcome and a snapshot. It has no long-term mutating lifecycle. Revisions to attributions are purely functional restatements. Replacing the aggregate with an event-stream model avoids UoW contention and perfectly matches the "Single Aggregate UoW" platform constraint by removing a needless aggregate entirely.

## 6. Value Objects
- **`AttributionIdentity`**: `attribution_id`, `outcome_id`, `thesis_id`, `policy_version`.
- **`AttributionPolicy`**: `policy_id`, `version`, `algorithm_hash`, `allocation_strategy` (e.g., EQUAL_WEIGHT).
- **`TargetIdentity`**: `target_id`, `target_type`.
- **`ThesisContributionSnapshot`**: Flat VO containing lists of originators, workers, and strategies.
- **`AttributedValue`**: `attributed_pnl`, `attributed_return`, `attributed_alpha`, `attributed_weight`.

## 7. Event Contracts
- **`AttributionCalculatedEvent`**:
  - `attribution_id`
  - `outcome_id`
  - `thesis_id`
  - `policy_version`
  - `realized_at` (Supports future temporal windows)
  - `allocations`: Array of `{ target_identity, attributed_pnl, attributed_return, attributed_alpha, attributed_weight }`
- **`AttributionReversedEvent`**:
  - `original_attribution_id`
  - `reason`

## 8. Application Services
- **`AttributionApplicationService`**:
  - `process_outcome(cmd: ProcessOutcomeCommand)`: Loads snapshot, runs service, fires `AttributionCalculatedEvent` to Outbox.
  - `restate_attribution(cmd: RestateAttributionCommand)`: Fires `AttributionReversedEvent` followed by a new `AttributionCalculatedEvent`.

## 9. Repositories
No explicit `AttributionRepository` is required because there is no `OutcomeAttribution` aggregate.
(Institutional Memory passively records the events).

## 10. Persistence Design
Only the **Outbox Table** is utilized. Zero domain tables are created for Attribution in Sprint-14. 

## 11. Integration Design
- Listens to: `InvestmentOutcomeRealizedEvent` (from Portfolio).
- Emits: `AttributionCalculatedEvent`, `AttributionReversedEvent` via Outbox.

## 12. Sequence Diagrams
1. `InvestmentOutcomeRealizedEvent` arrives.
2. `AttributionApplicationService` invoked.
3. Fetches `ThesisContributionSnapshot` from Thesis context.
4. Invokes `AttributionService.calculate()`.
5. UoW Opens -> Save Outbox `AttributionCalculatedEvent` -> Commit UoW.

## 13. State Diagrams
No state machines exist in this context due to the stateless design.

## 14. Failure Handling
- Missing snapshot or registry policy gracefully aborts with DLQ routing.
- Math validation ensures all fractional `attributed_weight` sum precisely to 1.0; failures prevent UoW commit.

## 15. OCC Strategy
Because no aggregate is saved, OCC contention on the Attribution layer is effectively zero. Outbox insertion is intrinsically lock-free.

## 16. Scalability Analysis
The stateless architecture scales linearly. Bottlenecks are completely removed as there are no row-level locks required to attribute an outcome.

## 17. Security Analysis
Cryptographic `algorithm_hash` verification ensures the policy used for calculation is strictly deterministic and auditable.

## 18. Migration Strategy
No database migrations required (only infrastructure application logic).

## 19. Risks
- **Upstream Latency**: Retrieving `ThesisContributionSnapshot` via synchronous API might induce latency if the Thesis Engine is under load.
- **Mitigation**: Cache the snapshot locally upon listening to `ThesisEvaluatedEvent`.

## 20. ADR Decisions
- **ADR-14.4**: Downgrade `OutcomeAttribution` from Aggregate to Domain Service.
- **ADR-14.5**: Flatten `ContributionGraph` to `ThesisContributionSnapshot`.
- **ADR-14.6**: Compensating Events for Restatement instead of mutable aggregate versions.
- **ADR-14.7**: Attribution owns Financial Value mapping; Performance owns Prediction Accuracy.

## 21. Architecture Challenges
**Q: How is future windowing supported without aggregates?**
A: `AttributionCalculatedEvent` includes the `realized_at` timestamp. Future `AttributionProfileWindow` aggregates will consume these events and apply temporal bucketization (e.g., 30D/90D) exactly as the Performance Engine does.

## 22. Architecture Delta Analysis
- **Delta**: Removed WP-14 Domain Database schema.
- **Delta**: Shifted to 100% Event-Driven calculation.
- **Delta**: Formalized `AttributionPolicy` explicit modeling.

## 23. Acceptance Criteria
1. Service computes fractions summing precisely to 1.0.
2. Equal-weight strategy cleanly handles N contributors.
3. Restatements yield negative/compensating events.
4. Output payload satisfies all future Capital Allocation metrics.

## 24. Final Verdict
**READY_FOR_FREEZE_REVIEW**

## 25. Review Findings Resolution Matrix
- **#1 Valid Aggregate**: Resolved. Aggregate removed. Replaced with `AttributionService` + Event.
- **#2 Knowledge Graph**: Resolved. Replaced with immutable `ThesisContributionSnapshot`.
- **#3 Policy Model**: Resolved. `AttributionPolicy` VO defined. Baseline strategy is `equal-weight`.
- **#4 Window Compatibility**: Resolved. Payload includes `realized_at` to support downstream temporal sharding.
- **#5 Prediction vs Value**: Resolved. Boundary formalized via ADR-14.7.
- **#6 Restatement Model**: Resolved. Moved to Option B (Compensating Events) avoiding mutability.
- **#7 Attribution Identity**: Resolved. `AttributionIdentity` VO ensures unique trace linking.
- **#8 Capital Allocation Gap**: Resolved. Payload expanded to include absolute PnL, Return, Alpha, and Weight.

## 26. Rejected Alternatives
- **Mutable Aggregate**: Rejected due to unnecessary UoW contention and poor auditability during recalculations.
- **Role-Weighted Strategy**: Rejected for baseline (Sprint-14). Equal-weight is mathematically simpler for establishing foundation; role-weighting deferred to future iteration.

## 27. Tradeoff Analysis
Moving to a purely stateless service increases reliance on Institutional Memory for historical queries, meaning ad-hoc attribution lookups require event replay or downstream projections rather than a simple database `SELECT`. This tradeoff is accepted to maximize write throughput and UoW safety.

## 28. Future Compatibility Assessment
The expanded event payload natively supports the Capital Allocation Engine, offering absolute financial values rather than raw percentages. The `realized_at` timestamp natively enables future temporal bucketing (30D, 90D).

## 29. Replayability Assessment
Replayability is 100% preserved. Because calculations rely entirely on the `algorithm_hash` tied to a specific `policy_version`, re-processing historical `InvestmentOutcomeRealizedEvent`s will consistently yield the exact same fractional distributions.

## 30. Freeze Readiness Assessment
The architecture has aggressively eliminated platform constraints violations, resolved all review findings, and simplified the implementation burden significantly by leveraging the existing Outbox/UoW infrastructure. The architecture is formally ready for freeze.
