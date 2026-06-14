# ADR-042: Root Cause and Organizational Learning Model

## Status
Approved

## Date
2026-06-14

## Context
Defining a robust, scale-ready failure analysis model for Karsa's Virtual Investment Firm (VIF) requires addressing:
1. **Failure Complexity**: Failures in complex virtual investment loops are rarely due to a single root cause; they typically involve multiple contributing factors (e.g. LLM reasoning failure coupled with high market slippage).
2. **Aggregate Inflation**: Modeling findings, root causes, and lessons learned as separate aggregates causes database layout bloat and lock contention.
3. **Immutability and Hindsight Protection**: Analysis records must be strictly write-once and immutable once committed to prevent retroactive modifications.
4. **Asynchronous Learning Loops**: The engine must propagate captured lessons back to Research, Thesis, Governance, and Capital Allocation without directly writing to those databases.

## Decision
We implement the following root-cause and organizational learning model:

1. **Formal Failure Taxonomy**:
   - We standardize failure categories into a hierarchy including: `Thesis Failure`, `Research Failure`, `Decision Failure`, `Execution Failure`, `Governance Failure`, `Risk Failure`, `Regime Failure`, `Provider Failure`, `Model Failure`, and `Process Failure`.

2. **Weighted Contributing Causes (Option B)**:
   - Root causes are represented as a normalized list of contributing factors, each mapped to a taxonomy category and assigned a weight ($0.0 \le w \le 1.0$) where the sum of weights must equal exactly $1.0$.
   - This provides the best balance of representational accuracy, query performance, and attribution compatibility.

3. **Zero Mutable Aggregates / Single Ledger Entry**:
   - To prevent aggregate inflation and lifecycle state complexity, the context contains zero mutable aggregate roots.
   - `PostMortemRecord` is modeled as an Immutable Write-Once Ledger Entry, with all associated findings, contributing causes, and lessons modeled as nested value objects inside JSONB columns.

4. **Taxonomy Schema Versioning**:
   - Every `PostMortemRecord` explicitly stores a `taxonomy_version` field. When the failure taxonomy is upgraded, old records remain deterministically parseable and replayable against their original schemas.

5. **Event-Driven Learning Loop**:
   - Upon finalization, a `PostMortemRecord` is appended to the relational ledger. No SQL updates or state transitions are supported.
   - The service emits a `PostMortemRecordCreatedEvent` containing the classification, weights, and action items.
   - Downstream contexts ingest this event to execute their respective adjustments (e.g., Thesis Engine quarantines version, Governance reduces limit size).

6. **Elimination of OCC**:
   - Because rows are strictly write-once and never updated, OCC conflict management and version columns are entirely removed.

## Consequences
- **High Representation Accuracy**: Accurately models multi-factor systemic failures.
- **Lock-Free Scalable Writes**: Write-once relational SQL design eliminates lock contention.
- **Asynchronous, Decoupled Learning**: Feedback loops are executed safely via event handlers without tight coupling.
