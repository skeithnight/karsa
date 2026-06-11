# Karsa — Bootstrap Plan

> *"Think big. Build small. Ship fast."*

**Document Status:** Execution Plan
**Date:** 2026-06-11
**Objective:** Define the exact 4-week engineering sequence to build Karsa MVP from scratch and successfully deliver Research Vault v0.1.

---

## 1. Core Assumptions
* **Team:** 1 Engineer (The Founder)
* **Timeline:** 4 Weeks (30 days)
* **Budget/Quota:** Strictly limited; prompt optimization is critical to prevent runaway token costs.
* **Stack:** Python 3.11+, Git, local filesystem, PydanticAI (or LiteLLM) for LLM execution, Pytest.
* **UI:** Pure CLI. No web interface.

---

## 2. Week 1: The Engine & Artifact Foundation

**Objectives:** 
Build the bare-metal orchestrator. No agents yet, just the state machine that can read/write files, commit to Git, and pause for human input.

**Deliverables:**
* `karsa` CLI tool executable.
* State management loop (`state.json`).
* Artifact manager (read/write markdown/code).
* Git automation wrapper.

**Architecture:**
* A strict Python `while` loop that checks the current state and transitions based on hardcoded rules.

**Tasks:**
1. Initialize the Python project and CLI entry point (`karsa start --idea "..."`).
2. Implement `StateController` to read/write `.karsa/state.json`.
3. Implement `ArtifactManager` to safely read/write files to the `./docs/` and `./src/` directories.
4. Implement `GitManager` to auto-commit state changes (`git add . && git commit -m "Karsa: State transition"`).
5. Implement the `HumanGate` function (a wrapper around `input()` that pauses execution until 'approve', 'reject', or a feedback string is typed).

**Acceptance Criteria:**
* Running `karsa start` creates `.karsa/state.json`.
* Mock workflow steps correctly pause, ask for CLI input, and save state to disk and Git when approved.

**Risks:**
* Overcomplicating the state machine. Keep it to a simple dictionary or string-based enum.

---

## 3. Week 2: Definition & Design (Gate 1)

**Objectives:**
Wire up the LLM. Implement the Maker/Checker dynamic for creating the `VISION.md` and `ARCHITECTURE.md`.

**Deliverables:**
* `ProductEngineerAgent` (Design mode).
* `ReviewAgent` (Design mode).
* Working Gate 1 workflow.

**Architecture:**
* Prompt templates injected with the initial idea. 
* Pydantic/JSON output for structured agent decisions.

**Tasks:**
1. Integrate LLM wrapper with API keys.
2. Write the `ProductEngineerAgent` system prompt for drafting Vision and Architecture.
3. Write the `ReviewAgent` system prompt for adversarially challenging the draft (looking for overengineering or cost explosions).
4. Implement the design loop: Maker generates docs -> Checker reviews -> If Checker rejects, Maker revises (max 2 times).
5. Wire the output to the `HumanGate`.

**Acceptance Criteria:**
* Founder runs `karsa start`. Agent generates coherent Vision and Architecture markdown files.
* CLI pauses and asks for approval. 
* Rejecting via CLI with feedback forces the agent to rewrite the document based on founder feedback.

**Risks:**
* Token exhaustion. Ensure agents only pass the specific markdown file context back and forth, not the whole project history.

---

## 4. Week 3: Execution & Delivery (Gate 2)

**Objectives:**
Implement the coding loop. The agents must now write code, run tests, review code, and prepare for release.

**Deliverables:**
* `ProductEngineerAgent` (Code mode).
* `ReviewAgent` (Code mode / Pytest integration).
* Working Gate 2 workflow.

**Architecture:**
* `subprocess` module to execute `pytest` and capture logs.

**Tasks:**
1. Write the `ProductEngineerAgent` prompt for code generation (reads `ARCHITECTURE.md` and creates `.py` files).
2. Implement the `TestRunner` utility to execute `pytest` locally and capture stdout/stderr.
3. Write the `ReviewAgent` prompt to evaluate the code diffs and test logs against the approved architecture.
4. Implement the coding loop: Maker writes code -> TestRunner runs -> Checker evaluates -> If fail, Maker fixes (max 3 loops).
5. Wire the successful build to `HumanGate` for final release approval.

**Acceptance Criteria:**
* Agent correctly writes Python code based on the architecture.
* Syntax errors are automatically caught by Pytest, fed back to the Maker, and fixed.
* System halts at Gate 2 for founder testing.

**Risks:**
* Agent hallucinating infinite loops (e.g., writing tests that pass trivially but don't test the actual application). Prompt the Review Agent to explicitly verify test quality.
* Agent breaking the host machine. Run the execution step inside a virtual environment or basic devcontainer.

---

## 5. Week 4: The Research Vault Pilot

**Objectives:**
End-to-end testing of the framework using the real "Research Vault" project as the test case. Refine prompts and eliminate edge cases.

**Deliverables:**
* Karsa v0.1 Engine.
* Research Vault v0.1 Released Software.

**Architecture:**
* Feature complete. No new architecture.

**Tasks:**
1. Run `karsa start --idea "Build Research Vault..."`.
2. Monitor the agent interactions closely. Adjust agent prompts where they hallucinate or get confused.
3. Fine-tune the temperature settings (lower for code, slightly higher for vision).
4. Verify Git commit history is clean and traceable.
5. Provide founder approval through the CLI and finalize the Research Vault software.

**Acceptance Criteria:**
* Research Vault v0.1 works on the local machine.
* The entire process was orchestrated by the Karsa CLI.

**Risks:**
* Scope creep. The Founder must resist the urge to ask the agent for more features during the pilot. Stick to the strict MVP scope.

---

## 6. The Smallest Possible Path to Execution

Here is the exact runtime flow Karsa will execute to get from zero to released software:

```bash
# 1. Start the workflow
karsa start --idea "Build Research Vault: a markdown knowledge base with tagging."

# Karsa: [ProductEngineer] Generating VISION.md and ARCHITECTURE.md...
# Karsa: [ReviewAgent] Challenging database choice. Recommending SQLite instead of Postgres.
# Karsa: [ProductEngineer] Updating ARCHITECTURE.md to use SQLite.
# Karsa: [SYSTEM] Gate 1 Reached. Please review ./docs/ARCHITECTURE.md.

# 2. Approve Design
karsa approve

# Karsa: [SYSTEM] Committing approved design to Git.
# Karsa: [ProductEngineer] Writing application code and tests...
# Karsa: [ReviewAgent] Running pytest... 1 failed.
# Karsa: [ProductEngineer] Fixing syntax error in database.py...
# Karsa: [ReviewAgent] Running pytest... All passed. Code logic verified against architecture.
# Karsa: [SYSTEM] Gate 2 Reached. Release candidate ready. Please test locally.

# 3. Approve Release
karsa approve

# Karsa: [SYSTEM] Committing release to Git. Tagging v0.1.
# Karsa: [SYSTEM] Research Vault successfully delivered. Exiting.
```

**Final Note:** This plan requires unwavering discipline. Any deviation toward building complex chat UIs, web dashboards, or integrating vector databases for agent memory will cause the 4-week timeline to fail. Focus entirely on the CLI loop and prompt quality.
