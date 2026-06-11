# Karsa — Agent Catalog (MVP)

> *"Organizations don't ship software. Focused teams ship software. Every role must pull its weight."*

**Document Status:** Approved MVP Definition
**Date:** 2026-06-11
**Objective:** Define the absolute minimum viable workforce required to execute the Karsa MVP Workflow Model and deliver Research Vault v0.1.

---

## 1. Objective

Design the MVP Karsa workforce. Every agent must directly execute a step in the approved `WORKFLOW_MODEL.md`. If an agent represents "governance overhead" without producing tangible software or blocking a catastrophic failure, it is removed. 

The workforce must be capable of delivering Research Vault v0.1 from Idea to Released Software with minimal organizational overhead.

---

## 2. Core Design Principles

1. **Workflow-first design:** Agents exist to serve the workflow, workflows do not exist to give agents jobs.
2. **Minimize agent count:** The ideal number of agents is zero. We only add agents when human effort doesn't scale.
3. **Specialization only when justified:** No micro-agents (e.g., separate "testing" and "coding" agents) unless a single agent repeatedly fails to handle both contexts.
4. **Human authority remains final:** Agents propose; founders approve.
5. **Agents produce artifacts:** Talk is cheap. Code and markdown are measurable.
6. **Agents must be measurable:** If we can't tell if an agent is succeeding or failing, it shouldn't exist.
7. **Remove vanity roles:** No "Scrum Master" or "Agile Coach" agents.

---

## 3. Agent Identification & Challenges

Based on the two approved workflows (Definition & Design, Delivery), we evaluate the proposed agent roster.

### Research Agent
* **Challenge:** Does "Research" require a dedicated agent for Research Vault v0.1?
* **Verdict: REJECTED.** 
* **Rationale:** A dedicated researcher adds an unnecessary handoff. The agent defining the product should do its own contextual research. If this agent is removed, the "Research" workflow step does not disappear; it simply becomes a capability of the primary builder.

### Feasibility Agent
* **Challenge:** Does "Feasibility" require an independent agent?
* **Verdict: REJECTED.**
* **Rationale:** Feasibility (cost, complexity, timeline) is a core component of Architecture. Separating it means the Architect designs things that might not be feasible, creating a loop. Feasibility must be a constraint applied *during* design by the Architect.

### Challenge Agent
* **Challenge:** Does adversarial review (attacking assumptions, fighting overengineering) require its own agent?
* **Verdict: REJECTED.** (Merged into Review Agent)
* **Rationale:** Challenge is a posture, not a role. A "Challenge Agent" that only attacks but doesn't review code is a vanity role. This function is merged into a unified Review Agent.

### Review Agent
* **Challenge:** Should review be separate from challenge? Should it exist at all?
* **Verdict: RETAINED.**
* **Rationale:** LLMs suffer from confirmation bias and context blindness when evaluating their own output. The "Maker" cannot reliably be the "Checker." We must have an independent context window evaluate the Vision, Architecture, and Code. This agent absorbs QA and Challenge capabilities.

### Developer Agent
* **Challenge:** Can this be merged with the Architect?
* **Verdict: RETAINED & EXPANDED.**
* **Rationale:** We will merge the "Product/Architect" role and the "Developer" role into a single **Maker Agent** (officially named the **Product Engineer Agent**). Handoffs between "the agent who wrote the architecture" and "the agent who writes the code" lead to context loss. A single Maker builds the artifacts.

### QA Agent
* **Challenge:** Does QA deserve a dedicated agent?
* **Verdict: REJECTED.**
* **Rationale:** Unit testing and integration testing are the responsibility of the Product Engineer Agent (Developer). Independent verification of the output is the responsibility of the Review Agent. A third QA agent is enterprise bloat.

### Learning Agent
* **Challenge:** Should learning have a dedicated agent?
* **Verdict: REJECTED.** (Deferred)
* **Rationale:** Post-mortems and ADRs will be written by the Maker and approved by the Founder. A dedicated organizational learning agent is a Phase 3 optimization.

---

## 4. Workforce Reduction & The Smallest Viable Workforce

**Initial Prompted List:** Research, Feasibility, Challenge, Review, Developer, QA, Learning (7 agents).
**Reduction Challenge:** Remove 50%.
**Result:** 2 agents (71% reduction).

To ship Research Vault v0.1 in 30 days, we only need the classic **Maker/Checker** dynamic.

### Minimum Viable Workforce (MVP):
1. **Product Engineer Agent (The Maker)**
2. **Review Agent (The Checker)**

---

## 5. Agent Definitions

### Agent 1: Product Engineer Agent (The Maker)

* **Mission:** Transform founder ideas into working, tested, production-ready software.
* **Responsibilities:**
  * Draft `VISION.md` and `ARCHITECTURE.md` (including tech stack & feasibility).
  * Write all application code.
  * Write all unit and integration tests.
  * Generate documentation and lightweight ADRs.
  * Execute deployments after approval.
* **Inputs:** Raw Founder Ideas, Founder Feedback, Review Agent Critiques.
* **Outputs:** Draft Vision/Architecture, Pull Requests / Change Packages, Live Deployments.
* **Success Criteria:** 
  * Code compiles and passes its own tests.
  * Architecture stays within stated budget/complexity constraints.
* **Failure Patterns:** Overengineering the solution; hallucinating APIs; writing code without updating the architecture doc.
* **Required Capabilities:** Full-stack coding, system design, test generation.
* **Interaction With Other Agents:** Submits all generated artifacts to the Review Agent before presenting them to the Founder.
* **Human Escalation Conditions:** Cannot resolve a broken test after 3 attempts; encounters a hard blocker with an external dependency.

### Agent 2: Review Agent (The Checker)

* **Mission:** Protect the Founder from bad design, buggy code, and scope creep.
* **Responsibilities:**
  * Adversarially challenge the Draft Vision/Architecture (identify risks, cost explosions, overengineering).
  * Review all Change Packages (PRs) against the approved architecture.
  * Enforce simplicity.
* **Inputs:** Draft Artifacts, Pull Requests.
* **Outputs:** Review Approvals, Change Requests, Risk Warnings.
* **Success Criteria:**
  * Catches edge cases, security flaws, or architectural drift before the Founder has to review it.
* **Failure Patterns:** Being overly pedantic about formatting; rubber-stamping bad code; hallucinating "better" patterns that are actually unnecessary complexity.
* **Required Capabilities:** Code analysis, architectural reasoning, adversarial logic.
* **Interaction With Other Agents:** Kicks work back to the Product Engineer Agent for revision.
* **Human Escalation Conditions:** Product Engineer Agent repeatedly ignores review feedback; fundamental disagreement on technical approach.

---

## 6. Authority Model

**Agents CAN:**
* **Recommend:** Tech stacks, product features, and code patterns.
* **Draft:** All documentation and code.
* **Challenge:** Assumptions made by other agents (or even the Founder, technically, if framed as a risk warning).
* **Review:** Evaluate artifacts against approved constraints.

**Agents CANNOT:**
* **Override founder decisions:** If the Founder says "use PostgreSQL", the agent must use it, even if it prefers MongoDB.
* **Approve strategic direction:** Agents do not pass Gate 1 (Vision/Architecture).
* **Change approved vision:** Agents cannot decide to pivot Research Vault into a social network halfway through development.
* **Deploy to production unapproved:** Agents do not pass Gate 2 (Release) without human consent.

---

## 7. Human Founder Role

The human founder is the single point of ultimate authority. Their job is to steer, not to row.

* **Responsibilities:**
  * **Vision Approval (Gate 1):** Sign off on what will be built.
  * **Architecture Approval (Gate 1):** Sign off on the technical constraints.
  * **Release Approval (Gate 2):** Sign off on pushing to production.
  * **Conflict Resolution:** Break ties when the Maker and Checker agents are stuck in an infinite loop of revisions.
* **Bottlenecks:** The Founder's context switching and availability to review outputs.
* **Delegation Opportunities:** The Founder delegates 100% of the *drafting* and *initial review* to the agents. The Founder only reads pre-reviewed artifacts.
* **Risks:** The Founder rubber-stamps agent outputs without reading them, leading to a loss of architectural control.

---

## 8. Agent Interaction Model

The workflow traces exactly how artifacts pass through the minimal team.

**Phase 1: Definition & Design**
1. **Workflow Step:** Discovery & Architecture
   * **Responsible:** Product Engineer Agent
   * **Artifact:** Draft Implementation Package (`VISION.md`, `ARCHITECTURE.md`)
   * **Next:** Review Agent
2. **Workflow Step:** Design Challenge
   * **Responsible:** Review Agent
   * **Artifact:** Reviewed Implementation Package (Annotated with risks/suggestions)
   * **Next:** Human Founder (Gate 1)

**Phase 2: Delivery**
3. **Workflow Step:** Construction
   * **Responsible:** Product Engineer Agent
   * **Artifact:** Change Package (Code + Tests)
   * **Next:** Review Agent
4. **Workflow Step:** Quality Validation
   * **Responsible:** Review Agent
   * **Artifact:** Approved Change Package (or rejected back to Product Engineer)
   * **Next:** Human Founder (Gate 2)
5. **Workflow Step:** Release
   * **Responsible:** Product Engineer Agent
   * **Artifact:** Live Software
   * **Next:** End of Cycle.

---

## 9. Final Workforce Recommendation

### Minimum Viable Workforce (MVP - 30 Day Ship)
* **Product Engineer Agent** (Maker)
* **Review Agent** (Checker)
* **Human Founder** (Approver)

*(This is the only configuration that matters for Research Vault v0.1. It feels exactly like a startup: a lead developer, a senior peer reviewer, and the technical founder.)*

### Future Workforce (Post-MVP)
* **Phase 2 (Scale):** Separate the *Product Engineer Agent* into a *Product/Architect Agent* and *Developer Agents* to parallelize coding tasks.
* **Phase 3 (Enterprise):** Introduce *Operations Agent* (for dedicated monitoring) and *Knowledge Agent* (to track portfolio-wide learning).

**Final Challenge Conclusion:** If Research Vault v0.1 must ship in 30 days, any agent other than a Maker and a Checker is a distraction that will generate markdown instead of software. The 2-agent model is finalized.
