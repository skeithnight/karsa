# Worker Extension Contract

## Context
The Karsa backend operates an asynchronous event-projection mechanism hosted inside `src/karsa/projection_worker.py`. This worker polls the `event_journal` to hydrate Read Models.

## Existing Architecture
*   **Event Storage**: `EventJournalRepository` handles sequence generation.
*   **Checkpoints**: `ProjectionCheckpointRepository` locks and tracks projection offsets.
*   **Routing**: Raw `if/elif` statements mapping event strings to Service methods.
*   **Projections**: Bound to standard Postgres tables.

## Extension Strategy
To integrate the 4 new Validation Platform events, we will strictly **EXTEND** the existing worker logic without introducing secondary workers or kafka queues.

### AlphaDecomposedEvent
*   **Handler**: `TrustProjectionService.consume_alpha_decomposed`
*   **Projection Target**: `TrustContext` snapshot.

### ForecastResolvedEvent
*   **Handler**: `ReviewProjectionService.consume_forecast_resolved`
*   **Projection Target**: Brier Score read model.

### CapabilityGradedEvent
*   **Handler**: `TrustProjectionService.consume_capability_graded`
*   **Projection Target**: `TrustVector` recalculation cache.

### TrustSuppressedEvent
*   **Handler**: `FirmHealthProjectionService.consume_trust_suppressed`
*   **Projection Target**: Firm Health decay metrics TSDB.

## Implementation Standard
Developers will append `elif event_type == "..."` into the primary loop inside `process_events()`, instantiate the required repositories prior to the loop, and inject them into the new Services.
