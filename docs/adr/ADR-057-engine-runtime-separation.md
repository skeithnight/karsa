# ADR-057: Separation of Engine Runtimes

## Context
The Sprint-48 Unified Post-Outcome Evaluation Architecture merges Performance, Attribution, and Governance logic. Processing heavy factor regressions (Attribution) alongside high-frequency state aggregations (Governance) creates massive scaling risks if run on a monolithic pipeline.

## Decision
All 3 engines (Performance, Attribution, Governance) MUST be physically deployable as independent microservices/containers. They interact solely via asynchronous Event Bus integration.

## Consequences
Prevents compute exhaustion. Enables independent horizontal scaling. Enforces strict bounds where a crash in causal attribution does not break the calculation of objective basic performance facts.
