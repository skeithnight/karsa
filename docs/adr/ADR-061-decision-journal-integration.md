# ADR-061: Decision Journal Integration

## Context
Initial iterations of the Unified Post-Outcome Evaluation Engine bound Thesis logic directly to Execution logic. This structurally severed the capability to record ex-ante rationalizations, preventing the Attribution engine from differentiating between "Wrong execution parameters" versus "Wrong interpretation of Thesis".

## Decision
Enforce the `DecisionJournal` as the mandatory intermediary between `Thesis` and `Execution`. No execution action may occur without generating an immutable `DecisionJournalEntry` specifying confidence, assumed risks, and invalidation criteria.

## Consequences
Restores causal intent separation. Satisfies the foundational knowledge graph of the Virtual Investment Firm. Guarantees Attribution engines have explicit datasets contrasting initial assumption bounds against final execution realities.
