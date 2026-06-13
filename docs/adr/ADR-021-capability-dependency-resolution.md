# ADR-021: Capability Dependency Resolution and Cycle Prevention

## Status
Approved

## Date
2026-06-14

## Context
Complex capabilities (such as composite task graphs or multi-agent workflows) may depend on other capabilities (e.g., a code-review capability depending on a code-diff capability).
To prevent stack overflows, infinite loops, and resolution deadlock at runtime:
1. We must define how capability dependencies are modeled and persisted.
2. We must validate and detect circular dependencies before a capability can be activated.
3. We must resolve dependency versions dynamically under defined semantic versioning constraints.

## Decision
We implement the following dependency resolution design:
1. **Aggregate Boundary**: Dependencies are modeled as a list of `CapabilityDependency` value objects nested inside the `CapabilityDefinition` aggregate root.
   - *Justification*: A capability's dependencies are intrinsic to its contract and have no lifecycle independent of the capability definition itself. This ensures that dependency updates increment the aggregate version, triggering OCC checks.
2. **Pinned Dependency Versioning**: During development (`DRAFT` state), capabilities can declare dependencies using version ranges (e.g. `^1.0.0`). However, when transitioning to the `REVIEW` state, the registry resolves the range to a specific compatible active version and pins it as an exact `dependency_id` (UUID). This guarantees absolute replay determinism.
3. **Cycle Prevention Algorithm**: During the capability transition from `DRAFT` to `REVIEW` (or activation), Karsa executes a validation service that checks the dependency graph. The service uses a **Depth-First Search (DFS) Node Coloring** cycle detection algorithm. If a back-edge is detected (indicating a loop), the validation fails, throwing a `DependencyCycleException` and blocking activation.
4. **Graph Projections**: Compilation of the execution DAG is decoupled from database reads. The registry builds a read-optimized **Dependency Graph Projection** to ensure high-performance, low-latency lookups.

## Consequences
- **Robust Execution**: Runtime execution is protected from infinite recursion and stack overflows caused by circular capability loops.
- **Strict Verification**: Capabilities can only be activated if all their dependencies exist in the registry and are active (or in review), ensuring graph completeness.
- **Dynamic Resolution Overhead**: Compiling the execution DAG has a performance cost. Resolved graphs must be cached at the routing layer.
