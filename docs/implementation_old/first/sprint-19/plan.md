# Sprint-19 Provider Abstraction Foundation Plan

## 1. Context & Scope
Following the frozen architecture of Sprint-17, Sprint-19 executes the physical implementation of the **Provider Abstraction Foundation**.
Objectives:
- Decouple logical capabilities from physical LLM backends (OpenAI, Gemini, Anthropic, Ollama, etc.).
- Isolate configuration updates from fast-updating health telemetry.
- Enforce namespaced URN identities alongside system UUID keys.
- Establish dynamic candidate routing, in-memory replay bypass, and failover budget re-evaluation.
- Provide mock adapters and repository implementations. No real API vendor clients are integrated.

## 2. Objectives
- Domain Layer: Implement `ProviderDefinition` and `ProviderHealthState` aggregates, value objects (`ProviderURN`, `ProviderPricing`, `CapabilityRequirement`, `ProviderRoutingDecision`), and mapping entity `ProviderCapabilityMapping`.
- FSM Lifecycle: Implement state transition rules (`DRAFT` -> `REVIEW` -> `ACTIVE` -> `DEGRADED`/`SUSPENDED`/`DEPRECATED`/`RETIRED`).
- Application Services: Implement `ProviderRegistryService` (writes configurations only), `ProviderTelemetryService` (writes health metrics only), and `ProviderRoutingService` (calculates candidate routing and handles replay).
- Repositories: Implement `InMemory` and `File` persistence layers with Optimistic Concurrency Control (OCC) guards.
- Mocks & Adapters: Build `BaseProviderAdapter`, `MockProviderAdapter`, and the `AdapterRegistry`.

## 3. Architecture Alignment
The implementation conforms to:
- [08-provider-abstraction.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/08-provider-abstraction.md)
- [ADR-018: Provider Identity, Registry, and Lifecycle Governance](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-018-provider-registry-lifecycle.md)
- [ADR-019: Provider Routing, Failover, Telemetry, and Cost Tracking](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/adr/ADR-019-provider-routing-telemetry-cost.md)

## 4. Work Packages
- **WP-19.1**: Domain aggregates, entities, value objects, and FSM.
- **WP-19.2**: Registry, Telemetry, and Routing services.
- **WP-19.3**: InMemory and File repositories with OCC checks.
- **WP-19.4**: Adapter registry and mock client implementation.
- **WP-19.5**: Testing, audit, and remediation.
