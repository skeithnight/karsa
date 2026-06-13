# ADR-018: Provider Identity, Registry, and Lifecycle Governance

## Status
Approved

## Date
2026-06-14

## Context
Karsa needs to integrate multiple Large Language Model (LLM) backends (e.g. OpenAI, Anthropic, Gemini, Ollama) without coupling the core Capability Engine to their proprietary APIs.
To achieve this:
1. We must uniquely identify providers and models.
2. We must map which provider supports which capability and with what compatibility level.
3. We must govern the lifecycle of these integrations to ensure that broken, degraded, or unsafe provider configurations do not disrupt live workflow executions.

## Decision
We implement a unified Provider Registry with the following design choices:
1. **Dual Provider Identity Format**: Establish a standardized identity structure consisting of:
   - `provider_id`: A system-generated, immutable UUIDv4 assigned upon initial registration. This is the primary key in cost metrics, tracing, and event streams.
   - `provider_urn`: A user-friendly, namespaced string (`urn:karsa:provider:{vendor}:{model}:{version}`) used for dynamic lookup and routing references.
2. **Aggregate Boundary Separation**: To prevent database write amplification and concurrency conflicts, the fast-updating health metrics are extracted from `ProviderDefinition`. We define two distinct aggregates:
   - `ProviderDefinition`: Holds stable provider configurations, capability mappings, and pricing values.
   - `ProviderHealthState`: Holds fast-updating latency, failure counts, and outage flags, updated asynchronously by the telemetry service.
3. **Provider Lifecycle States**: The registry manages provider configurations using a formal finite state machine (FSM) containing:
   - `DRAFT`: Initial configuration.
   - `REVIEW`: Awaiting security and capability compatibility audit.
   - `ACTIVE`: Available for live execution routing.
   - `DEGRADED`: Encountering temporary latency or rate-limiting issues; routed to as fallback only.
   - `SUSPENDED`: Temporarily disabled due to security breaches or consecutive system failures.
   - `DEPRECATED`: Allowed for ongoing, running workflows but blocked for new execution registrations.
   - `RETIRED`: Permanently disabled.
4. **Single-Writer Mapping Governance**: The Provider Registry is the single writer for all capability-to-provider mappings. It reads from the Capability Registry to validate capability URN availability during mapping updates.

## Consequences
- **Loose Coupling**: The Capability Engine executes capabilities through the registry, removing vendor dependencies from the core codebase.
- **Enhanced Safety**: Provider states (e.g., `SUSPENDED` or `DEPRECATED`) are enforced globally, preventing executions on failed or insecure models.
- **Immutability of Mappings**: Active capability mappings are frozen. Any updates to mapping configurations or pricing models require a version increment or a new draft configuration to ensure historical trace consistency.
- **High Concurrency performance**: Isolating stable metadata from fast-changing health states prevents transaction contention and aggregate lockouts.
