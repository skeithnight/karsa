# ADR-059: Factor Model Versioning

## Context
Attribution engines map causal variance (Luck vs Skill). However, mathematical models for what constitutes Beta vs Alpha evolve over the decades. Replaying a 2026 performance trace in 2036 using 2036 mathematical definitions destroys historical replayability.

## Decision
Introduce `FactorModelVersion` as a strictly immutable cryptographic configuration artifact. The `AttributionDecomposition` aggregate must inherently store the `factor_model_version_urn` foreign key representing the precise factor definitions utilized at the exact chronological moment of evaluation.

## Consequences
Guarantees absolute 10-year+ historical deterministic replayability.
