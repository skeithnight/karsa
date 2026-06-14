# ADR-034: Qualitative Review Session and Learning Feedback Model

## Status
Approved

## Date
2026-06-14

## Context
A review workflow in Karsa must evaluate qualitative attributes of models, theses, and workers (e.g. prompt deviation, logical inconsistencies, API timeout cascades) and translate them into actionable system updates. 

To ensure auditability, consistency, and scalability, the design must solve:
1. **Evidence Persistence**: Reviews rely on transient observability traces and active performance snapshots. If a trace is deleted or a projection is rebuilt, the historical review evidence must remain intact.
2. **Actionable Recommendations**: Recommendations like "Deprecate Thesis Version v1.2 due to style shift" must have a structured, machine-readable format that downstream services can process automatically.
3. **Formal State Machine**: A review session must follow a strict, non-reversible lifecycle state machine to ensure compliance.

## Decision
We implement the following domain model for the Review Engine:

1. **ReviewSession as an Aggregate Root**:
   - Manages the audit lifecycle.
   - Enforces a formal state machine: `CREATED` → `IN_PROGRESS` → `COMPLETED` (requires a `ReviewVerdict`) or `ABANDONED`.
   - Contains a collection of `ReviewFinding` value objects and `ReviewEvidence` snapshots.
2. **LearningFeedback as a separate Aggregate Root**:
   - Represents the outputs of a ReviewSession (e.g. proposed thesis deprecation, allocation limit adjustment).
   - Separating `LearningFeedback` from `ReviewSession` avoids bloating the session document and allows downstream executors to mutate the feedback status (`PROPOSED` → `ACCEPTED`/`REJECTED` → `APPLIED`) independently and asynchronously.
3. **Structured ReviewEvidence Snapshots**:
   - `ReviewEvidence` value objects store the raw, immutable payload or reference identifiers (`trace_id`, `evaluation_id`) captured at the moment the evidence is registered, ensuring replayability and preventing loss when external systems clean up telemetry storage.
4. **regime_id Conditioning**:
   - All review findings and verdicts include an optional `regime_id` field to support regime-aware analysis, ensuring post-mortems distinguish performance between different market environments.

## Consequences
- **Replay & Audit Preservation**: Historical review sessions can be inspected years later with the exact trace snapshots and evaluation facts preserved in `ReviewEvidence`.
- **Automated Learning Loop**: Systems can subscribe to `LearningFeedbackAppliedEvent` to automate risk overrides, reducing human operational latency.
- **Strict Concurrency Controls**: Standard VersionedAggregate implementation guarantees OCC safety on both `ReviewSession` and `LearningFeedback` aggregates using `aggregate_version` columns.
