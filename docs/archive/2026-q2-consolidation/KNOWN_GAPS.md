# Known Gaps

The following are explicit deviations between the Sprint 1 implementation and the architectural blueprints (`CORE_DOMAIN_MODEL_ARCHITECTURE.md`, `IMPLEMENTATION_FOUNDATION_ARCHITECTURE.md`, `EXECUTION_HIERARCHY.md`):

1. **`execution_metrics.json` File Missing**: 
   - *Architecture*: `EXECUTION_HIERARCHY.md` states "ExecutionMetrics: Immutable JSON object written to `.karsa/executions/<id>/execution_metrics.json`."
   - *Implementation*: The `ObservabilityManager` merges the metrics directly into `.karsa/executions/<id>/metadata.json` and never creates the independent metrics file.

2. **Unpopulated `ReviewCycleMetrics`**:
   - *Architecture*: `ReviewCycleMetrics` is a core ledger entity.
   - *Implementation*: The `MetricsAggregator` creates `review_cycle_metrics.json` as an empty `{}` file but never populates it. The `ExecutionCompletedEvent` does not carry a `review_cycle_id`, making aggregation impossible.

3. **EventBus Fragility**:
   - *Architecture*: `IMPLEMENTATION_FOUNDATION_ARCHITECTURE.md` calls for an EventBus that synchronously updates ledgers.
   - *Implementation*: The EventBus has zero error handling. A file permission error while updating `agent_metrics.json` will crash the entire workflow execution.

4. **Heuristic Tokenization**:
   - *Architecture*: The Tokenizer plugin is meant to provide accurate math for the Pricing Registry.
   - *Implementation*: `TokenUsageCollector` uses `len(text) // 4`. This is mathematically unsafe for code context and will lead to completely inaccurate USD reporting.

5. **Pricing Registry Persistence Boundary**:
   - *Architecture*: `IMPLEMENTATION_FOUNDATION_ARCHITECTURE.md` states the Pricing Registry is stored at `~/.karsa/pricing.json`.
   - *Implementation*: The `ObservabilityManager` attempts to lookup `pricing.json` via `Path.home() / ".karsa" / "pricing.json"`. In tests or CI environments, this pollutes the user's home directory instead of isolating to the project or respecting environment overrides.
