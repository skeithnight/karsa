# ADR-058: Mathematical Absolute Limits on Governance

## Context
The Governance Engine possesses the authority to suspend or promote workers based on aggregated Trust Scores. There is a risk of Governance logic attempting to override or "correct" Attribution logic if a stakeholder disagrees with an outcome.

## Decision
The Governance Engine is mathematically restricted to consuming Attribution and Performance arrays exactly as provided. It has zero capability, both structurally and at the API level, to overwrite attribution factors or modify raw facts.

## Consequences
Guarantees absolutely deterministic, mathematical accountability. Governance cannot overwrite Performance facts. HR and Promotion pathways are bounded by unforgeable mathematical histories.
