# Karsa — Execution Blueprint

> *"Stop talking. Start typing."*

**Document Status:** Execution Ready
**Date:** 2026-06-11
**Objective:** Provide the exact implementation blueprint required to immediately begin coding Karsa MVP. No further design is required.

---

## 1. Repository Structure

The codebase is structured for a single-engineer Python application. 

```text
karsa-mvp/
├── karsa/
│   ├── __init__.py
│   ├── cli.py                 # Typer/Click based CLI entrypoints
│   ├── core/                  # The bare-metal engine
│   │   ├── engine.py          # State machine runner
│   │   ├── state.py           # JSON state persistence
│   │   ├── human_gate.py      # CLI input blocking
│   │   └── git_manager.py     # Subprocess git commands
│   ├── agents/                # The workforce
│   │   ├── base_agent.py      # Shared LLM execution logic
│   │   ├── product_engineer.py# Maker Agent
│   │   └── review_agent.py    # Checker Agent
│   ├── artifacts/             # File I/O
│   │   └── manager.py         # Markdown/code reader and writer
│   └── llm/                   # Provider agnostic wrapper
│       └── client.py          # LiteLLM/PydanticAI initialization
├── pyproject.toml             # Dependencies (typer, litellm, pydantic)
└── .karsa_template/           # Scaffolding for new projects
    └── state.json             # Default empty state
```

**Rationale:** Separation of concerns without enterprise bloat. The CLI triggers the Engine. The Engine manages State and calls Agents. Agents read/write via the Artifact Manager. Git tracks it all.

---

## 2. Sprint 0: The Engine Foundation

**Goal:** The smallest possible codebase that should exist before any AI integration. Karsa must be able to move through mock states, write text files, and commit to Git.

**Deliverables:**
* `cli.py` with `start` and `approve` commands.
* `engine.py` workflow state machine.
* `manager.py` (Artifact storage).
* `git_manager.py` (Git integration).
* `human_gate.py` (Human approval gate).

**Acceptance Criteria:**
* Running `karsa start --idea "test"` creates a `.karsa/state.json` file in the current directory.
* The engine transitions from `IDEA` to `APPROVAL` automatically.
* At `APPROVAL`, execution halts and waits for the founder.
* Running `karsa approve` transitions the state, creates a dummy file in `./docs/`, and commits it to Git automatically.

---

## 3. Sprint 1: Product Engineer Agent

**Goal:** Implement the Maker. Connect the LLM so the agent can draft the required artifacts.

**Components & Classes:**
* `ProductEngineerAgent(BaseAgent)`
* `PromptBuilder` (Handles injecting context).

**Interfaces:**
* `execute_design(idea: str) -> None`: Generates Vision and Architecture.
* `execute_code(architecture: str) -> None`: Generates Python code.

**Artifact Generation Flow:**
1. Reads `state.json` to determine task.
2. Calls LLM with `system_prompt_maker`.
3. Calls `ArtifactManager` to write output to `./docs/vision.md` and `./docs/architecture.md`.

**Acceptance Criteria:**
* Agent reliably takes a 1-sentence idea and outputs properly formatted markdown files.
* Code generation creates syntactically valid `.py` files in `./src/`.

---

## 4. Sprint 2: Review Agent

**Goal:** Implement the Checker. The adversarial counterpart to the Maker.

**Components & Classes:**
* `ReviewAgent(BaseAgent)`
* `TestRunner` (Subprocess wrapper for pytest).

**Interfaces:**
* `review_design() -> ReviewResult`: Challenges architecture.
* `review_code() -> ReviewResult`: Runs tests and challenges code.

**Review Flow:**
1. Reads newly generated artifacts.
2. Analyzes for cost explosions, overengineering, or test failures.
3. Outputs a structured `ReviewResult` (Pass/Fail + Feedback).

**Acceptance Criteria:**
* Agent correctly identifies hallucinations or over-complicated database choices in the Architecture doc.
* Agent successfully captures failing `pytest` logs and formats them into a feedback string.

---

## 5. Workflow Engine

The exact state machine implementation. Persisted in `.karsa/state.json`.

**States:**
1. `IDEA`
2. `RESEARCH`
3. `ARCHITECTURE`
4. `REVIEW`
5. `APPROVAL`
6. `IMPLEMENTATION`
7. `RELEASE`
8. `DONE`

**Transitions:**
* `IDEA` -> `RESEARCH` (Auto)
* `RESEARCH` -> `ARCHITECTURE` (Auto)
* `ARCHITECTURE` -> `REVIEW` (Auto)
* `REVIEW` -> `APPROVAL` (If ReviewAgent passes)
* `REVIEW` -> `ARCHITECTURE` (If ReviewAgent fails)
* `APPROVAL` -> `IMPLEMENTATION` (If Founder types `approve`)
* `IMPLEMENTATION` -> `REVIEW` (Auto)
* `REVIEW` -> `RELEASE` (If ReviewAgent passes code/tests)
* `RELEASE` -> `DONE` (If Founder types `approve`)

**Invalid Transitions:**
* Cannot go from `ARCHITECTURE` to `IMPLEMENTATION` (Bypasses Review and Approval).
* Cannot go to `RELEASE` if tests fail.

**Persistence Strategy:**
* Simple JSON file updated on every transition. If the script crashes, running `karsa status` reads the JSON and resumes the correct function.

---

## 6. Artifact System

Artifacts are the source of truth. The LLM context window is reset between steps; it only reads these files to gain context.

**Hierarchy:**
* `/docs/vision.md` (Product definition)
* `/docs/research.md` (Feasibility notes)
* `/docs/architecture.md` (Tech stack, data models, ADRs)
* `/docs/implementation_plan.md` (Checklist of tasks)
* `/docs/review.md` (The latest feedback from the Review Agent)
* `/src/*` (Application Code)

**Creation:** Written exclusively by the `ArtifactManager` to ensure consistent formatting.
**Versioning:** Handled entirely by Git.
**Approval:** Approved when the state machine passes `APPROVAL` or `RELEASE`.
**Storage:** Plain text on the local filesystem.

---

## 7. Git Integration

Git acts as Karsa's database and audit log.

**Commit Strategy:**
* `GitManager.commit(message)` is called on *every* successful state transition.
* Example: `git commit -m "[Karsa] State transition: RESEARCH -> ARCHITECTURE"`

**Tag Strategy:**
* When Founder approves a gate, Karsa tags the commit.
* `git tag -a vision-approved -m "Founder approved vision"`
* `git tag -a v0.1-release -m "Founder approved release"`

**Approval Checkpoints & Rollback:**
* If the Maker agent gets stuck in a hallucination loop and ruins the codebase, the Founder runs `git reset --hard HEAD~1` to revert to the last clean state, and resumes Karsa.

---

## 8. CLI Design

Built using `typer` or `click` for immediate usability.

**Commands:**

* `karsa start --idea "<text>"`
  * *Structure:* Initializes `.karsa/state.json`, sets state to `IDEA`, kicks off engine.
  * *Outputs:* Terminal logs showing agent progress.

* `karsa review`
  * *Structure:* Triggers the `ReviewAgent` manually if the founder wants an on-demand check.
  * *Outputs:* Prints pass/fail and writes to `review.md`.

* `karsa approve`
  * *Structure:* Moves state from `APPROVAL` -> `IMPLEMENTATION` or `RELEASE` -> `DONE`.
  * *Outputs:* Commits to git, tags, and resumes the engine.

* `karsa reject --reason "<text>"`
  * *Structure:* Kicks state back to the Maker agent with the provided reason.

* `karsa status`
  * *Structure:* Reads `state.json` and prints current phase.

---

## 9. Core Class Diagram

Minimum class structure. No getters/setters, no abstract factories.

```python
class WorkflowEngine:
    def run(self)
    def transition_to(self, new_state)

class ArtifactManager:
    def read_artifact(self, name) -> str
    def write_artifact(self, name, content)

class GitManager:
    def commit_state(self, state_name)
    def tag_approval(self, tag_name)

class HumanGate:
    def wait_for_approval(self) -> bool

class ProductEngineerAgent:
    def draft_design(self, idea) -> dict
    def write_code(self, architecture) -> dict

class ReviewAgent:
    def challenge_design(self, design_docs) -> bool
    def verify_code(self, code_dir) -> bool
```

---

## 10. Development Order

1. **`cli.py` & `state.py`**
   * *Why:* You cannot run anything without the entry point and state tracking.
   * *Dependencies:* None.
2. **`artifacts.py` & `git_manager.py`**
   * *Why:* State transitions are useless if files aren't created and tracked.
   * *Dependencies:* State module.
3. **`engine.py` (Sprint 0 completion)**
   * *Why:* Ties CLI, State, Artifacts, and Git together. Must be tested before adding LLMs.
   * *Dependencies:* CLI, State, Artifacts, Git.
4. **`llm_client.py` & `product_engineer.py`**
   * *Why:* Now we add the brain. The Maker must be able to write the docs.
   * *Dependencies:* Engine, Artifacts.
5. **`review_agent.py`**
   * *Why:* The Checker must be implemented last so it has actual Maker outputs to review.
   * *Dependencies:* ProductEngineer outputs.
6. **Integration Testing (Research Vault Pilot)**
   * *Why:* Run it end-to-end.

---

## 11. Risks & Mitigations

* **Technical Risk: Context Window Exhaustion**
  * *Mitigation:* The `ArtifactManager` strictly limits what is passed to the LLM. The Review Agent only gets the `ARCHITECTURE.md` and the specific `.py` files changed in the last commit, not the entire repo history.
* **Prompt Risk: Infinite Revision Loops**
  * *Mitigation:* Hardcode a `max_retries=3` limit in the Workflow Engine. If the Checker rejects the Maker 3 times, auto-transition to `HUMAN_APPROVAL` so the Founder can break the tie.
* **Workflow Risk: Silent Failures**
  * *Mitigation:* If `pytest` hangs or errors out entirely, `TestRunner` must have a timeout (e.g., 30 seconds) that raises an exception and halts Karsa.
* **Founder Bottlenecks**
  * *Mitigation:* Karsa CLI emits a system beep or terminal bell `\a` when it reaches an approval gate so the founder can background the terminal while working.

---

## 12. Definition of Done

Karsa MVP is complete, and ready for production use, when a founder can open an empty directory, run:

```bash
karsa start --idea "Build Research Vault Lite: A local markdown viewer."
```

And successfully produce:
* `vision.md`
* `research.md`
* `architecture.md`
* `review.md`
* `implementation_plan.md`

All stored safely as artifacts in the `./docs/` folder, with full Git commit history, and a complete workflow trace proving the agents autonomously routed through the state machine and paused for the founder's approval.

**Implementation can begin immediately.**
