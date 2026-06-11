# Roadmap Revalidation

## 1. Objective

This document re-evaluates the canonical 15-Sprint roadmap defined in the `walkthrough.md` based on the newly introduced architectural artifacts:
- `WORKFLOW_STATE_MACHINE.md`
- `FAILURE_TAXONOMY.md`
- `SUCCESS_CRITERIA.md`

## 2. Challenging the Roadmap Assumptions

### Assumption 1: The Workflow Engine Already Exists
* **Challenge**: The current `walkthrough.md` assumes the Workflow Engine is mature enough to be governed. However, the `WORKFLOW_STATE_MACHINE.md` introduces strict, non-terminal and terminal states (`IDEA`, `DRAFT`, `REVIEW`, `REVISE`, `APPROVED`, `FAILED`, `ABORTED`) with hard entry/exit conditions that the current MVP code does not structurally enforce.
* **Conclusion**: We cannot attach a Governance Engine (Sprint 3) to a Workflow Engine that lacks a strict FSM representation. 

### Assumption 2: Cost Governance Can Precede FSM Refactor
* **Challenge**: The Governance Engine relies on intercepting state transitions (e.g., preventing a transition from `REVISE` to `REVIEW` if `max_review_cycles` is breached). If the underlying code does not emit explicit state transition events, Governance has nothing to intercept.
* **Conclusion**: The sprint ordering is flawed. The FSM must be implemented before or alongside Governance.

### Assumption 3: Benchmark Harness Can Evaluate Current MVP
* **Challenge**: The `SUCCESS_CRITERIA.md` mandates that "Success" at the Workflow Level strictly requires `cost < max_workflow_cost_usd`. If we run the Benchmark Harness (Sprint 2) before we build Cost Governance (Sprint 3), the benchmark results will be invalid because Karsa has no defense against infinite loops, artificially inflating its cost during complex tests.
* **Conclusion**: The Benchmark Harness must run *after* Cost Governance is active.

## 3. Revised Sprint Ordering

Based on this evidence, the immediate Sprints must be re-ordered.

**Old Order:**
Sprint 1: Observability
Sprint 2: Benchmark Harness
Sprint 3: Cost Governance
Sprint 4: Model Routing

**New Recommended Order:**
- **Sprint 1: Cost & Token Observability** (Unchanged - Prerequisite for all math).
- **Sprint 2: Workflow FSM & Failure Taxonomy** (NEW - We must refactor the MVP workflow loop to explicitly emit states like `REVIEW` and handle failures).
- **Sprint 3: Cost Governance** (Moved - Hooks into the FSM to enforce budgets and cycle limits).
- **Sprint 4: Benchmark Harness** (Moved - Now we can safely benchmark Karsa without fear of infinite loop bankruptcies).
- **Sprint 5: Model Routing** (Unchanged).

## 4. Final Recommendation

The introduction of the `FAILURE_TAXONOMY` and `WORKFLOW_STATE_MACHINE` reveals that the current `src/karsa/` codebase is a prototype script, not a governed platform. 

The immediate next step remains **Sprint 1: Cost & Token Observability**. However, **Sprint 2** MUST be the refactoring of the Karsa execution loop into the strict State Machine. Without the State Machine, Governance is impossible, and without Governance, Benchmarking is dangerous.
