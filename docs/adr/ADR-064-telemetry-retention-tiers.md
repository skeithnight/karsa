# ADR-064: Telemetry Retention Tiers

## Status
Accepted

## Context
The Observability Platform generates highly granular telemetry (100M+ events/day). Retaining this volume perpetually in hot PostgreSQL storage causes unbounded scaling degradation, violating the 10-year historical reconstruction mandate. Conversely, aggressive pruning deletes the capacity to replay.

## Decision
We establish a three-tier retention architecture based on event class:
1. **Business/Intent Events** (Thesis, Decision, Outcome, Performance, Attribution, Governance): These are NOT pruned. They persist eternally in the core Domain Ledgers. They are exempt from Observability's pruning.
2. **Hot Storage (PostgreSQL)**: Retains raw operational telemetry (Spans, Logs) for exactly 7 days to support live debugging and Sprint-51 Console queries.
3. **Cold Storage (S3/Parquet)**: At day 8, raw telemetry is batched, compressed into columnar Parquet files, and shifted to object storage for 10-year retention, allowing slow analytical replay if needed.
4. **Discard Tier**: Ephemeral metrics (e.g., Worker heartbeats) are aggressively pruned after 24 hours without cold storage migration, as they do not factor into historical business execution replays.

## Consequences
* 10-year replayability of core business logic is perfectly guaranteed.
* Postgres table sizes remain bounded and highly performant.
* Introduces complexity requiring daily archival chron jobs.
