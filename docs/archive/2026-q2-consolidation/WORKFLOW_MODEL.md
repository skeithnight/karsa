# Karsa — Workflow Model (MVP)

> *"Shipping is a feature. Everything else is a hypothesis."*

**Document Status:** Approved MVP Definition
**Date:** 2026-06-11
**Objective:** Define the minimum workflow model capable of delivering Research Vault v0.1 and establishing a pragmatic baseline for future projects.

---

## 1. Objective

The objective of this document is to define the **minimum workflow model** required for Karsa MVP. 

This model must support:
* The successful delivery of Research Vault v0.1.
* A repeatable, lightweight baseline for future software projects.
* Efficient, high-leverage human founder oversight.

This model explicitly **does not optimize for**:
* Large organizations.
* Multi-project portfolios.
* Workforce scaling.
* Advanced governance.
* Enterprise process management.

---

## 2. Core Design Principles

1. **Simplicity over completeness:** We only define steps that prevent catastrophic failure.
2. **Shipping over process:** The ultimate goal of the workflow is a deployed release.
3. **Learning over optimization:** We will fix the workflow later based on real friction, not hypothetical problems.
4. **Human authority remains final:** AI agents execute, human founders approve.
5. **Every workflow must produce artifacts:** Traceability relies on explicit documentation, not memory.
6. **Every workflow must have a measurable output:** Activity without a tangible output is waste.

---

## 3. Workflow Constraints

* **Maximum:** 2 primary workflows.
* **Justification:** Every stage, step, and gate must actively contribute to shipping Research Vault v0.1 or preventing its critical failure. Anything that does not directly serve delivery is removed.

---

## 4. Workflow 1: Definition & Design

**From:** Raw Idea
**To:** Approved Implementation Package

This workflow consolidates Research, Discovery, Feasibility Analysis, Architecture Design, and Implementation Planning into a single, contiguous loop.

* **Trigger:** Founder submits a raw idea or feature request (Markdown or text).
* **Purpose:** Transform a vague idea into a strict, buildable, and technically sound blueprint.
* **Inputs:** Idea statement, context, constraints.
* **Outputs:** Approved Implementation Package.

### Stages

1. **Discovery & Research:** 
   * Agent expands the idea, identifies unknowns, conducts ad-hoc research, and proposes a core feature set.
   * *Output:* Draft Vision Document.
2. **Feasibility & Architecture:** 
   * Agent selects the tech stack, outlines data models, and assesses feasibility (Can this be built? Is it cheap enough? Can it run?).
   * *Output:* Draft Architecture Document (includes lightweight ADRs).
3. **Design Review (Gate 1):**
   * Founder reviews the Vision and Architecture.
   * *Output:* Approved Implementation Package.

### Required Artifacts
* `VISION.md` (What are we building and why)
* `ARCHITECTURE.md` (How are we building it, including lightweight decisions)

---

## 5. Workflow 2: Delivery

**From:** Approved Implementation Package
**To:** Released Software

This workflow consolidates Engineering, Code Review, Quality Assurance, and Operations into a tight execution loop.

* **Trigger:** The Founder approves the Implementation Package.
* **Purpose:** Turn the approved design into working, deployed software.
* **Inputs:** Approved Implementation Package.
* **Outputs:** Released Software.

### Stages

1. **Construction:**
   * Agent writes code, writes tests, and builds the components as defined in the architecture.
   * *Output:* Code Changes / Pull Requests.
2. **Quality Loop:**
   * Agent self-reviews code, runs tests, lints, and fixes errors iteratively.
   * *Output:* Validated Release Candidate.
3. **Release Review (Gate 2):**
   * Founder performs a final sanity check of the working software (local run or staging review).
   * *Output:* Release Approval.
4. **Deployment:**
   * Agent pushes to the production environment.
   * *Output:* Live Software.

---

## 6. Artifact Flow

Traceability is maintained through the evolution of markdown files and code state.

### Workflow 1: Definition & Design
* **Input:** Raw Idea
* **Generated Artifacts:** Draft `VISION.md`, Draft `ARCHITECTURE.md`
* **Approved Artifacts:** Final `VISION.md`, Final `ARCHITECTURE.md`
* **Output:** Implementation Package (Vision + Architecture)

### Workflow 2: Delivery
* **Input:** Implementation Package
* **Generated Artifacts:** Source Code, Tests, Review Comments
* **Approved Artifacts:** Merged Code, Passing CI/CD checks
* **Output:** Released Software (Research Vault v0.1)

---

## 7. Human Approval Model

The workflow is designed to maximize founder leverage by enforcing binary approvals rather than open-ended management.

* **Where approval is REQUIRED:**
  * **Design Review Gate:** Approving the Vision and Architecture before coding begins.
  * **Release Review Gate:** Approving the final software before it goes to production.
* **Where approval is OPTIONAL:**
  * Component-level technical decisions (e.g., internal function structure).
  * Routine Pull Request reviews (the human only reviews critical paths if desired).
* **Where approval is DELEGATED (Agent Autonomy):**
  * Drafting initial documents.
  * Writing boilerplate, unit tests, and deployment scripts.
  * Fixing linting and test failures.

---

## 8. Design Review Model

The Minimum Viable Design Review prevents the creation of committees. It is a single synchronous (or asynchronous) review by the founder of the drafted Implementation Package.

**Evaluation Criteria:**
1. **Product Fit:** Does this solve the original problem?
2. **Technical Feasibility:** Can the agent realistically build this stack?
3. **Cost Feasibility:** Will this bankrupt the founder on API or infrastructure costs?
4. **Operational Feasibility:** Is this simple enough to maintain once deployed?

**Process:** The agent submits the `VISION.md` and `ARCHITECTURE.md`. The founder reads, asks for modifications if necessary, and ultimately approves. No boards, no bureaucracy.

---

## 9. Decision Model

We only record decisions that are expensive to reverse (e.g., Database choice, Core framework, External Provider selection).

* **What is recorded:** Major architectural shifts, irreversible tech choices.
* **What is ignored:** File naming conventions, minor library choices, internal function designs.

**Minimum Decision Record Structure (Embedded in ARCHITECTURE.md):**
1. **Decision:** What we are doing.
2. **Rationale:** Why we chose this (briefly).
3. **Authority:** Who approved it (The Founder).
4. **Date:** YYYY-MM-DD.

---

## 10. Failure Handling

When things go wrong, we prefer rapid iteration over formal escalation.

* **Insufficient Research / Vague Idea:** Agent asks the founder clarifying questions immediately rather than halting.
* **Rejected Design (Vision):** Agent refines the `VISION.md` based on founder feedback in a fast revision loop.
* **Rejected Architecture:** Agent proposes an alternative tech stack or data model.
* **Failed Feasibility:** If a feature is too expensive or too complex, the agent suggests scoping it down rather than escalating to a "blocker" status.
* **Failed Quality Loop (Tests fail):** Agent attempts to self-correct. If stuck in an infinite loop, it flags the founder for technical assistance.

---

## 11. Workflow Metrics

We track only what indicates velocity and health. (Maximum 4 metrics).

1. **Time to Design Approval:** Days from raw idea to Approved Implementation Package.
2. **Time to Release:** Days from Implementation Package to live software.
3. **Design Rejection Rate:** How often the founder rejects the initial Vision/Architecture drafts.
4. **Quality Loop Failure Rate:** How often the agent gets stuck trying to fix its own broken code.

---

## 12. MVP Validation

**Success Criteria:**
The workflow model is deemed successful if **Research Vault v0.1** can move from a raw idea to a deployed release with:
* Acceptable quality and stability.
* Traceable decisions (via Vision and Architecture docs).
* The founder spending their time making high-leverage decisions rather than micromanaging process overhead.

If the workflow feels heavy, it has failed. If Research Vault ships, it has succeeded.

---

## 13. Out of Scope

The following workflows are explicitly excluded from this MVP to protect delivery velocity:

* Portfolio management and cross-project workflows.
* Incident response and formal operational alerting workflows.
* Workforce management (agent capacity planning) workflows.
* Organizational analytics workflows.
* Advanced governance (security audits, compliance boards) workflows.
* Multi-project optimization workflows.
