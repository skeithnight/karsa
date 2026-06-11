# Karsa — Minimum Viable Product (MVP) Model

> *"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."*

**Document Status:** Approved MVP Definition
**Date:** 2026-06-11
**Objective:** Define the smallest, most pragmatic version of Karsa capable of delivering Research Vault v0.1.

---

## 1. MVP Objective

**"What must Karsa successfully accomplish before we can justify building additional organizational complexity?"**

**Success Statement:**
Karsa must successfully guide a single project (Research Vault) from a raw idea to a deployed, working v0.1 release, using AI agents for execution and a single human founder for authority—without the organizational overhead exceeding the value of the work produced.

The objective is to prove the core "human authority + agent execution + lightweight governance" loop works in reality.

---

## 2. Scope Reduction Analysis

All current Karsa concepts have been ruthlessly evaluated against the goal of shipping Research Vault v0.1.

| Concept | Classification | MVP Decision |
|---|---|---|
| **Discovery** | Must Have | Retained. Essential for defining what Research Vault is. |
| **Architecture** | Must Have | Retained. Essential for defining how to build it safely. |
| **Review** | Must Have | Retained. Essential for catching AI hallucinations/defects. |
| **Planning** | Must Have | Retained (Lightweight). Need a basic roadmap, not a complex portfolio timeline. |
| **Knowledge Organization** | Should Have | **Reduced**. We need ADRs and Post-mortems, but not a dedicated organization. |
| **Research** | Should Have | **Reduced**. Merged into Discovery/Architecture phases as an ad-hoc capability. |
| **Portfolio Management** | Future Phase | **Removed**. There is only one project. |
| **AI Workforce Management** | Future Phase | **Removed**. Agents are invoked directly; no dynamic capacity scaling needed. |
| **AI Platform Organization** | Future Phase | **Removed**. Use direct API calls. Capability routing is premature. |
| **Multi-Project Support** | Future Phase | **Removed**. |
| **Resource Allocation** | Future Phase | **Removed**. The founder and the active agents are the only resources. |
| **Economic Governance** | Future Phase | **Removed**. Founder monitors raw API spend manually for now. |

---

## 3. Minimum Organizational Model

The 7-organization model is too heavy for Stage 1. Karsa MVP reduces this to **Three Core Functions**. These are not "departments," but distinct hats worn during the lifecycle.

### 1. Product Function
* **Why it must exist:** AI agents will build the wrong thing if the "what" is not explicitly defined and constrained.
* **If removed:** Scope creep, misaligned features, and endless iteration without a goal.

### 2. Engineering Function (Absorbs Operations)
* **Why it must exist:** To write the code, run the tests, and deploy the software. Operations is absorbed because "you build it, you run it" is the only viable model for a v0.1.
* **If removed:** No software gets built.

### 3. Governance Function (Lightweight)
* **Why it must exist:** To enforce the boundary between human authority and agent execution, and to ensure basic quality checks are passed before deployment.
* **If removed:** Agents run autonomously, introducing technical debt and security risks without human awareness.

*(Portfolio, Knowledge, and AI Platform organizations are explicitly deferred).*

---

## 4. Minimum Capability Set

To deliver Research Vault v0.1, the organization requires only these 5 core capabilities:

1. **Requirements Translation**
   * **Purpose:** Turn founder ideas into a strict scope document.
   * **Inputs:** Founder's raw notes.
   * **Outputs:** Approved Domain Vision.

2. **System Architecture**
   * **Purpose:** Select the tech stack, data models, and API boundaries.
   * **Inputs:** Domain Vision.
   * **Outputs:** Architecture Document & lightweight ADRs.

3. **Code Construction & Testing**
   * **Purpose:** Write the actual implementation and unit tests.
   * **Inputs:** Architecture Document, component tasks.
   * **Outputs:** Pull Requests / Change Packages.

4. **Quality Review**
   * **Purpose:** Verify code against requirements and catch bugs.
   * **Inputs:** Change Packages.
   * **Outputs:** Review feedback or approval.

5. **Release Deployment**
   * **Purpose:** Push code to the live environment.
   * **Inputs:** Approved Change Packages.
   * **Outputs:** Live Research Vault v0.1.

---

## 5. Minimum Workflow Set

Workflows are aggressively merged to prevent handoff friction.

### Workflow 1: Definition & Design
* **Trigger:** Founder submits an idea for Research Vault.
* **Process:** Agent drafts Vision -> Founder Approves -> Agent drafts Architecture -> Founder Approves.
* **Output:** Approved Implementation Plan.
* **Why:** Combines Idea, Research, Discovery, Architecture, and Planning into a single, contiguous loop.

### Workflow 2: Execution & Delivery
* **Trigger:** Approved Implementation Plan exists.
* **Process:** Agent writes code -> Agent reviews code (Quality Gate) -> Founder does final sanity check -> Agent deploys.
* **Output:** Working Software Release.
* **Why:** Combines Engineering, Review, and Operations.

---

## 6. Minimum Governance Model

Bureaucracy is stripped away. We retain only what prevents disaster.

### Required Approval Gates (Only 3)
1. **Vision Gate:** Human founder approves the exact scope before any code is written.
2. **Architecture Gate:** Human founder approves the tech stack and data model to prevent costly rework.
3. **Release Gate:** Human founder approves pushing code to production.

### Required Decision Records (ADRs)
Only recorded for decisions that are hard to reverse (e.g., database selection, core framework).
* **Fields reduced from 12 to 4:** Decision, Rationale, Authority (Who approved), Date.

*(All other gates: Scope, Quality, Security, Knowledge, Decision — are either automated by agents implicitly or deferred).*

---

## 7. Human Involvement Model

Assuming a single founder, their time is the ultimate bottleneck. The system must maximize their leverage.

* **Where Human Approval is REQUIRED:**
  * Vision and Scope definition (Vision Gate).
  * Major architectural choices (Architecture Gate).
  * Final production deployments (Release Gate).
  * Unblocking agents when they get stuck in loops.

* **Where Human Approval is OPTIONAL:**
  * Routine pull request reviews (Agents should self-review and cross-review; human only reviews critical paths).
  * Minor technical implementations (e.g., how a specific function is written).

* **What MUST be Delegated:**
  * Writing boilerplate code.
  * Writing unit tests.
  * Formatting, linting, and basic security scanning.
  * Generating documentation.

**Identified Bottleneck:** The founder's cognitive load switching between "CEO/Product Owner" (Vision) and "Lead Engineer" (Architecture/Code Review). Karsa must present clear, binary choices to the founder, not open-ended questions.

---

## 8. Research Vault Delivery Scenario

How MVP Karsa will deliver Research Vault v0.1:

1. **Idea:** Founder drops a markdown file with the core concept of Research Vault into Karsa.
2. **Discovery & Architecture:** The Product/Engineering agent reads it, asks 2-3 clarifying questions, and generates a combined Vision & Architecture document.
3. **Review (Gate 1 & 2):** Founder reviews the document. Makes a few edits. Approves it.
4. **Execution:** The Engineering agent breaks the document into 5 distinct coding tasks. It executes Task 1, writes tests, and runs a quality check.
5. **Review (Gate 3):** Agent presents the completed feature. Founder tests it locally or reviews the PR. Approves.
6. **Delivery:** Agent deploys the feature to the hosting provider.
7. **Repeat:** Steps 4-6 repeat for the remaining tasks until v0.1 is complete.

---

## 9. Deferred Capabilities

The following are explicitly excluded from the MVP to guarantee we ship:

* **Portfolio Optimization:** We are only building Research Vault.
* **Workforce Scaling:** No dynamic agent allocation. Agents are invoked linearly.
* **Agent Replication / Shared Memory:** Agents will rely on standard context windows and explicit markdown files (like the Architecture doc), not a complex shared organizational memory database.
* **Advanced Cost Forecasting:** Founder will monitor OpenAI/Anthropic dashboards manually.
* **Multi-Project Governance:** Standards apply only to Research Vault for now.
* **Organizational Analytics / Metrics (The 42 metrics):** We will track zero organizational metrics for v0.1. The only metric is: "Did it ship?"

---

## 10. MVP Success Criteria

The MVP is successful if and only if:

1. **Research Vault v0.1 reaches an implementation-ready state** based on agent-generated, founder-approved designs.
2. **Research Vault v0.1 is deployed and usable** by the founder.
3. **Traceability is maintained:** There is a clear paper trail (Markdown files) of what was built and why.
4. **Founder Leverage:** The founder feels Karsa accelerated the delivery compared to coding it entirely themselves, despite the overhead of governance.

---

## 11. Recommended Next Steps

**Phase 1: Validate MVP (Current)**
* Ship Research Vault v0.1 using the reduced 3-function, 3-gate model.

**Phase 2: Formalize Operations & Learning (Post-v0.1)**
* Introduce basic Operations (monitoring, incident response for Research Vault).
* Introduce the Knowledge Function (formalize Post-Mortems to learn from v0.1 mistakes).
* Expand from 4-field ADRs to a slightly richer format.

**Phase 3: Portfolio & Scaling (Project 2+)**
* Introduce Stock Bot as the second project.
* Activate the Portfolio Organization to manage resources between Research Vault and Stock Bot.
* Activate the AI Platform Capability Registry to route different tasks to specialized, cost-effective models.
