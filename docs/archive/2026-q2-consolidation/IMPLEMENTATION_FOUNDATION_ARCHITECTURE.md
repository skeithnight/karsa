# Implementation Foundation Architecture

## 1. Configuration Architecture

To support Cost Governance and Provider Management without hardcoding, Karsa relies on a hierarchical configuration model resolving to a `karsa.toml` file.

### 1.1. Hierarchy & Overrides
Configuration is resolved in the following order of precedence (highest to lowest):
1. **Environment Variables**: E.g., `KARSA_MAX_WORKFLOW_COST_USD=2.00`.
2. **Repository Configuration**: `<repo>/.karsa/karsa.toml`.
3. **Global Configuration**: `~/.karsa/karsa.toml`.
4. **Hardcoded Defaults**: Defined in the Python codebase (e.g., fallback `max_review_cycles = 3`).

### 1.2. Policy Configuration
The `karsa.toml` introduces a `[governance]` block:
- `max_workflow_cost_usd`: Global kill-switch ceiling.
- `max_execution_cost_usd`: Per-call limit.
- `max_review_cycles`: Infinite loop prevention.

### 1.3. Provider Configuration
The `[providers]` block:
- Defines allowed models, routing preferences, and API key environment variable mappings.
- The `PricingRegistry` data (rates per 1M tokens) is persisted globally in `~/.karsa/pricing.json`. It acts as a local cache that can be manually or automatically updated without requiring a Karsa CLI release.

---

## 2. Event Bus Architecture

To support the requirement that "Aggregation occurs via an event-driven flow," Karsa implements a lightweight, synchronous, in-memory Event Bus.

### 2.1. Domain Events
Standardized Python dataclasses representing state changes. Examples:
- `ExecutionCompletedEvent` (carries token usage and exact USD cost).
- `StateTransitionEvent` (carries `IDEA` -> `DRAFT`).
- `ReviewCycleCompletedEvent`.

### 2.2. Event Publishing & Subscriptions
- **Publishing**: The `LLMClient` emits an `ExecutionCompletedEvent` directly to the `EventBus` singleton immediately after receiving an API response.
- **Subscriptions**: The `AgentMetrics`, `ReviewCycleMetrics`, and `WorkflowMetrics` aggregators register as listeners during startup.
- **Synchronous Execution**: To keep the MVP simple, event handlers execute synchronously on the main thread. If an aggregator throws an error, it crashes the workflow immediately, ensuring the ledger never falls out of sync with reality.

### 2.3. Event Persistence Strategy
- All events published to the bus are automatically serialized and appended to the workflow's `events.jsonl` file. This fulfills the Hybrid Persistence requirement (Event Sourcing + Snapshots) defined in the Durability Architecture.

---

## 3. Workspace Architecture

Karsa requires a clear boundary between global platform telemetry and repository-specific executions.

### 3.1. Global Workspace (`~/.karsa/`)
Owned by the Platform. Contains data that spans across multiple projects.
- `pricing.json`: The global Pricing Registry.
- `provider_registry.json`: Global API key tracking, quota failures, and usage.
- `benchmarks/`: Output from the Benchmark Harness (cross-repo comparative data).

### 3.2. Repository Workspace (`<repo>/.karsa/`)
Owned by the specific project/repository. Contains execution and state data for that specific codebase.
- `workflows/<workflow_id>/state.json`: The FSM durability snapshot.
- `workflows/<workflow_id>/events.jsonl`: The append-only event log.
- `executions/<execution_id>/`: Diagnostic forensics (`request.txt`, `response.txt`, `execution_metrics.json`).
- `metrics/`: Rolling aggregations (`workflow_metrics.json`, `review_cycle_metrics.json`).
- `cache/`: Context Cache storage (e.g., AST graphs, hashed file states).

---

## 4. Sandbox Architecture

The Benchmark Harness and Verification Workflow require executing LLM-generated code safely. The MVP approach relies on isolated local directories rather than heavy containerization.

### 4.1. Local Worktree Isolation
- When the `TestEvaluator` or `BenchmarkHarness` requires a clean environment, Karsa utilizes `git worktree add <temp_dir> <sha>`. 
- This guarantees a pristine, isolated copy of the repository without the massive I/O overhead of a full `git clone` or copying the `.git` directory.

### 4.2. Temporary Directories
- Sandboxes are strictly generated in the OS temporary directory (e.g., `/tmp/karsa_sandbox_<uuid>/`).
- Karsa operates entirely within this chroot-like mental model.

### 4.3. Cleanup Strategy
- The Sandbox Manager registers an `atexit` handler in Python.
- Regardless of whether the workflow succeeds, fails, or crashes (unless `SIGKILL` is sent), the `git worktree remove --force` command is executed, and the `/tmp` directory is wiped. This prevents disk bloat during heavy benchmark runs.
- *Security Note*: For MVP, we accept the risk of local execution. Karsa assumes it is running in an environment where the user trusts the LLM not to issue malicious host-level commands (`rm -rf /`).

---

## 5. Sprint Impact

These foundational architectures directly unblock the critical path:

- **Unblocks Sprint 1 (Cost & Token Observability)**: The `PricingRegistry` now has a home (`~/.karsa/pricing.json`), allowing the Cost Attribution Engine to perform math dynamically instead of relying on hardcoded rates.
- **Unblocks Sprint 2 (Workflow FSM & Durability)**: The in-memory `EventBus` provides the exact mechanism required to append `events.jsonl` and trigger synchronous metric aggregation without tightly coupling the Workflow Engine to the Ledger.
- **Unblocks Sprint 3 (Cost Governance)**: The `karsa.toml` Configuration Architecture allows Governance to actually read the `max_workflow_cost_usd` limit dynamically, rather than enforcing an arbitrary hardcoded limit. The `git worktree` Sandbox approach allows the Verification gate to run safely.

---

## 6. Final Readiness Verdict

**Verdict: GO.**

**Justification:**
All critical integration gaps identified in the readiness review have been closed. We have defined exactly *how* policy budgets are loaded, *where* pricing data lives, *how* metrics communicate synchronously via the Event Bus, and *how* the repository is safely isolated during execution. 

There are no remaining architectural ambiguities blocking the instantiation of the core engines. The platform design is complete, strictly governed, economically sound, and technically feasible for immediate implementation.
