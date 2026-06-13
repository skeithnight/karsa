# ADR-016: Capability Identity and Registration Governance

## Status
Approved

## Date
2026-06-14

## Context
In Karsa, capabilities represent execution primitives (e.g., LLM inference, shell execution, AST scanning). The lack of a unified representation of capabilities as first-class objects creates several risks:
1. Namespace collisions between standard and custom tools.
2. Code injections where agents register raw commands or insecure code without validation.
3. Inability to track who owns and manages a capability.
4. Loss of execution history when capability definitions shift over time.

We need a standardized identity and lifecycle model for all capabilities.

## Decision
We establish the following architecture for Capability Identity and Registration:
1. **URN-Based Identity**: All capabilities are uniquely identified by a structured URN: `urn:karsa:capability:{namespace}:{name}:{version}`.
   - Example: `urn:karsa:capability:core:docker-execution:v1.0.0`
   - Example: `urn:karsa:capability:provider:gemini-chat:v2.1.0`
2. **First-Class Aggregates**: Capabilities are modeled as a bounded aggregate root (`CapabilityDefinition`) containing ownership metadata, semantic versioning, and lifecycle states.
3. **Registration Governance Gate**: Registering a capability is restricted to the Control Plane. A capability begins as `DRAFT` and must transition through `REGISTERED` to `ACTIVE`. The transition to `ACTIVE` is intercepted by the `GovernanceService` to verify that the execution contract and resource boundaries comply with system safety policies (e.g., AST limitations, resource limits).
4. **Explicit Ownership**: Every capability has a designated `CapabilityOwner` value object containing the owner ID and type (`SYSTEM`, `AGENT`, or `PARTNER`), enforcing accountability.

## Consequences
- **Safety**: Unverified capabilities cannot execute, as the engine rejects any execution request for a capability not in the `ACTIVE` state.
- **Traceability**: All execution traces can reference an immutable capability URN, ensuring historical reproducibility.
- **Overhead**: Introducing a registration gate adds a small upfront registration step for custom tools or agents, but this is a critical trade-off for system safety.
