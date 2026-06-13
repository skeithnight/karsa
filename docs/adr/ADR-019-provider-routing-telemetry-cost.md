# ADR-019: Provider Routing, Failover, Telemetry, and Cost Tracking

## Status
Approved

## Date
2026-06-14

## Context
Executing capabilities requires selecting the best provider based on dynamic constraints like cost, speed, data residency, and capability compatibility. Furthermore:
1. Third-party APIs are unreliable, experiencing timeouts, rate-limiting, and temporary outages.
2. Capability execution cost must be tracked in real-time, matching token usage to financial models.
3. Telemetry ownership must be clear, logging trace events without violating data privacy or bloating persistence stores.

## Decision
We establish the following routing, failover, and telemetry designs:
1. **Dynamic Routing Engine**: The Capability Engine queries a `ProviderRoutingService` to resolve a capability request to a `ProviderRoutingDecision`. Selection is guided by a `RoutingPolicy` (e.g. `LOWEST_COST`, `LOWEST_LATENCY`, `HIGH_ACCURACY`).
2. **Replay Determinism**: During replays, the `ProviderRoutingService` is bypassed. The system rehydrates the exact historical output matching the `execution_id` from the `EvidenceRegistry` without dispatching physical API requests.
3. **Attributed Cost Ownership**: The **Attribution Engine** owns and maintains all financial and token cost records. The `ProviderRegistry` defines the model rates, and the `ProviderTelemetry` context extracts token usage from API responses. Cost is hierarchically attributed across `WorkflowExecution`, `CapabilityExecution`, and `ProviderDefinition` dimensions.
4. **Governance-Re-evaluated Failover**: Automated failovers cascade to the next fallback candidate only after re-evaluating the candidate against the remaining execution budget (`Total_Workflow_Budget - Accumulated_Workflow_Cost`). Any fallback provider exceeding the remaining budget triggers an immediate execution block.
5. **Multi-Dimensional Compatibility Evaluation**: Provider mapping compatibility checks evaluate concrete model feature flags (`json_mode`, `tool_calling`, `streaming`, `min_context_window`, `structured_output`, `reasoning_support`) against the capability's contract requirements.

## Consequences
- **High Availability**: Outages or rate-limit violations trigger immediate failover to the next fallback provider, improving workflow resilience.
- **Strict Budget Control**: Every failover step enforces budget limits, preventing runaway LLM costs by denying executions that exceed token or financial budgets before they reach third-party APIs.
- **Trace Auditing**: Standardized telemetry allows detailed execution dashboard rendering and optimization analysis.
- **Perfect Replay Reproducibility**: Bypassing routing during replays ensures that changes in model prices or health states do not alter historical trace trajectories.
