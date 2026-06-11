# MVP Delivery Readiness Review

## 1. MVP Goal Validation

**Goal:** Evaluate whether Sprints 1–3 are sufficient to support autonomous repository analysis, architecture review, code generation, revision, and verification for an external repository like `stock-bot`.

**Verdict:** Sprints 1, 2, and 3 are fundamentally **insufficient** to deliver autonomous implementation against an external repository. 

Sprints 1-3 are entirely focused on building the "Engine Block" (Cost Observability, FSM Durability, Cost Governance). While these guarantee Karsa operates safely, economically, and consistently, they do absolutely nothing to perform actual software engineering. After Sprint 3, Karsa will be an ultra-safe execution engine that possesses no built-in logic to clone `stock-bot`, read its AST, write a patch, or run `pytest`. 

---

## 2. Missing Runtime Capabilities

To successfully modify `stock-bot`, Karsa requires several runtime capabilities that are currently deferred to later sprints. These do not exist yet in either code or explicit architectural blueprints:

1. **Implementation Workflow**: The orchestrator that takes an approved architecture delta and converts it into a sequence of actionable Coder agent tasks.
2. **Artifact Generation Flow**: The specific prompt rules, context assembly, and validation gates required to instruct an LLM to generate an initial complete file or module.
3. **Patch Application Flow**: The critical capability to take an LLM-generated unified diff, map it to the target file in the sandbox, and strictly apply it without destroying existing source code.
4. **Verification Pipeline**: The sandbox executor that runs `pytest`, linters, and static analysis, captures the `stdout/stderr` streams, and feeds them directly back into the `REVIEW` state of the FSM.

---

## 3. Design vs Delivery Analysis

**Already Designed (Ready for Code):**
- Telemetry & Ledger (`ExecutionMetrics`, `WorkflowMetrics`)
- Governance & Budgets (`max_workflow_cost_usd`, Pre-flight estimates)
- Durability (`snapshot.json`, `events.jsonl`, Idempotency)
- Workflow State Machine (`IDEA` -> `APPROVED`)
- Evaluation Harness (Benchmark comparison foundation)

**Still Theoretical (High-level concepts defined, exact mechanics missing):**
- Patch-Based Revisions (We know we *want* diffs, but we haven't designed *how* the patch applicator handles fuzz/offsets).
- Review Delta Strategy (We know Reviewers should look at diffs, but haven't designed the prompt injection logic).
- Context Caching (We know we want it, but haven't mapped it to the specific API boundaries).

**Not Designed (Complete gaps):**
- External Repository Ingestion (How Karsa actually reads `stock-bot` AST/directory structure).
- CI/CD Sandbox Verification (How Karsa actually executes a test suite and parses the output).

---

## 4. Earliest Usable Version

Karsa becomes useful for real `stock-bot` development at **Sprint 13 (Verification Workflow)**.

- **Sprints 1-6** build the platform engine, governance, and prompt routing.
- **Sprints 7-9** optimize the token payload so generating code isn't prohibitively expensive.
- **Sprints 10-12** build the actual engineering workflows (Repository Analysis, Architecture, Implementation).
- **Sprint 13** implements Verification. 

Without Verification (Sprint 13), Karsa is merely a blind code generator. It must be able to run `stock-bot`'s tests in a sandbox to iteratively converge on a working solution.

---

## 5. Critical Path

The absolute shortest path from current architecture to *"Karsa can autonomously implement approved stock-bot changes"* requires completing the roadmap sequentially up to Verification:

1. **Build the Safe Engine**: Sprints 1, 2, 3 (Observability, FSM, Governance). *Without this, you bankrupt the project.*
2. **Build the Cheap Generator**: Sprints 5, 6, 7 (Prompt Builder, Caching, Patch Revision). *Without this, the context window explodes.*
3. **Build the Engineer**: Sprints 10, 11, 12 (Repo Analysis, Arch Delta, Implementation). *Without this, the LLM has no idea how to modify a codebase.*
4. **Build the Quality Gate**: Sprint 13 (Verification Workflow). *Without this, Karsa hallucinates broken code.*

---

## 6. Recommendation

**Continue Sprint 1 implementation immediately.**

**Justification:** While Karsa cannot modify `stock-bot` after Sprint 3, you cannot skip Sprints 1-3. Attempting to design or implement the "Patch Application Flow" or "Verification Pipeline" right now is premature optimization. If you build the Verification Pipeline first, an infinite review loop trying to fix a broken `pytest` will cost hundreds of dollars in unmonitored API calls. 

The engine block (Observability and Governance) MUST be built first. We are fully aware that Sprints 1-3 do not deliver autonomous software engineering; they deliver the **foundation** that makes autonomous software engineering economically viable. 

Proceed to coding Sprint 1.
