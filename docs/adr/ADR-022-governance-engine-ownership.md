# ADR-022: Governance Engine Ownership and Context Boundaries

## Status
Approved

## Date
2026-06-14

## Context
Karsa needs a centralized policy framework to enforce compliance, transaction safety, loss control, and budget caps across capability executions, registry activities, and multi-agent coordination.

To maintain strict domain boundaries:
1. We must isolate policy configurations from core execution states.
2. We must ensure that policy definitions and execution outcomes are audit-traceable.
3. We must obey the single-writer principle: no other bounded context may mutate policies or governance decisions.
4. Consecutive execution requests must not block on database writes due to synchronous cryptographic audit chains.
5. Suspension and revocation status writing must not lead to split ownership.

## Decision
We establish the **Governance Engine** as a dedicated bounded context with complete ownership of policies, evaluations, decisions, and compliance audit logging:

1. **PolicyDefinition Ownership**: The Governance Engine is the single writer for `PolicyDefinition` aggregates.
2. **GovernanceDecision Aggregate Root (Layer A)**: Persisted atomically upon evaluation to block executions immediately. It commits the decision first and publishes `GovernanceDecisionCreatedEvent`.
3. **Asynchronous GovernanceAuditChain (Layer B)**: Audit logs are chained via SHA-256 hashes asynchronously by a background audit worker. Hashing operations are removed from the critical runtime write path, resolving sequential lock contention.
4. **Suspension & Revocation Requests**: The Governance Engine does not directly mutate Capability or Provider aggregate states. It publishes `SuspensionRequest` or `RevocationRequest` events. The target registry FSM consumes these events and remains the sole writer of its aggregate state.

## Consequences
- **High Concurrency**: Extracting Layer B hashing to a background worker eliminates thread locks on concurrent capability invocations.
- **Strict Single-Writer Pattern**: Resolves aggregate boundary leaks. Target registries own all local state transitions, complying with DDD guidelines.
