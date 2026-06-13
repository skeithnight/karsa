# Final Minor-Adjustment Review: Sprint-11.5 Stabilization

## 1. Executive Summary
This document completes the final minor-adjustment review of the Sprint-11.5 Stabilization plan. Having previously reigned in the scope to strictly mechanical and deterministic foundations (UoW, OCC, Event Envelopes), this review ensures the *schemas* of those foundations are fully sufficient for future Attribution, Performance, and Capital Allocation engines. The review mandates the inclusion of `originator_type` and `originator_version` to track AI model performance natively. It rejects overly complex lineage arrays in favor of strict `correlation_id` / `causation_id` propagation. Finally, it approves the drafting of the `ExecutionOutcome` contract (without implementation) as a necessary boundary definition to secure Attribution readiness. 

## 2. OriginatorIdentity Review
**Current Proposal**: `originator_id`
**Evaluation**: An ID alone is insufficient for the Performance Engine to distinguish between human analysts, quantitative heuristics, and LLM-driven AI agents. To properly build Capital Allocation loops, the system must track performance by originator class and algorithm version.
**Recommendation**: The `OriginatorIdentity` structure must include:
- `originator_id`: (e.g., "USER-492" or "MODEL-GPT4")
- `originator_type`: (e.g., "HUMAN", "LLM", "QUANT")
- `originator_version`: (e.g., "v1.2", "2024-05-snapshot")
**Classification**: MUST DO NOW. (Adding 2 scalar fields to an event envelope payload requires minimal effort but prevents massive historical data loss).

## 3. Event Lineage Review
**Current Proposal**: `correlation_id`, `causation_id`
**Evaluation**: `causation_id` points to the direct parent event. `correlation_id` points to the root event. For an execution outcome to trace back through Portfolio -> Allocation -> Thesis -> Research, these two fields provide a perfect singly-linked tree structure traversable via recursive SQL or graph queries on the WORM storage.
**Recommendation**: Do NOT add `parent_ids` or `lineage_ids` arrays. Array-based lineage within event payloads is a denormalization anti-pattern that bloats event size and duplicates the data inherently captured by recursively following `causation_id`.
**Classification**: REJECT (Lineage arrays). Keep strictly to `correlation_id` and `causation_id`.

## 4. ExecutionOutcome Contract Review
**Evaluation**: The `ExecutionOutcome` is the exact mathematical inverse of the `PortfolioDecision`. Attribution is the delta between the two. If WP-18 stabilizes without defining the shape of the outcome it expects back from the future WP-14 (Execution Engine), the boundaries remain untested.
**Recommendation**: Define an explicit `ExecutionOutcomeContract` in `karsa.shared.contracts`.
- `decision_id`, `intent_id`
- `execution_status` (FILLED, PARTIAL, FAILED)
- `filled_quantity`, `average_fill_price`
- `fees`, `slippage`
**Classification**: SHOULD DO NOW. (Schema definition only. No code implementation. Guarantees WP-18 Intent structures are practically executable).

## 5. Attribution Compatibility Analysis
Attribution relies on measuring *Intent vs Reality*. By standardizing the `PlatformEventEnvelope` and explicitly drafting the `ExecutionOutcomeContract` now, the pipeline guarantees that when WP-14 goes live, its output will perfectly map back to the `decision_id` locked in the `DecisionContextSnapshot`. Compatibility is fully secured.

## 6. Performance Compatibility Analysis
Performance relies on measuring *P&L vs Originator*. By upgrading the `OriginatorIdentity` to include `type` and `version`, the Performance Engine will be able to answer queries such as: "Are LLM-driven theses outperforming Human theses under High Volatility Regimes?" Compatibility is fully secured.

## 7. Capital Allocation Compatibility Analysis
Capital Allocation relies on shifting risk budgets toward historically successful Originators. Because Performance is secured, Capital Allocation receives the pristine input signals it needs.

## 8. Recommended Sprint-11.5 Additions
1. Expand `OriginatorIdentity` fields in the `PlatformEventEnvelope` schema.
2. Draft the `ExecutionOutcome` JSON/Protobuf schema in `karsa.shared.contracts`.

## 9. Explicit Non-Goals
- No semantic graph databases.
- No `ArtifactLink` relationship definitions.
- No new bounded contexts (Knowledge Engine, Graph DB).
- No implementation of the Execution Engine.

## 10. Risks
- Drafting the `ExecutionOutcome` contract now risks requiring revisions when WP-14 is actually implemented and encounters real-world broker API constraints. (Mitigation: Treat the contract as a draft interface, versioned strictly).

## 11. Final Verdict
**READY_FOR_IMPLEMENTATION**

**Rationale**: The adjustments requested (3 fields in an envelope, 1 contract definition file) introduce near-zero implementation drag while completely closing the conceptual gaps for the future Attribution and Performance engines. Sprint-11.5 is now mathematically, mechanically, and conceptually bulletproof. Engineering execution may commence immediately.
