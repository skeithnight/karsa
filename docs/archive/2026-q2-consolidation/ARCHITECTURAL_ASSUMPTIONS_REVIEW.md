# Karsa — Architectural Assumptions Review

> *"The purpose of a review is not to validate the design. It is to find the cracks before the building is occupied."*

**Document Status:** Independent Review
**Date:** 2026-06-11
**Reviewer Role:** Independent Enterprise Architect
**Review Scope:** [VISION.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/vision/VISION.md), [ORGANIZATION_MODEL.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/organization/ORGANIZATION_MODEL.md)
**Engagement:** Critical review — no prior involvement in design

---

## Reviewer's Note

I was not involved in creating Karsa. I have reviewed VISION.md and ORGANIZATION_MODEL.md as an outsider — with the lens of a skeptical CTO, enterprise architect, and organizational designer. My job is not to praise what is strong. My job is to find what is assumed, what is fragile, what is missing, and what may be over-designed for the current reality.

The documents are well-written. The thinking is coherent. That makes it more important — not less — to stress-test the foundation before building on it.

---

## 1. Assumption Inventory

The following assumptions are embedded in the current design. Some are stated explicitly. Most are implied. All carry risk.

### A1. Karsa Is an Organization, Not a Tool

| Field | Detail |
|---|---|
| **Assumption** | The "organization" metaphor is the correct framing for a system of AI agents governed by a human founder |
| **Why It Exists** | To differentiate Karsa from automation scripts, prompt chains, and agent swarms — and to justify governance, authority, and institutional structure |
| **Risk If Wrong** | If the metaphor is too heavy, it creates organizational overhead that exceeds the value of the work being governed. A solo founder managing 3 small projects through 7 organizational functions, 8 authority levels, 8 governance gates, and 42 metrics may spend more time managing the organization than building products. |
| **Confidence Level** | **Medium.** The metaphor is valuable for long-term vision. The risk is that it becomes a constraint before it becomes an advantage — particularly in the Foundation Stage. |

### A2. Human Approval Remains Central and Scalable

| Field | Detail |
|---|---|
| **Assumption** | The Human Founder can serve as the ultimate authority for all strategic decisions, vision approvals, conflict resolution, and governance overrides — across a growing portfolio |
| **Why It Exists** | To ensure human oversight and prevent autonomous organizational behavior |
| **Risk If Wrong** | The Human Founder becomes the system's bottleneck. Every Vision Gate, every unresolved escalation, and every governance override flows to a single person. With 3–5 concurrent projects, each with multiple lifecycle phases, the human becomes the approval queue. This directly triggers Risk 16.3 (Approval Bottlenecks) from the organization's own risk registry. |
| **Confidence Level** | **Low for Stage 2+.** Works for a single project. Breaks at portfolio scale unless delegation is aggressively expanded. |

### A3. AI Agents Can Reliably Fill Specialized Organizational Roles

| Field | Detail |
|---|---|
| **Assumption** | Current AI capabilities are sufficient to reliably perform the specialized roles described — discovery, architecture, engineering, quality review, operations, governance, knowledge management — at a professional standard |
| **Why It Exists** | It is the foundational premise. Without it, the entire organizational model is theoretical. |
| **Risk If Wrong** | The organization is designed around a capability that does not yet exist at the required reliability. Governance gates assume reviewers can catch issues. Architecture reviews assume architectural reasoning. Knowledge transformation assumes analytical capability. If any of these are unreliable, the governance system provides false assurance — which is worse than no governance at all. |
| **Confidence Level** | **Medium.** Some roles (code generation, code review) are within current capabilities. Others (strategic product decisions, architectural trade-off reasoning, organizational learning extraction) are at the frontier or beyond it. |

### A4. Governance Is Net-Positive at All Scales

| Field | Detail |
|---|---|
| **Assumption** | Governance creates more value than it costs, at every stage of organizational maturity |
| **Why It Exists** | VISION.md Principle 6.3 states governance is foundational. The Organization Model embeds 8 approval gates, 5 compliance review types, and a 12-field decision traceability schema. |
| **Risk If Wrong** | At small scale (1–2 projects, 1 human), full governance may cost more than the defects it prevents. The documents acknowledge this risk (Governance Overhead, Risk 16.5) but do not define a "governance light" mode for early stages. The Stage 1 characteristics mention "basic governance gates" but do not define which gates are omitted or how the model is reduced. |
| **Confidence Level** | **Medium at maturity. Low at foundation.** Proportional governance is mentioned as a principle but never operationalized. |

### A5. A Shared Workforce Model Is Viable for AI Agents

| Field | Detail |
|---|---|
| **Assumption** | AI agents can be meaningfully "allocated," "reassigned," and "scaled" across projects like a human workforce |
| **Why It Exists** | To support portfolio thinking and resource management as organizational functions |
| **Risk If Wrong** | AI agents are not humans. They do not retain context between invocations (unless explicitly designed to). They do not carry "organizational learning" inherently. The shared workforce model may import human organizational concepts that do not map to AI operational reality. An AI agent "reassigned" from Project A to Project B does not bring Project A's lessons — it brings whatever context its prompt and memory system provide. |
| **Confidence Level** | **Low.** This is the assumption with the largest gap between the organizational metaphor and AI operational reality. |

### A6. Capability-Based Execution Is Superior to Model-Based Execution

| Field | Detail |
|---|---|
| **Assumption** | Organizations should request capabilities ("I need code review") rather than specific models ("I need Claude Opus") |
| **Why It Exists** | For decoupling, cost optimization, and centralized governance (Section 3.7) |
| **Risk If Wrong** | At current maturity, the organization may have exactly one provider for most capabilities. The abstraction layer adds complexity without providing actual routing flexibility. If you have one model that can do code review, the "capability abstraction" is just an indirection layer around a direct model call. The value only materializes at scale with multiple providers — which may be years away. |
| **Confidence Level** | **High at maturity. Low at foundation.** Sound long-term architecture. Premature at current scale. |

### A7. Knowledge Compounds Automatically Through Organizational Process

| Field | Detail |
|---|---|
| **Assumption** | Capturing decisions, post-mortems, and patterns will naturally lead to knowledge compounding — where each project makes the organization measurably smarter |
| **Why It Exists** | It is the core value proposition of Karsa's Knowledge Organization and one of the stated competitive advantages |
| **Risk If Wrong** | Knowledge compounding requires not just capture but retrieval, contextual matching, and application. These are distinct capabilities that require their own infrastructure. The documents describe an aspirational outcome (compounding) but not the mechanism by which past knowledge surfaces at the moment of decision. Without this mechanism, knowledge accumulates but does not compound — becoming the archive the documents explicitly warn against. |
| **Confidence Level** | **Medium.** The Knowledge Organization section is the strongest in the design. But the "how does past knowledge reach the current decision" mechanism is not addressed. |

### A8. Seven Organizational Functions Is the Right Number

| Field | Detail |
|---|---|
| **Assumption** | Portfolio, Product, Engineering, Operations, Governance, Knowledge, and AI Platform are the correct organizational decomposition |
| **Why It Exists** | Mirrors conventional software organization structure |
| **Risk If Wrong** | Seven organizations for a single-person-founded virtual entity managing 3 initial projects may be overstructured. In a traditional company, these functions emerge as the company grows. Here they are defined before the first project ships. Some functions (Portfolio, Knowledge) may not have enough work to justify organizational distinction at Stage 1. |
| **Confidence Level** | **High for the taxonomy. Medium for early-stage activation.** The functions are correct; the question is when each one earns its existence. |

### A9. Research Vault Is Separate from Karsa

| Field | Detail |
|---|---|
| **Assumption** | Research Vault (a project in the portfolio) provides knowledge infrastructure to Karsa (the organization) while being governed by Karsa |
| **Why It Exists** | To separate concerns: Karsa is the organization; Research Vault is the knowledge infrastructure |
| **Risk If Wrong** | Circular dependency. Karsa depends on Research Vault for institutional memory. Research Vault depends on Karsa for governance and resource allocation. If Research Vault is deprioritized in the portfolio, Karsa's own knowledge infrastructure degrades. If Karsa's governance is immature, Research Vault's quality suffers. The "separate but symbiotic" framing may mask a tighter coupling that the organizational model does not adequately address. |
| **Confidence Level** | **Medium.** The separation is clean on paper. The operational dependency creates fragility. |

### A10. The Organizational Metaphor Will Not Limit Innovation

| Field | Detail |
|---|---|
| **Assumption** | Structuring AI agents as an "organization" with human corporate concepts (authority hierarchies, governance gates, approval workflows, escalation paths) is the right paradigm for AI-native work |
| **Why It Exists** | It provides a familiar, proven model for structured work |
| **Risk If Wrong** | Human organizational structures evolved to manage human limitations — communication bandwidth, trust gaps, cognitive load, political dynamics. AI agents may not share these limitations and may be better served by a fundamentally different coordination model. By importing the full organizational metaphor, Karsa may be importing solutions to problems that AI agents do not have — while missing solutions to problems that AI agents do have (context window limits, hallucination, determinism, lack of true understanding). |
| **Confidence Level** | **Medium.** This is a philosophical risk. The organizational metaphor may be exactly right, or it may be a comfortable cage. The design should remain aware that it is a choice, not an inevitability. |

---

## 2. Organization vs. Operating System

### The Question

Is Karsa better positioned as:

- **Option A:** A Virtual Software Organization (current positioning)
- **Option B:** An Operating System for Software Organizations

This is not a semantic distinction. It has profound implications for scope, identity, and long-term strategic direction.

### Option A: Virtual Software Organization

**Advantages:**
- Provides a clear identity and narrative — "Karsa is an organization"
- Justifies the full organizational model (governance, authority, knowledge, etc.)
- Creates emotional resonance — "building an organization" feels more ambitious than "building a tool"
- Naturally supports the portfolio concept — organizations manage portfolios
- Aligns with the founder's vision of a company-like entity

**Disadvantages:**
- Limits scope to a single organizational instance — Karsa *is* the organization, so there is only one
- Makes Karsa's identity inseparable from its current projects — if Stock Bot and Research Vault fail, has the "organization" failed?
- Creates conceptual overhead for a single-founder operation — one person running seven organizations
- Risks the "playing house" critique — is this a real organization or a simulation of one?
- Makes it harder to evolve toward a platform model later

### Option B: Operating System for Software Organizations

**Advantages:**
- Positions Karsa as infrastructure — reusable, extensible, general-purpose
- Allows multiple organizational instances to run on the same "OS"
- Separates the model from the instance — Karsa defines how organizations work; specific projects are instances
- More natural fit for the concepts already in the design: workflows, governance gates, authority models, capability registries
- Enables future extensibility — other founders could theoretically run their own organizations on the Karsa OS

**Disadvantages:**
- More abstract — harder to explain and less emotionally compelling
- Risks "platform trap" — building infrastructure instead of shipping products
- May encourage premature generalization before the model is validated
- Loses the narrative power of "Karsa is the organization"
- Increases design complexity — now you need a meta-model (the OS) and instances (the organizations)

### Long-Term Implications

| Dimension | Organization | Operating System |
|---|---|---|
| **Identity** | Singular, specific | General, reusable |
| **Scope** | One organization, many projects | Many organizations possible |
| **Risk** | Organization-level failure is existential | Platform without users is pointless |
| **Growth path** | Add projects to the portfolio | Add organizations to the platform |
| **MVP feasibility** | Higher — you just run the org | Lower — you need the meta-layer |

### Recommendation

**Stay with Organization for now. Acknowledge Operating System as a possible future evolution.**

The Operating System framing is intellectually appealing but premature. Karsa has not yet validated its organizational model with a single project. Building a meta-model for organizations before proving the model works for one organization is a classic platform-before-product mistake.

However, the design should be **aware** that the organizational model it is building could eventually be extracted as a reusable operating model. This means avoiding decisions that permanently embed Karsa-the-organization into Karsa-the-model. The current design is reasonably clean in this regard — the organizational model is documented as an artifact, not hardcoded into the identity.

> **Action:** Add a note in VISION.md Section 10 (Future Evolution) acknowledging that the organizational model itself could become a reusable asset — without committing to it now.

---

## 3. Capability Layer Evaluation

### The Question

Does Karsa need a formal Capability Layer between the Organization and Workflows?

- **Option A:** Organization → Workflow (direct)
- **Option B:** Organization → Capability → Workflow (intermediated)

### Option A: Organization → Workflow

| Dimension | Assessment |
|---|---|
| **Benefits** | Simpler. Fewer abstractions. Faster to implement. Easier to debug. The organization defines workflows; workflows are executed. |
| **Costs** | Workflows become tightly coupled to organizational structure. Changing the organization requires changing the workflows. |
| **Complexity** | Low |
| **Scalability** | Adequate for Stage 1–2. May struggle at Stage 3 when workflow reuse across projects becomes important. |

### Option B: Organization → Capability → Workflow

| Dimension | Assessment |
|---|---|
| **Benefits** | Capabilities become reusable building blocks. The same "code review" capability can be composed into different workflows for different projects. The AI Platform's capability-based model already implies this layer. Enables governance at the capability level, not just the workflow level. |
| **Costs** | Additional abstraction layer. Capability registry becomes a critical dependency. Requires defining, cataloging, and governing capabilities as distinct organizational entities. |
| **Complexity** | Medium-High |
| **Scalability** | Superior for Stage 2+. Capabilities can be composed, reused, and independently governed. |

### Assessment

The current design **already implies a Capability Layer** through the AI Platform Organization's Capability Registry. But it is positioned as an infrastructure concern (which model handles which request) rather than an organizational concern (what can the organization do).

The gap is between:
- "Capabilities" as AI model routing (current: Section 11.3)
- "Capabilities" as organizational competencies (missing: what can the organization do, at what quality level, across which domains?)

### Recommendation

**Do not add a formal Capability Layer now. But recognize the AI Platform's Capability Registry as the seed of one.**

At Stage 1, adding a full capability layer is premature complexity. At Stage 2, when multiple projects need the same organizational competencies (code review, architecture analysis, test generation), the Capability Registry should evolve from "which model handles this request" to "what can the organization do and how well."

> **Action:** Note in the Organization Model that the Capability Registry is expected to evolve from a provider-routing mechanism into an organizational capability catalog as the organization matures.

---

## 4. Research Function Evaluation

### The Question

Should Research be:

- **Option A:** An organization (peer to Engineering, Product, etc.)
- **Option B:** A capability (available to all organizations)
- **Option C:** A shared service (infrastructure, like AI Platform)

### Current State

Research is not an organization. Research Vault is a project in the portfolio that provides knowledge infrastructure to Karsa. The Knowledge Organization handles internal organizational learning. There is no explicit "research function" — no one is responsible for external research, technology scanning, competitive analysis, or strategic intelligence gathering.

### Evaluation

| Option | Pros | Cons |
|---|---|---|
| **Organization** | Dedicated focus on research. Clear accountability. Full organizational treatment with metrics, governance, and authority. | Overhead for a function that may not have continuous demand. 8th organization adds complexity. Research may be episodic, not continuous. |
| **Capability** | Available to all organizations on demand. No standing overhead. The Engineering Organization can research when it needs to; the Product Organization can research when it needs to. | No accountability for research quality. No organizational learning from research efforts. Research becomes ad-hoc — exactly the behavior Karsa is designed to prevent. |
| **Shared Service** | Positioned like the AI Platform — infrastructure that serves all organizations. Continuous operation without full organizational overhead. Centralized research governance. | May not have enough work to justify a standing service at Stage 1. Could be absorbed into the Knowledge Organization. |

### Recommendation

**Do not create a Research Organization. Assign research responsibility as a capability of the Knowledge Organization.**

The Knowledge Organization already has the mission of pattern identification, cross-project learning, and institutional wisdom development. External research (technology scanning, competitive analysis, domain research) is a natural extension of this mission. Creating a separate organization would fragment the knowledge function unnecessarily.

Research Vault should remain a project (infrastructure for knowledge storage and retrieval), not an organization.

> **Action:** Add "external research and technology scanning" to the Knowledge Organization's responsibilities if it is deemed important. Do not create a new organizational function for it.

---

## 5. Economic Governance Evaluation

### Current State

The design mentions financial governance (VISION.md Section 7.5), budget awareness, and cost management (AI Platform Organization). The Resource Constraint Policies (Section 12) address budget exhaustion scenarios.

### Gaps Identified

| Gap | Description | Severity |
|---|---|---|
| **No organizational budget model** | There is no definition of what Karsa's operating costs are, how they are categorized, or how budget is structured. AI costs are addressed; infrastructure costs, tooling costs, and total cost of ownership are not. | **High** |
| **No cost-per-project tracking** | Portfolio prioritization considers "strategic value" and "resource demand" but does not include cost-per-project as a dimension. A project that is strategically aligned but economically unsustainable should be identifiable. | **High** |
| **No ROI or value realization framework** | The organization produces Approved Work Packages but has no mechanism for evaluating whether those packages produce value. Without value measurement, the organization cannot distinguish between productive work and expensive busywork. | **Medium** |
| **No total cost of governance** | Governance is described as foundational but its cost is not measured. The Governance Overhead risk (16.5) identifies this as a risk but the metrics section does not include a "governance cost as percentage of total output" metric. | **Medium** |
| **No infrastructure cost awareness** | The design focuses on AI provider costs but does not address infrastructure costs — hosting, storage, CI/CD, monitoring tools, development environments. These costs exist and grow with the portfolio. | **Medium** |
| **No cost ceiling or budget authority** | The authority model defines who approves decisions but does not define spending authority. Can Engineering choose a more expensive architectural approach without cost review? At what threshold does a decision become a spending decision? | **High** |

### Recommendation

**Add an Economic Governance section to the Organization Model.** This should define:

1. Organizational cost categories (AI compute, infrastructure, tooling, governance overhead)
2. Budget structure and allocation authority
3. Cost-per-project awareness as a portfolio dimension
4. Spending authority thresholds — at what cost level does a decision require financial review?
5. Value realization — how does the organization know its outputs are producing value, not just artifacts?

> **Action:** Create a dedicated Economic Governance subsection in the Organization Model. This is a significant gap. An organization that does not understand its own economics cannot make informed strategic decisions.

---

## 6. Design Review System Evaluation

### Current State

The Organization Model defines 8 governance gates (Section 8.2) covering vision, architecture, scope, quality, security, release, decision, and knowledge. Architecture reviews produce ADRs and cross-project impact assessments (Section 8.4).

### Gaps Identified

| Review Type | Currently Covered? | Gap Assessment |
|---|---|---|
| **Architecture Review** | ✅ Yes — Section 8.4 | Well-defined. Produces ADRs and cross-project impact analysis. |
| **Code/Quality Review** | ✅ Yes — Quality Gate | Covered as a governance gate. |
| **Security Review** | ✅ Yes — Security Gate | Covered as a governance gate. |
| **Release Review** | ✅ Yes — Release Gate | Comprehensive — 7 criteria defined. |
| **Cross-Functional Review** | ⚠️ Partial | Reviews are gate-based (pass/fail). There is no defined mechanism for cross-functional review workshops where multiple organizations evaluate a proposal collaboratively before it reaches a gate. Gates are checkpoints; cross-functional reviews are collaborative design activities. |
| **Cost Review** | ❌ No | No gate evaluates whether a design or decision is economically sound. Architecture can approve a design that is technically excellent but operationally unaffordable. |
| **Infrastructure Review** | ❌ No | No gate evaluates infrastructure decisions — hosting, scaling strategy, environment design. These are implicit in the Architecture Gate but not explicit. |
| **Operational Readiness Review** | ⚠️ Partial | The Release Gate includes "operational readiness criteria" but there is no pre-architecture operational review — ensuring designs are operable before they are built, not just before they are deployed. |
| **Feasibility Review** | ❌ No | Product requirements pass through a Scope Gate but there is no formal feasibility review where Engineering evaluates whether a requirement is achievable within resource, time, and capability constraints before it enters the roadmap. |
| **Post-Implementation Review** | ❌ No | After a release, there is no formal review evaluating whether the delivered software achieved its intended product goals. Post-mortems cover incidents; nothing covers "did this feature work?" |

### Recommendation

Three reviews should be added:

1. **Feasibility Review** — Engineering evaluates product proposals for technical and resource feasibility *before* they enter the roadmap. Currently, Product defines what is built and Engineering defines how — but there is no explicit checkpoint where Engineering validates that the "what" is achievable.

2. **Cost Review** — Significant architectural or infrastructure decisions should include a cost assessment. This does not need a new governance gate — it can be added as a required dimension of the Architecture Gate.

3. **Post-Implementation Review** — After a release has been operational for a defined period, a review evaluates whether the delivered product achieved its goals. This closes the learning loop from delivery back to product strategy.

> **Action:** Add Feasibility Review as a formal checkpoint between Product and Engineering. Add cost dimension to the Architecture Gate. Define Post-Implementation Review as part of the project lifecycle Evolution phase.

---

## 7. Complexity Assessment

### 7.1 Overengineering Risks

| Area | Risk Level | Assessment |
|---|---|---|
| **7 organizations for Stage 1** | **High** | A single project does not need Portfolio, Operations, or Knowledge organizations. These functions have no work at Stage 1. |
| **42 metrics** | **High** | Measuring 42 metrics requires capturing, analyzing, and acting on 42 data streams. At Stage 1, this is surveillance theater. Start with 5–8 critical metrics. |
| **8 governance gates** | **High** | Every Work Package passes through gates. For a single project with one engineer equivalent, this means every code change triggers a multi-gate review process. The governance cost per unit of work is disproportionate. |
| **12-field decision traceability** | **Medium** | Every decision needs 12 fields recorded. At Stage 1, the Human Founder is making most decisions. Recording a 12-field decision record for each one is high-ceremony for low-ambiguity decisions. |
| **Capability Registry** | **Medium** | An abstraction layer for model routing when you likely have 1–2 models. Premature infrastructure. |
| **Cooling policies** | **Low** | Reasonable to define but unlikely to be needed at Stage 1. |

### 7.2 Underengineering Risks

| Area | Risk Level | Assessment |
|---|---|---|
| **Economic governance** | **High** | As identified in Section 5. No budget model, no cost tracking, no spending authority. |
| **Feasibility checkpoint** | **High** | No mechanism to catch infeasible requirements before they enter the roadmap. |
| **Agent reliability validation** | **High** | No mechanism to assess whether AI agents are actually performing their roles reliably. The design assumes agent capability but defines no quality assurance for agent outputs. |
| **Feedback loops from production** | **Medium** | The design covers building and deploying. It undercovers the loop from "deployed product" back to "product strategy" — is the thing we built actually working? |
| **Human Founder capacity model** | **Medium** | The human is the ultimate authority but there is no model for human capacity. How many decisions per week? How many reviews? What happens when the human is unavailable? |
| **Disaster recovery / continuity** | **Medium** | What happens if organizational state is lost? If the knowledge base is corrupted? If critical artifacts become inconsistent? There is no organizational continuity plan. |

### 7.3 MVP Risks

The primary MVP risk is that Karsa becomes an organizational design exercise that never ships software. The documents are comprehensive, well-structured, and internally consistent — but they describe a mature organization that has never been tested. The risk is **analysis paralysis at the organizational level**.

### 7.4 Organizational Risks

The design's own Risk Section 16 is thorough. The gap is that it does not include:

- **Organizational narcissism** — The organization becomes more interested in perfecting its own model than in producing useful software
- **Founder capacity collapse** — The single human becomes the bottleneck and the organization stalls
- **Cargo cult governance** — Governance gates are performed ritualistically but do not catch real issues because agent capabilities are insufficient for meaningful review

---

## 8. Minimum Viable Karsa

If I were implementing Karsa with the smallest viable organizational footprint, here is what I would keep, defer, and remove.

### 8.1 What Must Exist (Day 1)

| Element | Rationale |
|---|---|
| **Human Founder as authority** | Non-negotiable. All authority from human. |
| **Product function** | Someone must define what is built. |
| **Engineering function** | Someone must build it. |
| **Three governance gates** | Vision Gate (human approves what), Architecture Gate (design is reviewed), Release Gate (deployment is approved). All others can be deferred. |
| **Decision records** | Lightweight — just record what was decided and why. 4 fields, not 12. |
| **Single project** | Prove the model works for one project before scaling. |
| **Basic knowledge capture** | ADRs and post-mortems. That is the seed of organizational memory. |

### 8.2 What Can Be Deferred (Stage 2)

| Element | When to Activate |
|---|---|
| **Portfolio Organization** | When there are 2+ concurrent projects |
| **Operations Organization** | When the first project reaches production |
| **Knowledge Organization (as a distinct function)** | When there are 2+ projects generating cross-project learning |
| **AI Platform Organization** | When there are 2+ AI providers or cost management becomes non-trivial |
| **Capability Registry** | When provider routing decisions become frequent |
| **Full governance model (8 gates)** | When governance overhead is justified by organizational scale |
| **Full metrics suite** | When there is enough organizational activity to produce meaningful data |
| **Resource allocation model** | When resource contention exists between projects |
| **Escalation model** | When there are sufficient organizational functions to have conflicts |
| **Cooling policies** | When quota or budget constraints are encountered |

### 8.3 What Should Be Simplified Now

| Element | Current State | Recommended MVP |
|---|---|---|
| **Organizations** | 7 | 3 (Product, Engineering, Governance-lite) |
| **Governance gates** | 8 | 3 (Vision, Architecture, Release) |
| **Decision record fields** | 12 | 4 (Decision, Rationale, Authority, Date) |
| **Metrics** | 42 | 5–8 core health indicators |
| **Authority levels** | 8 | 3 (Human, Project Lead, Executing Role) |
| **Work Package types** | 5 | 2 (Design Package, Change Package) |
| **Compliance review types** | 5 | 1 (periodic health check) |
| **Organizational principles** | 12 | 5 most critical |

### 8.4 MVP Architecture Summary

```
Human Founder (all authority)
      │
      ├── Product Function
      │     └── Define what to build, manage scope
      │
      ├── Engineering Function
      │     └── Design architecture, build, test, deploy
      │
      └── Governance Function (lightweight)
            └── 3 gates: Vision, Architecture, Release
            └── Decision records (4 fields)
            └── ADRs for significant technical decisions

Knowledge Capture: ADRs + Post-mortems (no separate organization)
Metrics: 5-8 health indicators (not 42)
Portfolio: Not needed until Project 2
Operations: Not needed until Production
AI Platform: Direct model usage until provider management becomes complex
```

---

## 9. Architectural Risks — Next 12 Months

Ranked by composite of Severity × Likelihood × Impact.

| Rank | Risk | Severity | Likelihood | Impact | Description |
|---|---|---|---|---|---|
| **1** | Organizational overhead exceeds productive output | Critical | High | Critical | The organization spends more time governing, documenting, and reviewing than building. The first project never ships because the organizational infrastructure is never "ready." |
| **2** | Human Founder bottleneck | Critical | High | Critical | The single human cannot review, approve, and decide at the rate the organization generates requests. Work queues. Momentum dies. |
| **3** | Agent capability gap | High | High | High | AI agents cannot reliably perform the roles defined for them — particularly governance review, architectural reasoning, and knowledge transformation. The organizational model assumes capabilities that do not exist yet. |
| **4** | Knowledge capture without knowledge use | High | High | Medium | The organization diligently captures decision records, ADRs, and post-mortems — but no mechanism exists to surface this knowledge at the point of decision. Knowledge accumulates. It does not compound. |
| **5** | Governance provides false assurance | High | Medium | High | Governance gates are performed by AI agents that lack the judgment to catch real issues. Gates pass. Problems ship. The organization believes it has quality assurance when it has quality theater. |
| **6** | Premature multi-project operation | Medium | Medium | High | The organization attempts to manage multiple projects before the model is validated for one. Portfolio management, resource allocation, and cross-project coordination add complexity before the foundation is proven. |
| **7** | Research Vault circular dependency | Medium | Medium | Medium | Karsa depends on Research Vault for knowledge infrastructure. Research Vault depends on Karsa for governance and resources. One degrades; both degrade. |
| **8** | Organizational model rigidity | Medium | Low | High | The comprehensive organizational model becomes treated as scripture — too complete and well-documented to challenge. Evolution becomes difficult because changing anything requires updating multiple interconnected documents. |

---

## 10. Recommendations

### 10.1 Immediate Recommendations (Before First Project Ships)

| # | Recommendation | Rationale |
|---|---|---|
| **I-1** | **Define and implement Minimum Viable Karsa (Section 8.4).** Do not implement the full organizational model for the first project. | The current model is designed for a mature, multi-project organization. Applying it to a single project with a single founder will create more overhead than value. |
| **I-2** | **Define the Human Founder capacity model.** How many hours per week? How many decisions per cycle? What is the approval SLA? What happens during absence? | The human is the most constrained resource in the system and is currently unmodeled. |
| **I-3** | **Validate agent capabilities before assigning organizational roles.** Run structured capability assessments for each role before assuming agents can fill it. | Building an organization around unvalidated workforce capabilities is building on sand. |
| **I-4** | **Add Economic Governance.** Define budget categories, spending thresholds, and cost-per-project awareness. | An organization that does not understand its economics cannot make informed decisions. This is the largest gap in the current model. |
| **I-5** | **Define the "governance light" mode for Stage 1.** Which gates? How many fields? What is proportional governance at minimum scale? | The documents say governance is proportional but never define what proportional governance looks like at the smallest scale. |

### 10.2 Near-Term Recommendations (First 3–6 Months)

| # | Recommendation | Rationale |
|---|---|---|
| **N-1** | **Add Feasibility Review to the project lifecycle.** Before requirements enter the roadmap, Engineering validates feasibility. | Currently there is no checkpoint for "can we actually build this?" |
| **N-2** | **Add Post-Implementation Review to the project lifecycle.** After a release, evaluate whether it achieved its goals. | Currently the lifecycle covers building and deploying but not validating. |
| **N-3** | **Define knowledge retrieval mechanisms, not just knowledge capture.** How does past knowledge reach the current decision-maker at the moment of decision? | Knowledge that is captured but not surfaced is an archive, not institutional memory. |
| **N-4** | **Introduce agent output quality assurance.** Define how the organization validates that AI agents are performing their roles reliably. | The design assumes reliable agents. This assumption needs continuous validation. |
| **N-5** | **Activate organizational functions incrementally.** Do not stand up all 7 organizations. Activate each one when its workload justifies its existence. | Structure should follow demand, not precede it. |

### 10.3 Long-Term Recommendations (6–12 Months)

| # | Recommendation | Rationale |
|---|---|---|
| **L-1** | **Evaluate the Organizational Model's fitness after the first complete project lifecycle.** Is the model helping or hindering? What should change? | The model has never been tested. It should be evaluated against reality, not against its own internal logic. |
| **L-2** | **Consider whether the organizational model can be extracted as a reusable pattern.** Not as an immediate goal — but as an awareness that the "Operating System" framing may become relevant. | The model is general enough to be reusable. This optionality should be preserved. |
| **L-3** | **Address the shared workforce assumption with real AI operational data.** Do agents actually carry knowledge between projects? Does "reassignment" produce the claimed benefits? Measure it. | This is the assumption with the widest gap between the metaphor and reality. |
| **L-4** | **Evaluate whether the 7-organization structure should be reduced or consolidated.** Some organizations may prove to be capabilities, not standing functions. | Organizational structure should earn its complexity through demonstrated need. |
| **L-5** | **Stress-test the governance model.** Deliberately run a project with minimal governance and compare outcomes to a fully governed project. Is the governance actually catching problems, or is it ceremony? | The documents assume governance is net-positive. This should be proven, not assumed. |

---

## Closing

The Karsa design is ambitious, internally consistent, and intellectually impressive. The vision is compelling. The organizational model is thorough.

That is precisely what makes this review important. Well-designed systems fail not because their logic is flawed, but because their **assumptions are wrong**. The highest risks in Karsa are not in what the documents say — they are in what the documents assume:

- That AI agents can fill the roles defined for them
- That governance creates net value at small scale
- That one human can govern a growing organization
- That knowledge compounds automatically through process
- That organizational metaphors from human companies map to AI workforces

These are not fatal assumptions. They are testable hypotheses. The difference between a vision document and a working organization is whether those hypotheses are validated before the organization scales.

**Ship the first project. Validate the model. Then scale.**

---

*This review was produced by an Independent Enterprise Architect with no prior involvement in Karsa's design. It represents a critical assessment, not an endorsement or rejection.*
