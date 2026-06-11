# Core Domain Model Architecture

## 1. Domain Model Catalog

This catalog explicitly defines the canonical domain objects that will be implemented as native Python dataclasses/models during Sprint 1.

- **`Workflow`**: The primary entity representing a single, end-to-end task from `IDEA` to termination.
- **`WorkflowState`**: An Enum representing the FSM state (`IDEA`, `DRAFT`, `REVIEW`, `REVISE`, `APPROVED`, `FAILED`, `ABORTED`).
- **`WorkflowMetrics`**: The global ledger tracking `total_cost`, `total_tokens`, and `total_duration_ms` for the workflow.
- **`ReviewCycle`**: Represents a single iteration loop. Contains specific findings, open issues, and the target convergence score.
- **`ReviewCycleMetrics`**: The localized ledger tracking cost and tokens explicitly consumed within one cycle.
- **`Agent`**: A logical persona (e.g., Coder, Reviewer) loaded with specific prompt contexts and tool access schemas.
- **`AgentMetrics`**: A rolling aggregator tracking total historical cost and tokens consumed by a specific agent persona across the workflow.
- **`Execution`**: The atomic network interaction payload containing the prompt, configuration, and `idempotency_key`.
- **`ExecutionMetrics`**: The immutable post-execution telemetry containing exact input/output tokens, calculated USD cost, and duration.
- **`GovernancePolicy`**: The loaded configuration rules defining `max_workflow_cost_usd`, `max_review_cycles`, and `max_tokens_per_execution`.
- **`ExecutionContract`**: The proactive SLA defined by the Agent before dispatch, dictating `execution_budget_usd` and `max_output_tokens`.
- **`PricingRegistryEntry`**: The financial schema containing `base_input_rate`, `base_output_rate`, `reasoning_output_rate`, etc., for a specific model ID.
- **`CostEstimate`**: The output of the Pre-flight Estimation Engine, returning projected `pessimistic_cost` and `confidence_level`.
- **`ForecastResult`**: The output of the Forecasting Engine, containing `projected_remaining_cost`, `projected_remaining_cycles`, and `forecast_confidence`.

---

## 2. Ownership Boundaries

| Domain Object | Responsibility | Lifecycle | Persistence Location |
|---|---|---|---|
| `Workflow` | Orchestrates FSM progression. | `IDEA` to Termination | `<repo>/.karsa/workflows/<id>/state.json` |
| `GovernancePolicy` | Enforces global bounds. | Boot to Shutdown | `~/.karsa/karsa.toml` & `<repo>/.karsa/karsa.toml` |
| `PricingRegistryEntry` | Translates tokens to USD. | Boot to Shutdown | `~/.karsa/pricing.json` |
| `ReviewCycle` | Tracks convergence progress. | Transition from DRAFT/REVISE | Bound to `Workflow` snapshot |
| `Agent` | Formats prompts; dictates contracts. | Ephemeral per task | Bound to `Workflow` snapshot |
| `ExecutionContract` | Binds execution to a strict limit. | Pre-flight to Execution end | Volatile (In-Memory) |
| `Execution` | Executes network requests. | Dispatch to Response | `<repo>/.karsa/executions/<id>/request.txt` |
| `ExecutionMetrics` | Records atomic transaction cost. | Immutable post-response | `<repo>/.karsa/executions/<id>/execution_metrics.json` |
| `WorkflowMetrics` | Global economic ledger. | Follows Workflow lifecycle | `<repo>/.karsa/metrics/workflow_metrics.json` |
| `CostEstimate` | Flags pre-flight risk. | Ephemeral | Volatile (In-Memory) |
| `ForecastResult` | Flags terminal trajectory risk. | Ephemeral | Volatile (In-Memory) |

---

## 3. Aggregate Roots

The domain is strictly hierarchical. Aggregation operations and persistence boundaries follow this root tree:

```text
Workflow (Aggregate Root)
 ├─ WorkflowState
 ├─ WorkflowMetrics
 └─ ReviewCycle
      ├─ ReviewCycleMetrics
      └─ Agent
           ├─ AgentMetrics
           └─ Execution
                ├─ ExecutionContract
                ├─ CostEstimate
                └─ ExecutionMetrics
```
- The `Workflow` is the ultimate Aggregate Root. All file-system operations representing the state of the system operate at this level (e.g., saving `snapshot.json` captures the entire tree).
- `PricingRegistryEntry` and `GovernancePolicy` are isolated Singleton Domain Services injected at runtime, not children of the Workflow.

---

## 4. Event Mapping

State transitions and data roll-ups occur via the Event Bus passing immutable Domain Events:

- **`ExecutionCompletedEvent`**: 
  - *Triggered by*: LLMClient after receiving API response.
  - *Carries*: `ExecutionMetrics`.
  - *Updates*: `AgentMetrics`, `ReviewCycleMetrics`, `WorkflowMetrics`.
- **`StateTransitionEvent`**: 
  - *Triggered by*: Workflow Engine upon advancing the FSM.
  - *Carries*: Old `WorkflowState`, New `WorkflowState`.
  - *Updates*: Appended to `events.jsonl`, triggers `snapshot.json` write.
- **`ReviewCycleCompletedEvent`**: 
  - *Triggered by*: End of `REVIEW` phase.
  - *Carries*: `ReviewCycleMetrics`, `convergence_score`.
  - *Updates*: Appended to `events.jsonl`, triggers Forecast Engine trajectory check.
- **`WorkflowCompletedEvent`**: 
  - *Triggered by*: Transition to `APPROVED`, `FAILED`, or `ABORTED`.
  - *Carries*: Final `WorkflowMetrics`.
  - *Updates*: Halts execution loop, writes final snapshot, wipes active memory.

---

## 5. Persistence Mapping

Every persistent domain object maps to a specific file on disk to guarantee durability and O(1) reads for CLI tools:

1. **`snapshot.json`**: Serializes `Workflow`, `WorkflowState`, active `ReviewCycle`, and active `Agent`. Written synchronously at recovery checkpoints.
2. **`events.jsonl`**: Serializes all Domain Events (`ExecutionCompletedEvent`, `StateTransitionEvent`). Written synchronously on publish.
3. **`metrics/*.json`**: Serializes `WorkflowMetrics`, `ReviewCycleMetrics`, and `AgentMetrics`. Updated incrementally.
4. **`executions/<id>/`**: Stores the raw string payload of the `Execution` prompt (`request.txt`) and response (`response.txt`), along with the immutable `ExecutionMetrics` JSON.

---

## 6. Sandbox Evolution Note

Karsa executes LLM-generated code during verification. The architecture guarantees a migration path to full untrusted execution without rewriting the workflow engine.

- **Trusted Mode (MVP Phase)**:
  - *Mechanism*: `git worktree add <tmp_dir>`.
  - *Assumption*: The user trusts the agent not to write `rm -rf /` or leak host environment variables.
  - *Use Case*: Fast, local iteration during Sprint 1-10 development.

- **Future Untrusted Mode (Production Release)**:
  - *Mechanism*: The Sandbox Manager interface implements a `DockerSandbox` provider.
  - *Migration Path*: The workflow engine passes the `git worktree` path to the Docker daemon as a mounted volume, executing the `Verification Workflow` inside a zero-network, unprivileged container. 
  - *Status*: Docker is strictly deferred. The interface must abstract the execution context so Docker can be swapped in natively later.

---

## 7. Sprint 1 Impact

Before Sprint 1 coding can commence, the developer must instantiate the specific Python interfaces (or type definitions) for:
1. `ExecutionMetrics` (Data carrier).
2. `PricingRegistryEntry` (Cost lookup).
3. `CostEstimate` (Pre-flight math).
4. `GovernancePolicy` (The kill-switch limits).
5. `EventBus` (The pub/sub broker interface).

By defining these classes exactly as outlined in the Domain Catalog, Sprint 1 (Cost & Token Observability) will immediately integrate cleanly into Sprint 2 (FSM & Durability) and Sprint 3 (Governance) without architectural refactoring.

---

## 8. Final Readiness Verdict

**Verdict: GO.**

**Justification:**
All domain objects, boundaries, event flows, and file-system mappings have been explicitly cataloged. The "Execution" naming contradiction is fully resolved via the hierarchical definition. The persistence strategy defines exactly what goes into memory, what goes into JSON, and what goes into the append-only log. 

The software architecture is now fully specified. Karsa is ready for Sprint 1 implementation.
