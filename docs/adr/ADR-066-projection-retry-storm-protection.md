# ADR-066: Projection Retry Storm Protection

## Status
Accepted

## Context
If upstream queues experience a failure triggering a 10-million message DLQ/Retry storm, synchronous projection updates within the Observability Platform will exhaust connection pools, cascading the outage.

## Decision
All Observability Projections must implement **Debounced Batching**.
* Instead of upserting `QueueState` on every event, the Projection Worker accumulates events in-memory.
* Flushes to the database occur either every N seconds (e.g., 5s) or after M events (e.g., 1000).
* Backpressure is implemented by deliberately halting the read off the telemetry bus if the flush latency exceeds SLA, allowing the bus (Kafka/Rabbit) to buffer the storm rather than the database.

## Consequences
* Observability remains `FAIL-OPEN` and structurally incapable of triggering a database outage via connection exhaustion.
* Operational snapshots will experience sub-second eventual consistency lag during extreme storms.
