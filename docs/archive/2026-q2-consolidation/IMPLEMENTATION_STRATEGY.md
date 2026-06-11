# Karsa — Implementation Strategy

> *"The best part is no part. The best process is no process. It weighs nothing. Costs nothing. Can't go wrong."*

**Document Status:** Approved Implementation Plan
**Date:** 2026-06-11
**Objective:** Define the lowest-effort, highest-probability engineering strategy to build Karsa MVP and ship Research Vault v0.1.

---

## 1. Build vs Buy Analysis

To implement the Founder + Maker (Product Engineer) + Checker (Review Agent) model, we must choose an orchestration layer.

### Option A: Build from Scratch (OpenAI SDK / Anthropic SDK)
* **Complexity:** Medium
* **Flexibility:** Maximum
* **Development effort:** High (Requires building state management, artifact parsing, and agent messaging from zero).
* **Maintainability:** High (Total ownership of the code).

### Option B: Fork an Existing Framework
* **MetaGPT:** Opinionated software company simulation. Highly aligned in spirit, but heavy.
* **LangGraph:** Unopinionated state-machine framework. Highly flexible, but requires building the agent personas from scratch.
* **CrewAI / AutoGen:** General-purpose agent orchestrators. Often suffer from "chat-loop" hallucinations without strict constraints.
* **PydanticAI:** Excellent for structured output, but lacks out-of-the-box multi-agent workflow orchestration.

### Recommendation: Fork and Amputate
**Fork MetaGPT** (or use LangGraph as a strict fallback if MetaGPT is too rigid). MetaGPT is already designed to output software projects and markdown artifacts. We will buy the framework, but we will aggressively strip it down.

---

## 2. MetaGPT Evaluation

MetaGPT was built on the premise of simulating a software company (Boss -> PM -> Architect -> Engineer -> QA).

### Compatibility
* **Existing Capabilities:** Artifact generation (PRD, System Design), code generation, and standard operating procedures (SOPs).
* **Missing Capabilities:** Hard human-in-the-loop blocking gates (Founder approval), adversarial Review Agent tuned for our specific Maker/Checker loop.
* **Workflow Compatibility:** MetaGPT's default workflow is a waterfall. We need to compress it into our two MVP workflows (Definition & Design, Delivery).

### Can MetaGPT become the foundation of Karsa MVP?
**Yes, but only if we ruthlessly amputate its default configuration.** 

* **What should be reused:** The underlying message bus (Environment), the document parsing utilities, and the code-writing sandbox.
* **What should be replaced:** The default Agent Roster. We will delete the default `ProductManager`, `Architect`, and `Engineer` classes and write a single `ProductEngineer` class. We will replace `QAEngineer` with our adversarial `ReviewAgent`.
* **What should be removed:** All complex, multi-step default SOPs. We replace them with our binary MVP workflow loops.

*(Risk Mitigation: If fighting MetaGPT's internal class structure takes more than 3 days, abandon it and rewrite the state machine in **LangGraph**, which is infinitely simpler for custom workflows).*

---

## 3. Agent Runtime Architecture

The architecture relies on a simple sequential state machine with pause states.

1. **Task Execution:** Agents do not "chat." They execute discrete functions that read files, call the LLM, and write files. 
2. **Context Passing:** Context is passed via the filesystem. The Review Agent doesn't need a summary from the Product Engineer; it just reads the `ARCHITECTURE.md` and the `.py` files.
3. **Review Loops:** 
   * Maker writes code -> broadcasts `CodeUpdated` event.
   * Checker catches event -> runs tests, reads code -> broadcasts `CodeRejected` or `CodeApproved`.
   * If `CodeRejected`, Maker triggers again. Max 3 loops before `HumanEscalation` event.
4. **Approval Handling:** When an agent finishes a phase (Design or Release), the orchestrator pauses execution and yields to standard input (CLI) waiting for the Founder.

---

## 4. State Management Strategy

**Recommendation: The Filesystem + Git.**

* **Project State:** Stored entirely in the working directory of the project being built (e.g., `./research-vault/`).
* **Workflow State:** A single `.karsa/state.json` file that tracks the current workflow step (e.g., `status: waiting_for_architecture_approval`).
* **Agent Outputs & Artifacts:** Written directly as Markdown and Code files.
* **Decisions:** Embedded in the Git commit history and the `ARCHITECTURE.md` file.

**Why:** No database required. No Postgres, no SQLite. Git provides perfect versioning, diffs, and traceability for free. If Karsa crashes, you just read `state.json` and resume.

---

## 5. Artifact Strategy

Artifacts are treated as first-class citizens and stored in plain text.

* **Storage Structure:**
  * `/docs/VISION.md`
  * `/docs/ARCHITECTURE.md` (Contains the 4-field MVP ADRs)
  * `/src/` (Source code)
* **Versioning:** Handled entirely by Git.
* **Traceability:** When the Founder approves a gate, Karsa automatically commits the state to Git with a tag: `git tag -a vision-approved`. This provides a perfect audit trail of exactly what was approved and when.

---

## 6. Human Interaction Model

**Recommendation: Command Line Interface (CLI) + Code Editor.**

* **Avoid:** Web UIs, custom chat interfaces, or dashboard portals. They require maintenance and distract from shipping.
* **MVP Interaction:**
  1. Founder runs `karsa start --idea "Research Vault..."`
  2. Karsa processes, then prints: `[ACTION REQUIRED] Draft Vision ready. Please review ./docs/VISION.md. Type 'approve' to continue or 'reject' to revise.`
  3. Founder opens the file in VSCode, edits it directly if needed, saves, and types `approve` in the terminal.
* **Code Review:** Karsa creates a local Git branch. The Founder reviews the diff in their IDE or via `git diff`.

---

## 7. Execution Flow (Research Vault v0.1)

1. **Idea:** Founder runs `karsa start --idea "A local markdown knowledge base with tagging."`
2. **Definition:** `ProductEngineerAgent` creates `./docs/VISION.md` and `./docs/ARCHITECTURE.md`.
3. **Challenge:** `ReviewAgent` scans it, forces `ProductEngineerAgent` to simplify the database choice from Postgres to SQLite.
4. **Gate 1 (Human):** Execution pauses. Founder reads `ARCHITECTURE.md`, approves via CLI. State updates, Git commit created.
5. **Construction:** `ProductEngineerAgent` writes the Python code and pytest files in `./src/`. 
6. **Quality Loop:** `ReviewAgent` runs `pytest`. Tests fail. `ProductEngineerAgent` fixes code. Tests pass.
7. **Gate 2 (Human):** Execution pauses. Founder tests the local app. Types `approve` in CLI.
8. **Release:** Karsa tags the release `v0.1` and exits gracefully.

---

## 8. Observability

**Recommendation: Standard Out (stdout) + Log Files.**

* **Console Output:** Clean, color-coded terminal output showing which agent is working and what step is active.
* **Log File:** A running `.karsa/execution.log` capturing every LLM prompt, LLM response, and system event.
* **Avoid:** Datadog, Prometheus, LangSmith, or enterprise tracing. Grepping a local text log is sufficient for MVP.

---

## 9. Technical Architecture

* **Language:** Python 3.11+
* **LLM Orchestration:** Stripped MetaGPT (or LangGraph).
* **LLM Provider:** OpenAI API (GPT-4o) or Anthropic (Claude 3.5 Sonnet) for high coding proficiency.
* **Storage:** Local Filesystem + Git binary.
* **Runtime Sandbox:** Standard local Python environment (or a basic Docker container if security against agent hallucinations is a strict requirement for the Founder).
* **Integration Points:** None. No Jira, no Slack. Direct to filesystem.

---

## 10. Roadmap

### Phase 1: Fastest Path to Working MVP (Weeks 1-2)
* Fork framework/setup LangGraph.
* Build the `ProductEngineerAgent` and `ReviewAgent` personas.
* Implement CLI-based pausing for Gate 1 and Gate 2.
* Wire up Git automation.
* **Goal:** Deliver Research Vault v0.1.

### Phase 2: Stabilization (Weeks 3-4)
* Improve error recovery (when LLM outputs malformed code).
* Harden the Quality Loop (better automated test parsing).
* Dockerize the agent execution environment to prevent agents from breaking the host machine.

### Phase 3: Future Evolution (Months 2+)
* Support multi-project states.
* Integrate GitHub API (Agents create actual PRs instead of local branches).

---

## 11. Architectural Risks

1. **Framework Lock-in / Rigidity.**
   * *Risk:* MetaGPT's internal architecture proves too difficult to strip down, wasting engineering time.
   * *Mitigation:* Timebox MetaGPT exploration to 3 days. If it resists modification, pivot immediately to LangGraph, which requires slightly more boilerplate but offers absolute state control.
2. **Agent Context Bloat.**
   * *Risk:* Passing the whole codebase to the LLM for every edit exhausts token limits and increases costs drastically.
   * *Mitigation:* The `ReviewAgent` only passes failed test logs and specific file diffs back to the `ProductEngineerAgent`, not the entire project history.
3. **Founder Bottleneck (CLI blocking).**
   * *Risk:* Karsa stops working overnight because it's waiting for a CLI input.
   * *Mitigation:* This is a feature, not a bug, for the MVP. We *want* execution to halt rather than hallucinate uncontrollably.
4. **Agent Hallucinated Destructive Commands.**
   * *Risk:* `ProductEngineerAgent` accidentally runs `rm -rf` while trying to clean a directory.
   * *Mitigation:* Run the MVP inside a devcontainer or Docker sandbox, never directly on the Founder's bare metal host.
