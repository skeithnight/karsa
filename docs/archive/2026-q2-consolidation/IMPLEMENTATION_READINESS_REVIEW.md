# Implementation Readiness Review

## 1. Executive Summary

This document serves as the final architectural audit of the Karsa platform design before implementation coding begins. The platform has evolved from a naive execution script into a highly governed, economically constrained, and mathematically measurable autonomous delivery system. 

While the architectural vision is exceptionally strong, this review has identified **three critical contradictions** and **four missing domain models** that would cause Sprints 1, 2, or 3 to fail. We are currently at a **NO-GO** status until these specific prerequisites are defined.

---

## 2. Architecture Consistency Review

The 11 approved artifacts represent a cohesive vision. The strict separation between Execution, Observability, Governance, and Benchmarking is sound. The upward flow of cost attribution and the downward enforcement of execution contracts form a robust defense against API bankruptcy.

However, the designs heavily focus on *what* will happen and *when* it will happen, but frequently abstract away *how* the data is passed between these completely isolated domains.

---

## 3. Contradiction Analysis

**Contradiction 1: The "Stateless" Utility vs. "Stateful" Forecaster**
* *The Conflict*: `COST_ESTIMATION_AND_PRE_EXECUTION_GOVERNANCE.md` states the Estimation Engine is a "stateless utility." However, `EXECUTION_CONTRACTS_AND_COST_FORECASTING.md` requires a Forecast Engine to project remaining cycles based on the `convergence_score` trend. To calculate a trend, the forecaster *must* be stateful or perform heavy I/O reads of past cycles on every pre-flight check.
* *Impact*: Sprint 3 (Cost Governance & Forecasting) will fail because the stateless engine cannot access the required historical convergence data without creating a massive circular dependency with the Observability ledger.

**Contradiction 2: Execution Definition Overlap**
* *The Conflict*: `EXECUTION_HIERARCHY.md` defines an Execution as "the lowest-level, atomic request/response interaction." However, `BENCHMARK_EXECUTION_BLUEPRINT.md` refers to "Execution (RUN)" as the entire sandbox lifecycle of passing a prompt and waiting for completion. 
* *Impact*: Developer confusion during Sprint 2. "Execution" is overloaded. We must rename the Benchmark phase to `EVALUATION_RUN` to protect the sanctity of the `Execution` entity class.

**Contradiction 3: Idempotency vs. Bound Execution Contracts**
* *The Conflict*: `WORKFLOW_DURABILITY.md` states the `idempotency_key` is a hash of `(prompt + model_config + execution_id)`. However, `EXECUTION_CONTRACTS.md` introduces an explicit SLA. If the SLA is modified (e.g., lower budget) but the prompt remains the same, does it yield a new idempotency key?
* *Impact*: Ghost executions might be incorrectly mapped if the contract is not part of the hash.

---

## 4. Missing Building Blocks

**1. Missing Domain Model: The Configuration Model**
* How does Karsa actually load the `max_workflow_cost_usd` limit? Is it a YAML file in the user's workspace? Global CLI environment variables? We have no `ConfigurationManager` architecture. Sprints 1 and 3 will fail without a defined place to read policy settings.

**2. Missing Persistence Model: The Pricing Registry Store**
* We defined the schema for the `PricingRegistry`, but where does it live? Is it hardcoded in Python? Downloaded dynamically from a Karsa server? If it's hardcoded, updating pricing requires a full CLI release.

**3. Missing Repository Abstractions**
* The `BENCHMARK_EXECUTION_BLUEPRINT.md` assumes the ability to clone Git SHAs into sandboxes. Karsa currently has a stub `git` directory, but no actual `WorkspaceManager` or `SandboxManager` architecture defined to handle ephemeral Git worktrees safely. Sprint 2 (Benchmark Harness) will fail.

**4. Missing Implementation Prerequisite: The Event Bus**
* `EXECUTION_HIERARCHY.md` states: "Aggregation occurs via an event-driven flow." Karsa currently has no Event Bus or Pub/Sub architecture. Agents cannot "emit" events asynchronously right now.

---

## 5. Sprint Readiness

### Sprint 1: Cost & Token Observability
* **Readiness**: **RED (Blocked)**
* **Missing**: `PricingRegistry` persistence strategy. `ConfigurationManager` to load the current active provider.

### Sprint 2: Workflow FSM, Durability & Bound Contracts
* **Readiness**: **RED (Blocked)**
* **Missing**: Definition of the `EventBus` to handle the transition emissions. Definition of how the FSM locks the `snapshot.json` file during concurrent file I/O.

### Sprint 3: Cost Governance & Forecasting
* **Readiness**: **RED (Blocked)**
* **Missing**: Resolution of the Stateless vs Stateful Forecaster contradiction. Definition of the global `GovernancePolicy` configuration schema.

---

## 6. Critical Risks (Hidden Complexity)

1. **The I/O Bottleneck**: By requiring synchronous `.jsonl` appends for events and `.json` overwrites for snapshots at every boundary, the Workflow Engine will spend a significant percentage of its time waiting on disk I/O. 
2. **The Test Evaluator Sandbox**: Executing arbitrary LLM-generated code in the `TestEvaluator` (Sprint 2) is a massive security risk if the sandbox is just a local directory. If an agent writes `os.system("rm -rf /")`, it destroys the host machine. We have no Docker/gVisor isolation architecture defined for the evaluator.

---

## 7. Dependency Graph & Fixes Before Coding

Before writing the first line of code for Sprint 1, the following foundational stubs must be designed:

```mermaid
graph TD
    A[ConfigurationManager (Policy & Secrets)] --> Sprint1
    B[PricingRegistry Storage Strategy] --> Sprint1
    C[EventBus Architecture] --> Sprint2
    D[Sandbox Isolation Strategy] --> Sprint2
    E[Stateful Forecaster Resolution] --> Sprint3
    
    Sprint1[Sprint 1: Observability] --> Sprint2[Sprint 2: FSM & Durability]
    Sprint2 --> Sprint3[Sprint 3: Governance]
```

### Recommended Fixes
1. **Define `karsa.toml`**: Create a global configuration schema mapping out where `max_workflow_cost_usd` is stored.
2. **Resolve Forecaster**: Explicitly design the Forecast Engine to perform an async read of the `review_cycle_metrics.json` to calculate the velocity curve, maintaining its statelessness relative to the core FSM memory.
3. **Rename Benchmark Run**: Rename the benchmark step to `BENCHMARK_RUN` to prevent overlapping with the `Execution` API class.
4. **Clarify Sandbox**: Explicitly state that for the initial benchmark harness, "Sandbox" means an isolated local Git worktree, accepting the security risk for v0.1, or mandate Docker.

---

## 8. Final Verdict

**NO-GO FOR IMPLEMENTATION.**

**Justification**: The architectural vision is excellent and mathematically sound. However, the lack of a basic Configuration Model, an Event Bus definition, and a Sandbox security policy guarantees that Sprints 1 and 2 will immediately stall on integration details. 

Once the 4 missing building blocks (Config, Pricing Store, Event Bus, Sandbox Strategy) are documented, the platform will be at a `GO` status for Sprint 1.
