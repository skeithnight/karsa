# ADR-071: Portfolio CQRS Read Models and Event Bus Architecture

- **Status**: Proposed
- **Date**: 2026-06-16
- **Supersedes**: N/A
- **Superseded By**: N/A

## Executive Summary

The runtime audit exposed that Portfolio read models rely on volatile `InMemory` repositories, and that domain events are swallowed by a `MockEventBus`. Consequently, the API serves empty datasets and state is lost upon container restart. This ADR defines the minimum necessary architecture to restore runtime data flow from domain writes to persistent frontend read models, without violating established domain boundaries.

## Architecture Resolutions

### Review Area 1: Read Model Ownership
**Finding**: The `portfolio_states` table exists and is owned by `PostgresCIODecisionRepository`. It stores a raw JSON `portfolio_tree` as an orchestration projection representing the ex-ante portfolio state *after* a CIO decision, not the canonical read model for frontend exposure and valuation metrics.
**Decision**: **Option B. Introduce `portfolio_read_*` tables.**
**Rationale**: Reusing `portfolio_states` would tightly couple the Portfolio Bounded Context to the CIO Bounded Context and force the API to parse raw orchestration trees. The canonical read model requires its own `portfolio_read_valuations` and `portfolio_read_positions` tables owned strictly by the Portfolio domain.

### Review Area 2: Event Replay Source
**Finding**: The system currently uses an outbox table (`outbox_records`) but **no event store exists**.
**Decision**: Events **cannot** be replayed today (Option B).
**Rationale**: `outbox_records` is a transactional queue designed to dispatch messages and mark them as `published_status = true`. It lacks a strict, gapless sequence number required for deterministic Event Sourcing replays. To support projection rebuilds, a dedicated `event_journal` table (Append-Only Event Store) with a global sequence must be introduced alongside the Outbox.

### Review Area 3: Worker Topology
**Recommendation**: **Option B (karsa-api + karsa-projection-worker)**
**Rationale**: Isolating the projection worker into a separate container (`karsa-projection-worker`) ensures that a heavy projection rebuild (replaying millions of events) or a bad event crash does not degrade or halt the `karsa-api` HTTP server.

### Review Area 4: Checkpoint Design
**Ownership**: Projection Engine (Read Side)
**Storage**: `projection_checkpoints` table in PostgreSQL.
**Recovery Behavior**: If a worker crashes during `REBUILDING` or `RUNNING`, the replacement worker reads the last `last_processed_sequence` from the checkpoint and resumes from that sequence in the `event_journal`.
**State Diagram**:
`Not Started` -> `Rebuilding` -> `Running` -> `Checkpoint Saved` -> `Running`
`Running` -> `Failed` (Requires manual intervention or automatic backoff)

### Review Area 5: Seeding Strategy Validation
**Finding**: Directly invoking `PortfolioProjectionService.consume_order_filled()` bypasses the Domain Flow (CIO -> Execution -> Portfolio).
**Decision**: The canonical seed entrypoint must be **Decisions**.
**Rationale**: The seed script must invoke `CioApplicationService.create_decision()`, which generates Target Snapshots, generating Execution Orders, leading to `FillService.record_fill()`, which finally emits `OrderFilledEvent` for the Projection to consume. No shortcuts allowed.

### Review Area 6: CQRS Ownership Diagram
**Write Side**:
- **Aggregate**: CIO Decision / Portfolio Target
- **Repository**: `PostgresCIODecisionRepository`
- **Event Source**: Outbox -> `event_journal`
**Read Side**:
- **Projection**: `PortfolioProjectionWorker`
- **Read Repository**: `PostgresValuationRepository` (Reads from `portfolio_read_valuations`)
- **API**: `PortfolioAPI`
This guarantees the API never touches the Write repositories directly.

### Review Area 7: Local-Production Fit Analysis
**Target Environment**: Docker Compose, Single PostgreSQL, Mini PC.
**Recommendation**: A PostgreSQL Outbox + `event_journal` paired with a separate `karsa-projection-worker` container.
**Rationale**: Kafka and RabbitMQ are unjustified for a Mini PC due to high memory overhead. PostgreSQL can easily handle transactional outbox polling at a small scale. A dedicated projection worker container is justified to prevent API latency spikes during projection catch-up.
