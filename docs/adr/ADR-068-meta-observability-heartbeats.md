# ADR-068: Meta-Observability Heartbeats

## Status
Accepted

## Context
If the Observability Platform's ingestion workers crash silently, the UI dashboards will display stagnant data, generating false-negative "System Healthy" assumptions.

## Decision
We introduce "Meta-Observability". 
The Observability Platform must emit its own internal telemetry:
* `IngestionHealth`: Measures bus read lag.
* `ProjectionHealth`: Measures time delta between `event.created_at` and `snapshot.updated_at`.
A dedicated lightweight Meta-Worker runs independently of the main ingestion pool. If the main ingestion lag exceeds 5 minutes, it triggers a catastrophic paging alert natively, bypassing standard routing.

## Consequences
* Prevents silent observability failures.
* Increases structural complexity by requiring a secondary meta-monitoring loop.
