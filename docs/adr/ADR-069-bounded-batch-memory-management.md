# ADR-069: Bounded Batch Memory Management

## Status
Accepted

## Context
During a 10M+ message DLQ/Retry storm, unrestrained in-memory buffering (ADR-066) will cause the Observability workers to exceed the 8GB-16GB RAM limits of a Lenovo Tiny node, resulting in catastrophic OOM crashing.

## Decision
We enforce rigid **Bounded Batching**:
* Maximum batch size: `5,000` events.
* Maximum memory budget per worker: `256MB` hard-limit.
* Maximum flush interval: `5.0` seconds.

If the 5,000 event limit or 256MB limit is hit before the 5.0 second interval, the batch flushes immediately. If the database cannot keep up, the worker blocks the bus poll, propagating backpressure natively without allocating further memory.

## Consequences
* Mathematical guarantee against OOM crashes during arbitrary event storms.
* Ingestion latency temporarily increases during storms, but memory stability is absolutely preserved.
