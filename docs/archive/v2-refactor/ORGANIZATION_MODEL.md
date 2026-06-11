# Karsa — Organization Model

> *"Structure creates capability. Governance creates trust. Memory creates wisdom."*

**Document Status:** Living Document
**Last Updated:** 2026-06-10
**Revision:** 1
**Owner:** Organizational Design Agent
**Governing Document:** [VISION.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/vision/VISION.md)

---

## 1. Organizational Philosophy

### 1.1 How Karsa Views Organizations

An organization is not a collection of individuals performing tasks. An organization is a **system of relationships, responsibilities, authorities, and knowledge** — designed to produce outcomes that no individual could produce alone.

Karsa applies this understanding literally. It is not a swarm of autonomous agents each pursuing independent objectives. It is not a pipeline where tasks flow mechanically from one step to the next. It is a **governed, structured, knowledge-accumulating organization** where every role exists for a reason, every authority has boundaries, every action is accountable, and every outcome enriches the institution.

The organizational model is the product. The software is the output.

### 1.2 Accountability

Every action within Karsa is attributable to a specific organizational role with defined responsibilities. There are no anonymous decisions. There is no work without ownership. When something succeeds, the organization knows who contributed. When something fails, the organization knows where accountability lies — not for blame, but for learning and correction.

Accountability flows in two directions:

- **Upward** — Every role is accountable to its governing authority for the quality, timeliness, and governance compliance of its outputs
- **Lateral** — Every role is accountable to its peer organizations for honoring handoff contracts, respecting authority boundaries, and contributing to shared organizational goals

### 1.3 Authority

Authority in Karsa is **delegated, bounded, and revocable**. No role possesses inherent authority. All authority originates from the Human Founder and is delegated downward through the organizational hierarchy.

Delegated authority carries constraints:

- **Scope** — Authority applies only within a defined domain
- **Limits** — Authority has explicit boundaries beyond which escalation is required
- **Conditions** — Authority may be contingent on governance compliance
- **Revocability** — All delegated authority can be withdrawn by the granting authority

**Human authority is final.** No organizational process, no governance gate, and no escalation path supersedes the Human Founder's authority. Every decision in the organization can be overridden by human directive.

### 1.4 Governance

Governance is not bureaucracy. Governance is the organizational mechanism that creates **trust, consistency, and traceability**. Without governance, an organization cannot learn from its decisions because decisions are not recorded. Without governance, an organization cannot ensure quality because there are no standards to measure against. Without governance, an organization cannot scale because there is no way to maintain coherence across expanding scope.

**Autonomy without governance creates chaos.**

In Karsa, governance is embedded into every organizational function — not as an external review layer, but as an intrinsic property of how work is done. Governance should feel like structure, not friction.

### 1.5 Collaboration

Collaboration in Karsa is **structured, not ad-hoc**. Organizations collaborate through defined interfaces: handoff contracts, shared artifacts, and governed communication channels. This is not a limitation — it is the mechanism by which the organization maintains coherence as it scales.

Effective collaboration requires:

- **Shared language** — All organizations use consistent terminology and artifact formats
- **Explicit contracts** — Handoffs between organizations have defined inputs, outputs, and quality expectations
- **Mutual visibility** — Organizations can observe the state and health of peer organizations without requiring direct interrogation
- **Conflict resolution** — Disagreements are resolved through defined escalation paths, not through power dynamics or avoidance

### 1.6 Human Oversight

The Human Founder is the ultimate authority in all matters. Human oversight is not a constraint on the organization — it is the foundation upon which the organization's legitimacy rests.

Human oversight operates at multiple levels:

- **Strategic oversight** — Setting organizational direction, approving portfolio composition, and defining success criteria
- **Approval oversight** — Reviewing and approving critical artifacts, architectural decisions, and release candidates
- **Exception oversight** — Resolving conflicts, overriding decisions, and intervening when organizational processes produce unacceptable outcomes
- **Evolutionary oversight** — Approving changes to the organizational model itself, including role definitions, governance processes, and authority structures

The organization is designed to minimize the need for human intervention in routine operations — but never to eliminate the ability to intervene.

---

## 2. Organizational Purpose

### 2.1 Primary Organizational Output

Karsa exists to produce one thing: **Approved Work Packages**.

An Approved Work Package is a governed, reviewed, and authorized unit of work that has passed through all required organizational gates and is ready for its intended purpose — whether that purpose is production deployment, further development, architectural evolution, or organizational improvement.

### 2.2 Work Package Types

The organization produces several categories of Approved Work Packages:

| Work Package Type | Description | Primary Gate |
|---|---|---|
| **Design Package** | Approved architectural designs, technical approaches, and system specifications | Architecture Review |
| **Change Package** | Approved code changes, configuration updates, and system modifications | Engineering Review + Governance Approval |
| **Release Package** | Approved production-ready deliverables with full quality and compliance verification | Release Approval |
| **Decision Package** | Approved strategic, architectural, or organizational decisions with full rationale and traceability | Authority Approval |
| **Knowledge Package** | Approved organizational learning artifacts — post-mortems, pattern libraries, decision records | Knowledge Review |

### 2.3 What Makes a Work Package "Approved"

A Work Package achieves "Approved" status only when:

1. It has been produced by the responsible organizational function
2. It has been reviewed by the appropriate peer function
3. It has passed all applicable governance gates
4. It has been authorized by the appropriate authority level
5. Its decision rationale has been recorded for organizational memory
6. It does not contradict any higher-level artifact in the artifact hierarchy

No work product is considered organizationally valid until it has achieved Approved status through the appropriate governance process.

---

## 3. Organizational Structure

Karsa is organized into **seven major organizational functions**, each with a distinct purpose, clear responsibilities, defined success metrics, and explicit decision authority. These are not teams — they are **organizational functions** that will eventually be staffed by specialized roles.

### 3.1 Portfolio Organization

**Purpose:** To manage Karsa's portfolio of projects as a unified strategic entity — making investment decisions, prioritization tradeoffs, and resource allocation choices that maximize organizational value.

**Responsibilities:**

- Maintain the portfolio backlog and project registry
- Prioritize projects based on strategic value, resource availability, and organizational capacity
- Allocate shared resources across competing project demands
- Monitor portfolio health, balance, and strategic alignment
- Identify cross-project dependencies, synergies, and conflicts
- Recommend project initiation, continuation, pausing, or sunsetting
- Report portfolio status and strategic recommendations to the Human Founder

**Success Metrics:**

- Portfolio strategic alignment score
- Resource utilization across the portfolio
- Cross-project dependency conflict rate
- Time from idea acceptance to project initiation
- Portfolio balance across risk profiles and maturity stages

**Key Decisions:**

- Project prioritization ranking
- Resource allocation across projects
- Project lifecycle transitions (initiate, pause, resume, sunset)
- Cross-project tradeoff resolution

---

### 3.2 Product Organization

**Purpose:** To define *what* is built and *why* — translating rough ideas into clear product visions, requirements, and roadmaps that can be executed by the Engineering Organization.

**Responsibilities:**

- Transform ideas into structured product visions and requirements
- Define product roadmaps, milestones, and success criteria
- Prioritize features and capabilities within each project
- Manage scope and ensure alignment with the approved vision
- Define acceptance criteria for deliverables
- Represent the user perspective in organizational decision-making
- Coordinate with the Portfolio Organization on strategic alignment

**Success Metrics:**

- Requirements clarity and completeness
- Scope stability (change rate after approval)
- Stakeholder alignment on product direction
- Feature acceptance rate at delivery
- Vision-to-roadmap traceability

**Key Decisions:**

- Product requirements and priorities
- Feature scope and acceptance criteria
- Product roadmap sequencing
- Scope change requests (subject to governance review)

---

### 3.3 Engineering Organization

**Purpose:** To define *how* things are built and to execute the construction, testing, and integration of software with technical excellence and professional discipline.

**Responsibilities:**

- Design system architectures and technical approaches
- Execute software construction, testing, and integration
- Maintain engineering standards, patterns, and practices
- Conduct code reviews and technical quality assurance
- Manage technical debt and architectural evolution
- Produce Architecture Decision Records for all significant technical choices
- Coordinate with the Product Organization on feasibility and technical tradeoffs

**Success Metrics:**

- Code quality and test coverage
- Architecture decision record completeness
- Technical debt trajectory
- Build and integration reliability
- Engineering standards compliance rate

**Key Decisions:**

- Architecture and design choices (within approved constraints)
- Technical approach selection
- Engineering standards and patterns
- Technical debt prioritization
- Build and integration strategy

---

### 3.4 Operations Organization

**Purpose:** To ensure that what is built runs reliably, securely, and observably in production — and that operational incidents become organizational learning assets.

**Responsibilities:**

- Manage deployment, release, and rollback processes
- Monitor system health, performance, and availability
- Manage incidents, outages, and operational emergencies
- Conduct post-mortems and produce incident learning artifacts
- Define and enforce operational standards (reliability, security, observability)
- Manage environment configurations and infrastructure-as-code governance
- Coordinate with the Engineering Organization on operability requirements

**Success Metrics:**

- System availability and reliability
- Incident response time and resolution time
- Post-mortem completion rate and quality
- Deployment success rate
- Operational standard compliance

**Key Decisions:**

- Deployment timing and strategy
- Incident response actions
- Rollback decisions
- Operational readiness assessments
- Post-mortem findings and corrective actions

---

### 3.5 Governance Organization

**Purpose:** To ensure that all organizational work adheres to defined standards, that decisions are traceable, that quality gates are enforced, and that the organization maintains its integrity as it scales.

**Responsibilities:**

- Define and maintain organizational governance standards
- Operate approval gates for all Work Package types
- Conduct compliance reviews and audits
- Enforce artifact hierarchy consistency
- Maintain the organizational decision registry
- Monitor governance health across all organizational functions
- Recommend governance process improvements based on organizational learning
- Ensure accountability is maintained for all organizational actions

**Success Metrics:**

- Governance gate compliance rate
- Decision traceability completeness
- Artifact hierarchy violation rate
- Governance process cycle time (time from submission to decision)
- Organizational standard currency (freshness and relevance)

**Key Decisions:**

- Governance standard definitions and updates
- Compliance findings and required remediation
- Artifact hierarchy violation rulings
- Governance process changes (subject to Human Founder approval)
- Organizational standard enforcement actions

---

### 3.6 Knowledge Organization

**Purpose:** To serve as the **learning engine** of Karsa — transforming raw organizational experiences into institutional intelligence that compounds over time and makes the organization progressively more capable with every project, every decision, and every outcome.

The Knowledge Organization does not merely store information. It **transforms experiences into organizational wisdom**. Its output is not a filing system — it is a living body of institutional intelligence that actively improves the quality, speed, and reliability of all organizational functions.

#### Documentation, Knowledge, and Learning

The Knowledge Organization operates across three distinct tiers of organizational intelligence. These tiers are not synonyms — they represent fundamentally different levels of value, and the Knowledge Organization's primary responsibility is to drive information upward through these tiers.

| Tier | Definition | Example | Organizational Value |
|---|---|---|---|
| **Documentation** | The raw record of what happened — facts, artifacts, logs, and records. Documentation is captured; it is not interpreted. | A decision record stating that Provider X was selected for capability Y | Low on its own. Documentation is necessary but not sufficient. A perfectly documented organization that never learns from its documents has gained nothing. |
| **Knowledge** | The understood patterns, principles, and insights extracted from documentation. Knowledge is interpreted; it answers *why*, not just *what*. | An analysis showing that Provider X consistently underperforms on capability Y during peak hours, leading to a recommendation to route peak-hour requests to Provider Z | Medium. Knowledge informs specific decisions and prevents specific mistakes. But knowledge is still reactive — it explains what has already happened. |
| **Learning** | The organizational intelligence that changes how the organization operates. Learning is transformative; it modifies behavior, standards, processes, and decision-making frameworks. | A new organizational standard that requires all critical capabilities to have peak-hour fallback routing, derived from the Provider X pattern — and now applied across all providers and all capabilities | High. Learning changes the organization itself. It does not just inform a decision — it improves the decision-making system. Learning is how knowledge compounds. |

The Knowledge Organization's fundamental mission is to ensure that Karsa does not stop at documentation. Every significant organizational experience must be driven through the full progression:

```
Experience → Documentation → Knowledge → Learning → Organizational Improvement
```

An organization that documents but does not learn is an archive. An organization that learns but does not apply its learning is an academy. Karsa must be neither — it must be an **institution that transforms experience into action**.

#### Responsibilities

**Documentation Responsibilities:**

- Define documentation standards and formats for all organizational artifacts
- Ensure organizational events, decisions, and outcomes are recorded with sufficient context
- Maintain the organizational documentation taxonomy and ensure discoverability
- Coordinate with Research Vault for durable, versioned documentation preservation
- Monitor documentation health — identifying gaps, staleness, and completeness issues

**Knowledge Responsibilities:**

- Analyze documentation to identify patterns, trends, and causal relationships across projects and organizational functions
- Extract transferable insights from project outcomes, incident analyses, governance findings, and resource allocation results
- Curate cross-project knowledge — ensuring that insights from one project are accessible and relevant to other projects
- Maintain pattern libraries and anti-pattern registries that distill organizational experience into reusable knowledge
- Produce organizational knowledge reports — synthesizing what the organization has learned across defined periods

**Learning Responsibilities:**

- Identify recurring patterns in organizational knowledge that indicate opportunities for systemic improvement
- Extract best practices from successful outcomes and formalize them as organizational recommendations
- Propose organizational standards evolution — recommending changes to standards, processes, and governance based on accumulated evidence
- Develop institutional wisdom — the deep organizational understanding of what works, what fails, and why, that transcends any individual project or decision
- Drive knowledge compounding — ensuring that each new piece of organizational intelligence builds upon and enriches what came before
- Assess organizational learning effectiveness — measuring whether captured knowledge is actually changing organizational behavior and producing better outcomes

**Cross-Cutting Responsibilities:**

- Facilitate cross-project learning sessions — structured processes where insights from one project are evaluated for applicability to other projects
- Maintain the organizational precedent base — a searchable collection of past decisions, their rationale, their outcomes, and their applicability to future decisions
- Monitor knowledge decay risk — proactively identifying when organizational knowledge is becoming stale, disconnected, or unused
- Serve as the organizational memory of process evolution — documenting how and why organizational structures, workflows, and governance have changed over time
- Advise other organizational functions on relevant institutional knowledge when they face decisions similar to past organizational experiences

#### How the Knowledge Organization Operates

The Knowledge Organization is not a passive archive. It is an **active organizational function** that operates through three modes:

| Mode | Description |
|---|---|
| **Capture** | Ensuring that organizational experiences are documented — monitoring that decision records are created, post-mortems are completed, review findings are recorded, and outcomes are assessed |
| **Transform** | Analyzing captured documentation to extract knowledge and learning — identifying patterns, deriving insights, proposing best practices, and recommending organizational improvements |
| **Distribute** | Ensuring that knowledge and learning reach the organizational functions that need them — pushing relevant knowledge to decision-makers, publishing pattern analyses, and advising on precedent when similar decisions arise |

The most common organizational failure mode is capturing documentation and assuming the job is done. The Knowledge Organization exists to ensure that documentation is only the beginning — that the organization invests the effort to transform raw records into actionable intelligence and then distributes that intelligence to where it can improve outcomes.

**Success Metrics:**

- Knowledge capture rate (percentage of significant decisions and events with recorded documentation)
- Knowledge discoverability (time to find relevant organizational precedent)
- Cross-project knowledge reuse rate (frequency of cross-project knowledge application)
- Knowledge staleness index (percentage of knowledge artifacts past their review cycle)
- Documentation-to-learning conversion rate (percentage of documented events that produce extractable learning)
- Organizational learning application rate (percentage of identified learnings that produce measurable changes in organizational behavior)
- Best practice adoption rate (percentage of formalized best practices adopted across the portfolio)

**Key Decisions:**

- Knowledge taxonomy and organizational structure
- Documentation and knowledge capture standards
- Knowledge retention, review, and archival policies
- Best practice formalization and publication
- Organizational standards evolution recommendations (subject to Governance Authority approval)
- Cross-project pattern identification and distribution priorities
- Knowledge system evolution

---

### 3.7 AI Platform Organization

**Purpose:** To manage the AI capabilities that power Karsa's workforce — ensuring reliable, cost-effective, and governed access to AI capabilities while abstracting provider-specific details from all other organizational functions.

**Responsibilities:**

- Maintain the organizational Capability Registry — a catalog of AI capabilities available to the workforce
- Govern model selection, ensuring capability-based assignment rather than direct model specification
- Manage provider relationships, quotas, budgets, and cost optimization
- Define and enforce prompt standards and interaction patterns
- Monitor workforce health — availability, latency, quality, and cost per capability
- Manage capacity forecasting based on portfolio demand projections
- Define cooling policies, rate limiting, and workload distribution strategies
- Maintain fallback strategies for provider degradation or outage scenarios
- Report AI platform health and cost metrics to the Portfolio Organization

**Success Metrics:**

- Capability availability (uptime of requested capabilities)
- Cost per capability unit
- Provider diversification index
- Workforce health score (quality, latency, availability composite)
- Capacity forecast accuracy
- Prompt standard compliance rate

**Key Decisions:**

- Capability-to-provider mapping
- Budget allocation across capability categories
- Provider selection, onboarding, and offboarding
- Cooling and throttling policy activation
- Fallback strategy activation
- Capacity scaling decisions

**Why Capability-Based Assignment:**

Organizations request capabilities — *"I need code review capability"* — not specific models — *"I need GPT-4o"*. This abstraction is critical for three reasons:

1. **Decoupling** — Organizational functions remain independent of provider-specific details. Provider changes do not cascade into organizational process changes.
2. **Optimization** — The AI Platform Organization can route capability requests to the most cost-effective, available, and appropriate provider without burdening requesting organizations with that decision.
3. **Governance** — Centralizing provider decisions enables consistent cost management, quota governance, and quality monitoring that would be impossible if every organizational function selected its own models independently.

---

## 4. Authority Model

### 4.1 Authority Hierarchy

Authority in Karsa flows from the Human Founder downward through delegated authority levels. Each level has defined rights and constraints.

| Authority Level | Scope | Held By |
|---|---|---|
| **Organizational Authority** | All organizational decisions, all overrides, all exceptions | Human Founder |
| **Portfolio Authority** | Portfolio composition, cross-project prioritization, organizational resource allocation | Portfolio Organization Lead |
| **Product Authority** | Product vision, requirements, roadmap, scope within a project | Product Organization Lead (per project) |
| **Engineering Authority** | Architecture, technical approach, engineering standards within a project | Engineering Organization Lead (per project) |
| **Governance Authority** | Governance standards, compliance enforcement, approval gate management | Governance Organization Lead |
| **Operational Authority** | Deployment decisions, incident response, operational standards | Operations Organization Lead |
| **Knowledge Authority** | Knowledge standards, taxonomy, retention policies | Knowledge Organization Lead |
| **Platform Authority** | Capability governance, provider management, cost and quota policies | AI Platform Organization Lead |

### 4.2 Rights Matrix

| Authority Level | Approve | Reject | Escalate | Override |
|---|---|---|---|---|
| **Organizational (Human)** | All decisions | All decisions | N/A (final authority) | All decisions |
| **Portfolio** | Project prioritization, resource allocation, project lifecycle transitions | Misaligned project proposals | To Organizational Authority | Product and Engineering decisions when portfolio coherence is at risk |
| **Product** | Requirements, scope, acceptance criteria | Engineering proposals that violate product intent | To Portfolio Authority | N/A |
| **Engineering** | Architecture, technical approach, engineering standards | Product requests that are technically infeasible | To Portfolio Authority | N/A |
| **Governance** | Compliance certifications, governance gate passage | Non-compliant Work Packages | To Organizational Authority | N/A (but can block any non-compliant action) |
| **Operational** | Deployments, operational readiness | Releases that fail operational criteria | To Engineering or Portfolio Authority | Emergency rollback decisions |
| **Knowledge** | Knowledge artifacts, taxonomy changes | Low-quality knowledge submissions | To Governance Authority | N/A |
| **Platform** | Capability assignments, provider changes, cost policies | Requests exceeding budget or quota | To Portfolio Authority | Capability routing for cost or availability reasons |

### 4.3 Conflict Resolution Principles

When authorities conflict, resolution follows these principles in order:

1. **Human authority is final.** Any conflict can be resolved by the Human Founder at any time.
2. **Higher authority prevails.** Portfolio Authority overrides Project-level authority. Organizational Authority overrides all.
3. **Governance has blocking power.** Governance Authority cannot force a decision, but it can block any action that violates organizational standards until compliance is achieved or an explicit override is granted.
4. **Escalation is mandatory, not optional.** When a conflict cannot be resolved at the current level, escalation to the next level is a requirement, not a suggestion. Unresolved conflicts do not persist — they escalate.
5. **Escalation has a time bound.** Unresolved escalations that exceed a defined time threshold automatically escalate to the next authority level. Conflicts do not stall the organization.
6. **Decisions are recorded.** Every conflict resolution — including the rationale, the alternatives considered, and the final ruling — is recorded in the organizational decision registry.

---

## 5. Artifact Hierarchy

### 5.1 Hierarchy Definition

Karsa maintains a strict hierarchy of organizational artifacts. Higher-level artifacts govern and constrain lower-level artifacts. No artifact may contradict an artifact above it in the hierarchy.

```
Organizational Vision
        │
        ▼
Organizational Model
        │
        ▼
  Domain Vision
        │
        ▼
Domain Architecture
        │
        ▼
  Project Roadmap
        │
        ▼
Implementation Plan
        │
        ▼
  Execution Artifact
```

### 5.2 Artifact Level Definitions

| Level | Artifact | Description | Authority |
|---|---|---|---|
| **L1** | Organizational Vision | The purpose, mission, principles, and strategic direction of Karsa | Human Founder |
| **L2** | Organizational Model | The organizational structure, governance model, authority model, and operating principles | Human Founder |
| **L3** | Domain Vision | The vision, scope, and strategic goals for a specific product or domain | Product Authority (approved by Human Founder) |
| **L4** | Domain Architecture | The architectural design, technical constraints, and design decisions for a specific domain | Engineering Authority (reviewed by Governance) |
| **L5** | Project Roadmap | The sequenced plan of milestones, deliverables, and timelines for a project | Product Authority (approved by Portfolio Authority) |
| **L6** | Implementation Plan | The detailed plan for executing a specific milestone or work item | Engineering Authority |
| **L7** | Execution Artifact | The actual deliverable — code, configuration, documentation, test results | Executing Role |

### 5.3 Governance Implications

**Downward Consistency Rule:** An artifact at level N must be consistent with all artifacts at levels 1 through N-1. If an inconsistency is detected, the lower-level artifact must be revised — the higher-level artifact is assumed correct unless explicitly changed through its own governance process.

**Upward Change Propagation:** If a lower-level artifact reveals that a higher-level artifact needs revision (e.g., implementation reveals an architectural flaw), the change must be proposed upward through the appropriate authority and governance channels. The lower-level artifact does not unilaterally override the higher-level one.

**Cross-Branch Consistency:** When two projects share a higher-level artifact (e.g., both are governed by the same Organizational Model), their respective lower-level artifacts must not contradict each other in ways that violate the shared ancestor. The Governance Organization monitors cross-branch consistency.

**Artifact Immutability After Approval:** Once an artifact achieves Approved status at a given level, it is immutable until a formal change request is processed through the appropriate governance gate. Informal modifications are not recognized by the organization.

---

## 6. Project Management Model

### 6.1 Project Lifecycle

Every project in Karsa progresses through a defined lifecycle. Each phase has explicit entry criteria, governing activities, and exit criteria.

| Phase | Purpose | Entry Criteria | Exit Criteria |
|---|---|---|---|
| **Proposal** | Capture and evaluate a new idea | Idea submitted to Portfolio Organization | Proposal accepted or rejected by Portfolio Authority |
| **Discovery** | Transform the idea into a clear vision and scope | Proposal accepted | Domain Vision approved by Human Founder |
| **Planning** | Produce a roadmap and initial architecture | Domain Vision approved | Roadmap approved by Portfolio Authority; Architecture approved by Engineering and Governance |
| **Execution** | Build, test, and integrate the software | Roadmap and Architecture approved | Milestone deliverables pass all governance gates |
| **Release** | Prepare and deploy to production | Execution milestone approved | Release Package approved by Operations and Governance |
| **Operation** | Monitor, maintain, and respond to incidents | Release deployed | Ongoing; governed by operational standards |
| **Evolution** | Iterate based on feedback and learning | Operational baseline established | New roadmap items feeding back into Planning |
| **Sunset** | Decommission and archive | Sunset decision approved by Portfolio Authority and Human Founder | System decommissioned; knowledge archived |

### 6.2 Project Ownership

Every project has a clear ownership structure:

| Role | Responsibility |
|---|---|
| **Project Sponsor** | The Human Founder — approves vision, authorizes resources, and retains ultimate authority |
| **Portfolio Owner** | The Portfolio Organization — manages project priority within the portfolio context |
| **Product Owner** | The Product Organization — defines what is built and why |
| **Technical Owner** | The Engineering Organization — defines how it is built and ensures technical excellence |
| **Operational Owner** | The Operations Organization — ensures reliability, security, and observability in production |

No project exists without explicit ownership at all five levels.

### 6.3 Project Prioritization

Projects are prioritized at the portfolio level using a multi-dimensional assessment:

| Dimension | Description |
|---|---|
| **Strategic Value** | How well does this project align with organizational vision and goals? |
| **Resource Demand** | What organizational capacity does this project require? |
| **Risk Profile** | What are the technical, operational, and organizational risks? |
| **Dependency Impact** | Does this project block or enable other portfolio projects? |
| **Knowledge Value** | Will this project generate organizational learning that benefits future projects? |
| **Maturity Stage** | Where is this project in its lifecycle and what phase-appropriate investment is needed? |

Prioritization is reviewed periodically and whenever significant portfolio changes occur (new project proposals, resource constraints, strategic shifts).

### 6.4 Project Health

Project health is monitored continuously across multiple dimensions:

| Health Dimension | Healthy | Warning | Critical |
|---|---|---|---|
| **Schedule** | On track | Milestones at risk | Milestones missed |
| **Scope** | Stable | Scope creep detected | Uncontrolled scope changes |
| **Quality** | Governance gates passing | Gate failures increasing | Repeated gate failures |
| **Resource** | Adequately staffed | Capacity concerns | Resource starvation |
| **Governance** | Fully compliant | Minor compliance gaps | Governance violations |
| **Knowledge** | Artifacts current | Knowledge gaps emerging | Significant knowledge loss |

### 6.5 Project Escalation

Escalation triggers within projects:

| Trigger | Escalation Path |
|---|---|
| Milestone missed without recovery plan | Project → Portfolio Authority |
| Unresolved Product-Engineering disagreement | Project → Portfolio Authority |
| Governance gate failure without remediation path | Project → Governance Authority → Portfolio Authority |
| Resource starvation affecting delivery | Project → Portfolio Authority |
| Critical incident in production | Operations → Portfolio Authority → Human Founder |
| Any unresolved conflict exceeding time threshold | Current level → Next authority level |

### 6.6 Multi-Project Coordination

Projects do not operate as isolated silos. The Portfolio Organization maintains:

- **Cross-project dependency map** — Identifying where projects depend on, share with, or conflict with each other
- **Shared resource schedule** — Ensuring workforce allocation across projects is coordinated, not competitive
- **Knowledge bridge** — Ensuring learning from one project is available to all others
- **Governance consistency** — Ensuring all projects operate under the same organizational standards

---

## 7. Resource Management Model

### 7.1 Shared Workforce Concept

Karsa maintains a **shared organizational workforce** — a pool of specialized capabilities that can be allocated across projects based on organizational priorities. Roles are not permanently assigned to projects. They are assigned based on current demand, priority, and capacity.

This shared model creates three advantages:

1. **Efficiency** — Specialized capabilities are utilized across the portfolio, not idle within a single project
2. **Knowledge transfer** — Roles carry organizational learning between projects, enriching execution everywhere
3. **Flexibility** — The organization can rapidly shift capacity to where it is most needed

### 7.2 Capacity Planning

Capacity planning is an organizational function — not a project function. The Portfolio Organization, in coordination with the AI Platform Organization, maintains:

- **Current capacity assessment** — What capabilities are available and at what capacity?
- **Demand forecast** — What capabilities will the portfolio need over upcoming planning horizons?
- **Gap analysis** — Where will demand exceed capacity, and what are the mitigation options?
- **Capacity allocation plan** — How is available capacity distributed across portfolio priorities?

Capacity planning operates on a rolling basis, updated as portfolio composition, project phases, and resource availability change.

### 7.3 Resource Allocation

Resource allocation follows a priority-based model:

| Priority Tier | Description | Allocation Behavior |
|---|---|---|
| **Critical** | Production incidents, security emergencies, governance-mandated actions | Immediate allocation; may preempt lower-priority work |
| **High** | Active execution milestones for top-priority projects | Guaranteed allocation within capacity constraints |
| **Normal** | Standard project work across the portfolio | Allocated based on available capacity after higher-priority commitments |
| **Low** | Background improvements, non-urgent knowledge work, exploratory tasks | Best-effort allocation; deferred when capacity is constrained |
| **Deferred** | Work explicitly paused due to resource constraints or strategic decision | No allocation until reclassified |

### 7.4 Utilization Management

The organization monitors its resource utilization to prevent both waste and burnout:

- **Over-allocation** — When demand consistently exceeds capacity, triggering workforce scaling or portfolio reprioritization
- **Under-allocation** — When capacity sits idle, triggering proactive work assignment or capacity reduction
- **Concentration risk** — When critical capabilities are concentrated in too few resources, creating fragility
- **Context-switching cost** — When resources are spread across too many projects, reducing effectiveness

### 7.5 Multi-Project Coordination

When multiple projects compete for the same resources:

1. Portfolio prioritization determines allocation order
2. Resource conflicts are surfaced to the Portfolio Authority
3. Tradeoff decisions are recorded in the organizational decision registry
4. Affected projects are notified of allocation changes and expected impact
5. Re-prioritization decisions can be escalated to the Human Founder if portfolio-level resolution is insufficient

---

## 8. Governance Model

> *"Autonomy without governance creates chaos."*

### 8.1 Governance Philosophy

Governance exists to create trust. It is the mechanism by which the organization ensures that its outputs are reliable, its decisions are sound, and its processes are consistent. Governance is not a tax on productivity — it is an investment in organizational integrity.

Effective governance is:

- **Proportional** — The depth of governance review is proportional to the risk and impact of the decision
- **Embedded** — Governance is part of the workflow, not an afterthought appended at the end
- **Traceable** — Every governance decision is recorded with its rationale
- **Learnable** — Governance findings feed back into organizational knowledge, improving future work
- **Consistent** — The same standards apply across all projects in the portfolio

### 8.2 Approval Gates

| Gate | What It Governs | Who Approves | Who Reviews |
|---|---|---|---|
| **Vision Gate** | Domain Vision documents | Human Founder | Product Organization, Portfolio Organization |
| **Architecture Gate** | Architecture designs and significant technical decisions | Engineering Authority | Governance Organization, Product Organization |
| **Scope Gate** | Scope changes after initial approval | Product Authority | Portfolio Organization, Governance Organization |
| **Quality Gate** | Engineering deliverables meeting quality standards | Engineering Authority | Governance Organization |
| **Security Gate** | Security compliance of deliverables and infrastructure | Governance Authority | Engineering Organization, Operations Organization |
| **Release Gate** | Production readiness of a release candidate | Operations Authority + Governance Authority | Engineering Organization, Product Organization |
| **Decision Gate** | Significant organizational or strategic decisions | Appropriate Authority Level | Governance Organization |
| **Knowledge Gate** | Quality and completeness of organizational learning artifacts | Knowledge Authority | Governance Organization |

### 8.3 Compliance Reviews

The Governance Organization conducts periodic compliance reviews across all organizational functions:

| Review Type | Scope | Frequency |
|---|---|---|
| **Artifact Consistency Review** | Verify lower-level artifacts do not contradict higher-level artifacts | At each governance gate |
| **Governance Health Review** | Assess governance process effectiveness across the organization | Periodic |
| **Standards Compliance Review** | Verify adherence to organizational standards (engineering, operational, knowledge) | Periodic |
| **Decision Traceability Audit** | Verify that significant decisions have recorded rationale and approval | Periodic |
| **Cross-Project Consistency Review** | Verify that shared standards are applied consistently across the portfolio | At portfolio review intervals |

### 8.4 Architecture Reviews

Architecture reviews serve dual purposes: **quality assurance** and **knowledge creation**.

Every architecture review produces:

1. **Approval or rejection** of the proposed design
2. **An Architecture Decision Record (ADR)** capturing the decision, rationale, alternatives considered, and tradeoffs accepted
3. **Cross-project impact assessment** — Does this decision affect, conflict with, or enable decisions in other projects?
4. **Knowledge contribution** — Patterns, anti-patterns, and lessons captured for organizational memory

Architecture reviews are governed by the Engineering Authority and monitored by the Governance Organization.

### 8.5 Release Approvals

A release achieves Approved status only when:

1. All Quality Gates for included deliverables have passed
2. The Security Gate has been cleared
3. Operational readiness criteria are satisfied
4. The Operations Organization has confirmed deployment feasibility
5. The Governance Organization has verified compliance with organizational standards
6. The Product Organization has confirmed that the release meets acceptance criteria
7. The release decision has been recorded with full traceability

### 8.6 Decision Traceability

Every significant organizational decision is recorded in the organizational decision registry with:

| Field | Description |
|---|---|
| **Decision ID** | Unique identifier |
| **Decision** | What was decided |
| **Context** | What circumstances led to this decision |
| **Alternatives** | What other options were considered |
| **Rationale** | Why this option was chosen over alternatives |
| **Authority** | Who had the authority to make this decision |
| **Approver** | Who specifically approved it |
| **Impact** | What is affected by this decision |
| **Reversibility** | Can this decision be reversed, and at what cost? |
| **Date** | When the decision was made |
| **Status** | Active, superseded, or revoked |

---

## 9. Knowledge Management Model

### 9.1 Organizational Memory

Organizational memory is the accumulated knowledge, decisions, patterns, and lessons that represent everything the organization has learned. It is not a filing system — it is a **strategic asset** that makes the organization progressively more capable.

Organizational memory encompasses:

- **Declarative knowledge** — Facts, standards, specifications, and documented decisions
- **Procedural knowledge** — How things are done, why processes exist, and what workflows have proven effective
- **Experiential knowledge** — Lessons learned from successes, failures, incidents, and near-misses
- **Contextual knowledge** — The circumstances, constraints, and reasoning behind past decisions

### 9.2 Decision History

Every significant organizational decision is preserved with full context. Decision history serves three purposes:

1. **Traceability** — The organization can always explain why a decision was made
2. **Learning** — Future decision-makers can review how similar decisions were handled in the past
3. **Precedent** — Recurring decision types accumulate a body of precedent that accelerates and improves future decision-making

Decision history is maintained by the Governance Organization and made discoverable through the Knowledge Organization.

### 9.3 Lessons Learned

The organization captures lessons learned from every significant event:

| Source | Lesson Type | Capture Trigger |
|---|---|---|
| **Project completion** | What worked, what didn't, what should be repeated or avoided | Project phase transition |
| **Incident resolution** | Root cause, response effectiveness, prevention measures | Post-mortem completion |
| **Architecture review** | Design patterns that succeeded or failed, tradeoffs that proved correct or incorrect | Architecture Decision Record creation |
| **Governance findings** | Common compliance issues, governance friction points, process improvement opportunities | Compliance review completion |
| **Resource allocation outcomes** | Capacity planning accuracy, allocation strategy effectiveness | Planning cycle review |

### 9.4 Incident Learning

Incidents are not merely resolved — they are **transformed into organizational learning assets**:

1. Every incident produces a post-mortem
2. Every post-mortem identifies root causes, contributing factors, and systemic improvements
3. Post-mortem findings are cross-referenced with past incidents to identify patterns
4. Identified patterns are elevated to organizational knowledge — informing standards, processes, and future decision-making
5. Post-mortem quality is reviewed by the Knowledge Organization to ensure learning value

### 9.5 Cross-Project Learning

Knowledge must flow across project boundaries:

- **Pattern libraries** — Successful architectural patterns, engineering approaches, and operational strategies are cataloged and made available to all projects
- **Anti-pattern registries** — Approaches that failed or caused problems are documented so they are not repeated
- **Decision precedents** — Decisions made in one project provide context and precedent for similar decisions in other projects
- **Shared post-mortems** — Incident learnings from one project are assessed for applicability to all projects in the portfolio

The Knowledge Organization is responsible for facilitating cross-project knowledge flow. Knowledge does not transfer automatically — it must be curated, indexed, and actively connected to relevant contexts.

### 9.6 Knowledge Compounding

Knowledge compounding is the organizational principle that each piece of captured knowledge makes future knowledge more valuable. This creates a positive feedback loop:

```
Decisions → Records → Patterns → Standards → Better Decisions → Better Records → ...
```

Over time, the organization's knowledge base creates compound returns:

- **Early projects** produce foundational decisions and initial patterns
- **Subsequent projects** benefit from existing patterns and produce refined patterns
- **Mature projects** operate with a rich body of precedent, dramatically reducing decision time and error rate
- **The organization itself** evolves its processes based on accumulated wisdom, becoming structurally better at producing and using knowledge

The goal is not to accumulate the most knowledge — it is to accumulate the **most useful** knowledge, organized so that it informs decisions at the point where those decisions are made.

---

## 10. Relationship with Research Vault

### 10.1 Overview

Research Vault is a project within the Karsa portfolio — but it has a special organizational relationship with Karsa itself. Research Vault serves as Karsa's **long-term knowledge infrastructure**, providing capabilities that the organization depends on for institutional memory, knowledge discovery, and learning.

### 10.2 Organizational Relationship

Research Vault and Karsa are **separate but symbiotic**:

| Dimension | Karsa | Research Vault |
|---|---|---|
| **Identity** | The organization | A project within the organization |
| **Scope** | Organizational model, governance, workflows, authority | Knowledge storage, retrieval, organization, and discovery |
| **Relationship** | Producer and consumer of knowledge | Curator and provider of knowledge infrastructure |
| **Governance** | Governed by Karsa's organizational model | Governed by Karsa's organizational model (as a portfolio project) |

Research Vault is governed by Karsa. Karsa depends on Research Vault. They are not merged — they are integrated through defined organizational interfaces.

### 10.3 How Research Vault Supports Karsa

| Capability | How It Supports Karsa |
|---|---|
| **Artifact Repository** | Provides durable, versioned storage for all organizational artifacts — from vision documents to execution records |
| **Decision History** | Maintains the searchable, cross-referenced decision registry that powers governance traceability |
| **Institutional Memory** | Preserves organizational knowledge in a form that survives individual agent lifecycles and project transitions |
| **Learning System** | Enables cross-project knowledge discovery, pattern identification, and precedent retrieval |
| **Knowledge Discovery** | Provides search and retrieval capabilities that allow any organizational function to find relevant past knowledge |

### 10.4 Integration Principles

- **Research Vault does not govern Karsa.** It provides knowledge infrastructure; it does not make organizational decisions.
- **Karsa does not bypass Research Vault's project governance.** Research Vault is a portfolio project and is subject to the same governance standards as any other project.
- **Knowledge flows through defined interfaces.** Organizational functions produce knowledge artifacts in defined formats. Research Vault ingests, organizes, and serves them. The interface is explicit and governed.
- **Research Vault's value is measured by organizational outcomes.** Its success metric is not the volume of knowledge stored, but the impact of that knowledge on organizational decision quality and efficiency.

---

## 11. AI Platform Organization — Extended Model

> *This section extends Section 3.7 with operational detail.*

### 11.1 Model Governance

The AI Platform Organization governs which AI models are used, how they are used, and under what conditions:

- No organizational function directly selects or specifies AI models
- All model access is mediated through the Capability Registry
- Model performance, cost, and quality are continuously monitored
- Model changes (upgrades, replacements, deprecations) are managed through a governed change process
- Model governance decisions are recorded in the organizational decision registry

### 11.2 Provider Governance

AI providers are managed as organizational resources, not individual tool selections:

- Provider selection is an AI Platform Organization decision, governed by capability requirements, cost constraints, and reliability criteria
- Provider contracts, quotas, and budgets are managed centrally
- Provider performance is monitored against defined service level expectations
- Provider diversification is maintained to prevent single-provider dependency
- Provider changes are transparent to consuming organizational functions

### 11.3 Capability Registry

The Capability Registry is the authoritative catalog of AI capabilities available to the organization:

| Registry Field | Description |
|---|---|
| **Capability Name** | What this capability does (e.g., "Code Review", "Architecture Analysis", "Test Generation") |
| **Capability Level** | Quality/depth tier (e.g., Standard, Advanced, Expert) |
| **Availability** | Current availability status and any constraints |
| **Cost Profile** | Relative cost per invocation or per unit of work |
| **Providers** | Which providers can fulfill this capability (managed by AI Platform, not visible to consumers) |
| **Fallback Chain** | Ordered list of alternatives if the primary provider is unavailable |

### 11.4 Cost and Quota Management

- Organizational budget for AI capabilities is allocated by the Portfolio Organization
- The AI Platform Organization distributes budget across capability categories based on portfolio demand
- Quota usage is monitored in real-time
- Cost anomalies trigger alerts and investigation
- Budget forecasts are updated based on actual consumption patterns

### 11.5 Workforce Health Monitoring

The AI Platform Organization monitors the health of the AI workforce:

| Health Metric | Description |
|---|---|
| **Availability** | Can capabilities be invoked successfully? |
| **Latency** | How long do capability invocations take? |
| **Quality** | Are capability outputs meeting expected standards? |
| **Cost Efficiency** | Are costs within expected ranges? |
| **Quota Headroom** | How much quota remains relative to projected demand? |

### 11.6 Cooling Policies

When workforce utilization approaches capacity limits or when provider rate limits are encountered:

- **Soft cooling** — Non-critical work is deferred; critical work continues at full capacity
- **Medium cooling** — Work is throttled across all priority tiers; only Critical-priority work runs at full speed
- **Hard cooling** — All non-Critical work is suspended; Critical work is rate-limited to sustainable levels

Cooling policy activation and deactivation are governed decisions, recorded in the decision registry.

---

## 12. Resource Constraint Policies

### 12.1 Constraint Scenarios

The organization defines explicit behavioral responses for resource constraint scenarios:

### Quota Exhaustion

When an AI provider's quota is exhausted:

1. AI Platform Organization activates the fallback chain from the Capability Registry
2. Affected organizational functions are notified of capability routing changes
3. If no fallback is available, affected work is throttled or deferred based on priority tier
4. Portfolio Authority is notified if constraint impacts High or Critical priority work
5. The constraint event is recorded and analyzed for capacity planning improvement

### Budget Exhaustion

When organizational AI budget is exhausted:

1. All non-Critical work is suspended immediately
2. Portfolio Authority convenes an emergency prioritization review
3. Human Founder is notified with options: budget increase, portfolio reprioritization, or work suspension
4. Budget exhaustion root cause is analyzed — was it a forecasting failure, unexpected demand, or cost anomaly?
5. Findings are recorded as organizational learning

### Provider Degradation

When an AI provider experiences performance degradation (increased latency, reduced quality):

1. AI Platform Organization monitors degradation severity against defined thresholds
2. If thresholds are breached, affected capabilities are rerouted to alternative providers
3. Consuming organizational functions are notified of potential quality or latency changes
4. Provider performance issue is logged for provider governance review
5. If degradation persists, provider is temporarily suspended and the fallback chain is activated

### Provider Outage

When an AI provider is completely unavailable:

1. Fallback providers are activated immediately for all affected capabilities
2. If no fallback exists, affected work is suspended and escalated to Portfolio Authority
3. Human Founder is notified if the outage impacts Critical-priority work
4. Once the provider recovers, workload is gradually rebalanced
5. Post-outage review is conducted and findings are recorded as organizational learning

### 12.2 Organizational Response Principles

Across all constraint scenarios, the organization follows these principles:

- **Protect Critical work first** — Resource constraints affect lower-priority work before higher-priority work
- **Communicate proactively** — Affected organizational functions are notified before impact is felt, not after
- **Decide explicitly** — Constraint responses are governed decisions, not automatic reactions
- **Learn from constraints** — Every significant constraint event produces a post-event review that improves future planning
- **Escalate, don't suppress** — Constraint impacts are surfaced to the appropriate authority level, never hidden

---

## 13. Escalation Model

### 13.1 Escalation Philosophy

Escalation is not a failure — it is an **organizational capability**. An organization that cannot escalate cannot resolve conflicts, and an organization that cannot resolve conflicts cannot maintain coherence.

Escalation is governed by two rules:

1. **Escalation is mandatory.** Unresolved conflicts must escalate. Allowing conflicts to persist without resolution is an organizational failure.
2. **Escalation is bounded.** Every escalation has a time limit. If the receiving authority does not resolve the conflict within the time bound, it automatically escalates further.

### 13.2 Conflict Scenarios and Resolution Paths

### Product vs. Engineering

| Conflict | Example | Resolution Path |
|---|---|---|
| Feasibility disagreement | Product requests a feature that Engineering considers technically infeasible | Engineering produces a feasibility assessment. Product reviews and either adjusts scope or challenges the assessment. If unresolved → Portfolio Authority decides. |
| Priority disagreement | Product wants Feature A prioritized; Engineering believes technical debt must be addressed first | Both parties present their case with supporting rationale. Portfolio Authority decides based on strategic priorities. |
| Quality standards disagreement | Product wants to ship faster; Engineering wants more testing | Governance Organization reviews against organizational quality standards. Standards prevail unless Portfolio Authority grants an explicit exception. |

### Engineering vs. Governance

| Conflict | Example | Resolution Path |
|---|---|---|
| Standard compliance | Engineering believes a governance standard is impractical for their context | Engineering proposes a standard modification with rationale. Governance reviews. If unresolved → Human Founder decides. |
| Gate failure disagreement | Engineering disagrees with a governance gate rejection | Engineering addresses the specific findings and resubmits. If the disagreement is on the standard itself → escalate to Human Founder. |
| Process friction | Engineering reports that a governance process creates excessive delay | Governance conducts a process efficiency review. Improvements are proposed. If disagreement persists → Portfolio Authority mediates. |

### Project vs. Portfolio

| Conflict | Example | Resolution Path |
|---|---|---|
| Resource allocation | A project needs more resources than the portfolio allocation provides | Project presents its case with impact analysis. Portfolio reviews against overall priorities. Portfolio Authority decides. |
| Priority ranking | A project believes it should be ranked higher than the portfolio assessment indicates | Project presents strategic justification. Portfolio reassesses. If unresolved → Human Founder decides. |
| Timeline pressure | Portfolio timelines conflict with project reality | Project provides evidence-based timeline revision. Portfolio assesses cross-project impact. Portfolio Authority decides. |

### Resource Conflicts (Cross-Project)

| Conflict | Example | Resolution Path |
|---|---|---|
| Shared resource contention | Two projects need the same specialized capability simultaneously | Portfolio Organization applies prioritization model. Higher-priority project gets precedence. Lower-priority project receives adjusted timeline. |
| Capability shortage | Portfolio demand exceeds AI Platform capacity | AI Platform Organization proposes options (scaling, throttling, reallocation). Portfolio Authority decides allocation. Human Founder decides budget implications. |

### 13.3 Escalation Path Summary

```
Executing Role
      │
      ▼
Organization Lead (Product, Engineering, Operations, etc.)
      │
      ▼
Portfolio Authority
      │
      ▼
Human Founder (Final Authority)
```

Cross-cutting escalation: Any organizational function can escalate directly to the Governance Organization if the conflict involves a governance standard, compliance requirement, or organizational principle.

---

## 14. Organizational Evolution

Karsa evolves through distinct maturity stages. Each stage builds upon the capabilities, structures, and knowledge accumulated in prior stages.

### 14.1 Stage 1 — Single Project Organization

**Organizational State:** Karsa operates with a single project and a minimal organizational structure.

| Dimension | Stage 1 Characteristics |
|---|---|
| **Portfolio** | Single project; no portfolio management needed |
| **Governance** | Basic governance gates (Vision, Architecture, Quality, Release) |
| **Resources** | Small workforce; no resource contention |
| **Knowledge** | Initial knowledge capture; foundational decision records |
| **AI Platform** | Single provider; basic capability mapping |
| **Escalation** | Direct escalation to Human Founder for all conflicts |

**Stage 1 Goals:**

- Prove the organizational model works for a single project
- Establish foundational governance processes
- Begin building organizational memory
- Validate the authority model with real decisions
- Produce the first complete Work Packages through governed processes

**Transition Criteria to Stage 2:**

- At least one project has completed a full lifecycle (Discovery → Release)
- Governance gates are functioning and producing traceable decisions
- Organizational memory contains foundational decision records
- The organizational model has been validated and refined through experience

---

### 14.2 Stage 2 — Multi-Project Organization

**Organizational State:** Karsa operates with multiple concurrent projects and an active portfolio management function.

| Dimension | Stage 2 Characteristics |
|---|---|
| **Portfolio** | Active portfolio management with prioritization and cross-project coordination |
| **Governance** | Full governance model with all gate types operational |
| **Resources** | Shared workforce with explicit allocation; capacity planning active |
| **Knowledge** | Cross-project learning active; pattern libraries emerging |
| **AI Platform** | Multiple providers; capability-based routing; cost management active |
| **Escalation** | Full escalation model with inter-organizational conflict resolution |

**Stage 2 Goals:**

- Demonstrate effective multi-project coordination
- Prove shared resource allocation works without project starvation
- Establish cross-project knowledge flow
- Mature governance to handle portfolio-level complexity
- Validate portfolio prioritization and tradeoff processes

**Transition Criteria to Stage 3:**

- Three or more projects managed concurrently without governance or resource failures
- Cross-project knowledge reuse is demonstrated and measurable
- Resource allocation operates effectively across the portfolio
- Governance processes scale without proportional increase in friction

---

### 14.3 Stage 3 — Large Portfolio Organization

**Organizational State:** Karsa operates a large portfolio with sophisticated organizational capabilities.

| Dimension | Stage 3 Characteristics |
|---|---|
| **Portfolio** | Large portfolio with diverse project types, maturity stages, and risk profiles |
| **Governance** | Proportional governance — lighter for low-risk, deeper for high-risk decisions |
| **Resources** | Advanced capacity planning; predictive resource allocation; workforce scaling |
| **Knowledge** | Deep institutional memory; knowledge compounding demonstrably accelerating execution |
| **AI Platform** | Mature provider governance; cost optimization; capacity forecasting |
| **Escalation** | Rare; most conflicts resolved at organizational function level through precedent |

**Stage 3 Goals:**

- Achieve operational excellence across the portfolio
- Demonstrate knowledge compounding — measurably faster and better execution on new projects
- Governance operates as an embedded organizational capability, not as an overhead layer
- New projects can be onboarded rapidly using organizational templates, patterns, and precedents
- The organization is self-improving — processes evolve based on measured outcomes

---

## 15. Organizational Principles

The following principles govern all organizational behavior in Karsa. Every role, every process, and every decision must be consistent with these principles.

---

**1. Human authority is final.**

No organizational process, governance gate, or escalation path supersedes the Human Founder's authority. All authority in the organization is delegated from and revocable by the Human Founder.

---

**2. Autonomy without governance creates chaos.**

Every action must be governed. Governance is not overhead — it is the mechanism that creates trust, consistency, and traceability. Ungoverned actions are organizational failures.

---

**3. Every artifact contributes to organizational memory.**

Work products are not disposable. Every decision, design, review, incident, and outcome is a knowledge asset that enriches the organization's institutional memory and informs future work.

---

**4. The organization continuously learns from every decision, review, incident, and outcome.**

Learning is not periodic — it is continuous. The organization becomes measurably better with each completed project because it captures, preserves, and applies what it has learned.

---

**5. No project exists in isolation.**

All projects operate within a unified portfolio with shared resources, shared governance, shared knowledge, and shared strategic context. Portfolio thinking governs resource allocation, prioritization, and tradeoff decisions.

---

**6. Accountability is non-negotiable.**

Every action is attributable to a specific role. Every decision has a recorded author. Every deliverable has a traceable governance history. The organization never produces anonymous or unaccountable work.

---

**7. Structure enables, not constrains.**

Organizational structure exists to amplify capability, not to limit it. Roles, workflows, and governance processes are designed to make work more effective, not more burdensome. When structure creates friction without corresponding value, the structure is evolved.

---

**8. Specialization creates excellence.**

Each organizational function has a defined scope and does not exceed it. A role that tries to do everything does nothing well. Clear boundaries create clear accountability, which creates clear excellence.

---

**9. Escalation is a capability, not a failure.**

Conflicts are surfaced and resolved through defined paths. Unresolved conflicts are an organizational threat. Escalation is mandatory, time-bounded, and always produces a recorded resolution.

---

**10. The organization evolves deliberately.**

Change to the organizational model is governed, evidence-based, and approved. The organization improves itself — but it does so through structured evolution, not through ad-hoc drift.

---

**11. Knowledge compounds.**

The value of organizational knowledge grows non-linearly. Each piece of captured knowledge makes future knowledge more valuable. The organization's hundredth decision benefits from the context of the ninety-nine that preceded it.

---

**12. Transparency is the default.**

Organizational state, decisions, and health are visible to all functions that need them. Information is withheld only for explicit, governed reasons — never by default. An opaque organization cannot learn, govern, or improve.

---

## 16. Organizational Risks

The following are the major organizational failure modes that Karsa must continuously monitor, detect early, and actively mitigate. These are not theoretical concerns — they are the predictable ways that organizations degrade when vigilance lapses.

Risk management is not a periodic exercise. It is an embedded organizational behavior. Every organizational function is responsible for monitoring the risks relevant to its domain and escalating when early warning signals appear.

---

### 16.1 Agent Drift

**Description:**
Agent Drift occurs when an agent gradually deviates from its defined role, responsibilities, and organizational boundaries. An agent begins making decisions outside its authority, adopting behaviors not sanctioned by its role definition, or producing outputs that do not conform to organizational standards. Drift is rarely sudden — it is incremental, which makes it difficult to detect without deliberate monitoring.

**Potential Impact:**
- Governance breakdown — ungoverned decisions are made without appropriate authority or review
- Accountability erosion — when roles blur, accountability becomes ambiguous
- Quality inconsistency — drifted agents produce outputs that may not meet organizational standards
- Authority violation — decisions are made by roles that lack the authority to make them
- Organizational confusion — other functions cannot predict what a drifted agent will do, undermining coordination

**Early Warning Signals:**
- An agent produces artifacts outside the scope of its defined responsibilities
- An agent makes decisions that should require escalation or peer review without triggering either
- Governance gate submissions contain work that originated from unexpected organizational functions
- Peer organizations report receiving unexpected directives or artifacts from the drifting agent
- Role boundary violations appear in compliance reviews

**Mitigation Strategy:**
- Maintain explicit, documented role definitions with clear scope boundaries for every organizational function
- Governance Organization conducts periodic role compliance reviews — verifying that each function operates within its defined scope
- Governance gates validate that Work Packages originate from the appropriate organizational function
- Escalation is triggered automatically when an agent's output is flagged as outside its defined role
- Role definitions are reviewed and refined after each organizational evolution stage

---

### 16.2 Knowledge Decay

**Description:**
Knowledge Decay occurs when organizational memory degrades over time — becoming stale, inaccurate, undiscoverable, or disconnected from the decisions it was meant to inform. Knowledge that exists but cannot be found is functionally equivalent to knowledge that was never captured. Knowledge that is found but no longer accurate is worse — it actively misleads.

**Potential Impact:**
- The organization repeats past mistakes because the lessons from those mistakes are no longer accessible
- Decisions are made without the context that past decisions would have provided
- Architecture choices conflict with forgotten constraints or rationale
- The knowledge compounding advantage is lost — the organization stops getting smarter over time
- Institutional memory becomes an unreliable archive rather than a strategic asset

**Early Warning Signals:**
- The same type of problem recurs across projects, indicating that past learnings are not being applied
- Decision records reference outdated or superseded information
- Knowledge Organization reports increasing staleness index in the knowledge base
- Teams produce work that contradicts existing organizational standards or patterns — not from disagreement, but from unawareness
- Cross-project knowledge reuse rate declines over time

**Mitigation Strategy:**
- Knowledge Organization maintains an active staleness monitoring program — reviewing knowledge artifacts for currency and relevance on a defined schedule
- Every knowledge artifact has a defined review cycle — it is either confirmed, updated, or deprecated at each review
- Knowledge is linked to the decisions and contexts it informs, so that when decisions are revisited, the relevant knowledge surfaces automatically
- Post-mortems and retrospectives explicitly check whether relevant existing knowledge was consulted — and if not, why not
- Knowledge that is deprecated is archived with a clear record of why it was retired, preserving the organizational learning even when the specific content is no longer current

---

### 16.3 Approval Bottlenecks

**Description:**
Approval Bottlenecks occur when governance gates, authority approvals, or review processes become congestion points that slow organizational throughput disproportionately. The organization produces work faster than it can approve work, creating queues that delay delivery, frustrate executing functions, and create pressure to bypass governance.

**Potential Impact:**
- Delivery velocity drops as work stalls waiting for approvals
- Pressure to bypass governance grows — risking ungoverned actions and quality degradation
- Executing functions lose momentum and context while waiting, reducing output quality when work resumes
- The organization develops a perception that governance is an obstacle rather than an enabler
- In severe cases, the bottleneck creates a cascading delay across the portfolio, as downstream work depends on blocked upstream approvals

**Early Warning Signals:**
- Governance gate cycle time (submission to decision) increases consistently
- A growing queue of Work Packages awaiting review or approval
- Executing functions report idle time caused by pending approvals
- Escalation volume increases as functions seek to expedite blocked work
- Informal workarounds or pre-approvals emerge outside the governed process

**Mitigation Strategy:**
- Governance processes are designed with defined service level expectations — maximum time from submission to decision
- Governance Organization monitors gate throughput and cycle time as primary health metrics
- Proportional governance is applied — lower-risk decisions receive lighter review, preserving governance capacity for higher-risk decisions
- When bottlenecks are detected, Governance Organization conducts a process efficiency review and proposes structural improvements
- Approval authority is delegated to the lowest appropriate level — avoiding unnecessary escalation to higher authorities for routine decisions
- Bottleneck patterns are recorded as organizational learning and used to improve governance process design

---

### 16.4 Resource Starvation

**Description:**
Resource Starvation occurs when one or more projects lack sufficient workforce capacity to make meaningful progress. This can result from poor allocation, over-commitment of the portfolio, unplanned demand spikes, or the gravitational pull of high-priority projects that absorb disproportionate organizational capacity.

**Potential Impact:**
- Starved projects miss milestones, accumulate delays, and lose strategic momentum
- Quality degrades as insufficient capacity is spread too thin across too much work
- Project teams lose coherence and context as resources are intermittently available
- Portfolio balance is disrupted — strategic projects may stall while tactical work consumes capacity
- In severe cases, starved projects fail silently — they do not formally fail, but they stop making meaningful progress

**Early Warning Signals:**
- Project health dashboards show sustained "Warning" or "Critical" status on the Resource dimension
- Milestone velocity declines without a corresponding reduction in scope
- The same resources are allocated to an increasing number of concurrent projects
- Projects report repeated context-switching costs as shared resources oscillate between assignments
- Portfolio reviews reveal that lower-priority projects have not progressed between review cycles

**Mitigation Strategy:**
- Portfolio Organization conducts regular capacity-vs-commitment reviews — verifying that total portfolio demand does not exceed organizational capacity
- Resource allocation decisions are explicit, recorded, and revisited at defined intervals
- When starvation is detected, Portfolio Authority conducts a tradeoff review — determining whether to reduce portfolio scope, increase capacity, or accept the starvation and its consequences deliberately
- No project is allocated resources below the minimum viable level — if a project cannot receive enough capacity to make meaningful progress, it is formally paused rather than allowed to linger
- Resource starvation events are recorded as organizational learning and inform future capacity planning

---

### 16.5 Governance Overhead

**Description:**
Governance Overhead occurs when governance processes consume a disproportionate share of organizational capacity relative to the value they produce. Governance exists to create trust, traceability, and quality — but when governance processes grow beyond what is necessary, they become a tax on productivity that undermines the very organizational health they are meant to protect.

**Potential Impact:**
- Organizational throughput declines as an increasing share of capacity is consumed by governance activities rather than value-producing work
- Executing functions develop resentment toward governance, reducing cooperation and compliance
- The organization becomes slow and bureaucratic — losing the agility advantage that a well-structured virtual organization should provide
- Governance fatigue sets in — reviews become perfunctory, approvals become rubber stamps, and the governance system loses its integrity while retaining its cost

**Early Warning Signals:**
- The ratio of governance activity to productive output increases over time
- Executing functions consistently report that governance processes are the primary constraint on delivery
- Governance reviews produce fewer actionable findings per review — indicating that the review depth exceeds what the work requires
- Governance standards accumulate without retirement — the number of standards grows monotonically
- Compliance review findings increasingly focus on procedural technicalities rather than substantive quality or risk issues

**Mitigation Strategy:**
- Governance is designed to be proportional — the depth and rigor of governance review scales with the risk and impact of the decision being governed
- Governance Organization tracks its own cost-to-value ratio — measuring the governance findings that prevented real problems against the organizational capacity consumed by governance processes
- Governance standards are subject to periodic review and retirement — standards that no longer serve an active purpose are deprecated with recorded rationale
- The principle "Structure enables, not constrains" is applied to governance processes — when a process creates friction without corresponding protective value, it is evolved or removed
- Governance overhead is an explicit metric monitored at portfolio reviews, ensuring organizational leadership maintains awareness of the governance-to-production balance

---

### 16.6 Organizational Fragmentation

**Description:**
Organizational Fragmentation occurs when the unified organizational structure degrades into disconnected silos. Projects operate independently. Knowledge stops flowing across project boundaries. Governance standards diverge between projects. Resource allocation becomes project-centric rather than portfolio-centric. The organization loses its coherence and begins behaving as a collection of independent efforts rather than a unified entity.

**Potential Impact:**
- The portfolio thinking advantage is lost — each project operates as if it were the only project
- Knowledge compounding stops — lessons from one project do not reach other projects
- Governance inconsistency emerges — different projects operate under different standards, making organizational quality unpredictable
- Resource allocation becomes competitive rather than strategic — projects compete for resources through influence rather than through governed prioritization
- The organization's value becomes merely the sum of its parts, rather than greater than the sum

**Early Warning Signals:**
- Cross-project knowledge reuse rate drops to near zero
- Projects develop their own standards, templates, and processes that diverge from organizational norms
- Portfolio reviews reveal that projects are unaware of relevant decisions, patterns, or incidents from peer projects
- Resource allocation decisions are made within projects without portfolio-level coordination
- Governance findings differ significantly in type and severity across projects — suggesting inconsistent standard application

**Mitigation Strategy:**
- Portfolio Organization actively maintains cross-project visibility — ensuring that all projects are aware of portfolio context, peer project status, and shared organizational priorities
- Knowledge Organization proactively curates and distributes cross-project learning — not waiting for projects to seek knowledge, but actively pushing relevant knowledge to projects that would benefit
- Governance Organization enforces consistent standards across the portfolio — conducting cross-project consistency reviews at defined intervals
- Resource allocation is a portfolio-level function, not a project-level function — projects request resources; the portfolio allocates them
- Organizational fragmentation is treated as a governance violation — when detected, it triggers a corrective review and remediation plan

---

### 16.7 Project Priority Conflicts

**Description:**
Project Priority Conflicts occur when multiple projects legitimately compete for the same organizational resources, strategic attention, or governance capacity — and the organization fails to resolve these conflicts through its defined prioritization and escalation processes. Unlike resource starvation (which is a capacity problem), priority conflicts are a decision-making problem — the organization has the capacity but cannot agree on where to direct it.

**Potential Impact:**
- Organizational paralysis — resources oscillate between projects without making sustained progress on either
- Political behavior emerges — project advocates attempt to influence prioritization through persuasion rather than through governed criteria
- Strategic coherence erodes — without clear priorities, the portfolio drifts toward whichever project has the most vocal advocate
- Human Founder is overwhelmed with escalations that should be resolvable at the portfolio level
- Lower-priority projects lose morale and engagement as their importance is perpetually deferred

**Early Warning Signals:**
- Portfolio prioritization decisions are frequently revisited or challenged between review cycles
- Resource allocation changes frequently without corresponding strategic justification
- Escalation volume from project-level to portfolio-level increases
- Projects duplicate effort because they cannot rely on shared resources being available
- Portfolio reviews become contentious rather than analytical

**Mitigation Strategy:**
- Portfolio prioritization uses explicit, documented criteria — not subjective judgment — to rank projects
- Prioritization decisions are recorded with full rationale in the decision registry, creating precedent for future decisions
- Once set, priorities are stable until the next scheduled review unless a qualifying strategic event triggers an unscheduled review
- Qualifying events for unscheduled reprioritization are defined in advance — preventing ad-hoc priority changes driven by urgency rather than strategy
- The Human Founder is the final arbiter of priority disputes that the Portfolio Authority cannot resolve — but the expectation is that this escalation is rare, not routine

---

### 16.8 AI Provider Dependency

**Description:**
AI Provider Dependency occurs when the organization becomes critically dependent on a single AI provider — such that a provider outage, pricing change, capability deprecation, or policy change would significantly disrupt organizational operations. This risk is amplified because Karsa's entire workforce consists of AI agents — making provider dependency an existential organizational risk, not merely a technical inconvenience.

**Potential Impact:**
- A single provider outage halts organizational operations across the entire portfolio
- Provider pricing changes can make the organization's operating model economically unviable without warning
- Provider capability changes or deprecations can eliminate organizational capabilities that workflows depend on
- Provider policy changes (usage restrictions, content policies, rate limits) can constrain organizational operations in unpredictable ways
- The organization loses negotiating leverage with a provider it cannot realistically leave

**Early Warning Signals:**
- Provider concentration index exceeds defined thresholds — a single provider handles a dominant share of capability requests
- Fallback chains in the Capability Registry have gaps — certain capabilities have no alternative provider
- The organization has not tested fallback activation in a defined period
- Provider cost as a percentage of organizational budget grows without corresponding capability growth
- Provider announcements (deprecation notices, pricing changes, policy updates) would materially impact organizational operations

**Mitigation Strategy:**
- AI Platform Organization maintains a provider diversification policy — no single provider should handle more than a defined percentage of total capability demand
- The Capability Registry maintains active fallback chains for all critical capabilities — and fallback chains are tested periodically, not just documented
- Provider governance includes ongoing monitoring of provider health, financial stability, policy direction, and competitive landscape
- The capability-based assignment model (organizations request capabilities, not models) provides the architectural flexibility to reroute capability requests across providers without disrupting organizational workflows
- Provider dependency is reviewed at every portfolio review, with explicit assessment of concentration risk and fallback readiness
- Budget planning includes contingency for provider cost increases, ensuring the organization is not one pricing change away from a budget crisis

---

### 16.9 Risk Monitoring Responsibilities

| Risk | Primary Monitor | Secondary Monitor | Escalation Target |
|---|---|---|---|
| Agent Drift | Governance Organization | Knowledge Organization | Portfolio Authority |
| Knowledge Decay | Knowledge Organization | Governance Organization | Portfolio Authority |
| Approval Bottlenecks | Governance Organization | Portfolio Organization | Human Founder |
| Resource Starvation | Portfolio Organization | AI Platform Organization | Human Founder |
| Governance Overhead | Portfolio Organization | Governance Organization | Human Founder |
| Organizational Fragmentation | Portfolio Organization | Knowledge Organization | Human Founder |
| Project Priority Conflicts | Portfolio Organization | Governance Organization | Human Founder |
| AI Provider Dependency | AI Platform Organization | Portfolio Organization | Human Founder |

### 16.10 Risk Management Principles

- **Risks are organizational, not individual.** These risks belong to the organization, not to specific agents. Every organizational function contributes to risk monitoring and mitigation.
- **Early detection is more valuable than late correction.** The early warning signals defined above are not informational — they are triggers for investigation and action.
- **Risk mitigation is a governed activity.** Mitigation actions are recorded, their effectiveness is evaluated, and the results inform future risk management.
- **Risk acceptance is a deliberate decision.** When the organization chooses to accept a risk rather than mitigate it, that acceptance is an explicit, recorded decision made at the appropriate authority level — never a default or oversight.
- **Risk patterns are organizational knowledge.** How risks manifest, how they are detected, and how they are resolved becomes part of institutional memory — making the organization progressively better at managing its own vulnerabilities.

---

## 17. Organizational Metrics

### 17.1 Purpose of Organizational Metrics

Metrics exist to make organizational health **visible, measurable, and improvable**. Without metrics, the organization cannot distinguish between perception and reality, cannot detect degradation before it becomes a crisis, and cannot evaluate whether its evolutionary changes are producing actual improvement.

Karsa's metrics are not performance scorecards for individual agents. They are **organizational health indicators** — measurements of how well the organization's structures, processes, and knowledge systems are functioning as a whole. They inform decisions, trigger investigations, and provide the evidence base for organizational evolution.

### 17.2 Metrics Principles

- **Metrics measure organizational health, not individual performance.** A metric that degrades indicates an organizational problem — a process weakness, a structural gap, or a resource imbalance — not a failing agent.
- **Metrics are leading indicators, not lagging reports.** The primary value of a metric is its ability to signal a developing problem before it becomes a crisis. A metric reviewed only in retrospect has lost most of its value.
- **Metrics drive investigation, not punishment.** When a metric degrades, the organizational response is to investigate the root cause and address it — not to assign blame.
- **Metrics evolve with the organization.** As Karsa matures through its stages, the metrics that matter will change. New metrics will be introduced, existing metrics will be refined, and metrics that no longer serve an active purpose will be retired.
- **Metrics without action are waste.** Every metric defined below has a purpose — it informs a specific class of organizational decision. A metric that is collected but never used to inform a decision should be questioned and potentially retired.

---

### 17.3 Portfolio Metrics

**Purpose:** Evaluate the health, balance, and strategic effectiveness of Karsa's project portfolio as a whole.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **Portfolio Health Index** | Composite score of all active project health assessments | ≥80% of projects in Healthy status | 50–79% of projects in Healthy status | <50% of projects in Healthy status |
| **Delivery Predictability** | Percentage of milestones delivered within their planned timeframe | ≥80% on-time delivery | 60–79% on-time delivery | <60% on-time delivery |
| **Strategic Alignment Score** | Degree to which active projects align with stated organizational vision and priorities | All projects have current, approved alignment with organizational vision | Some projects lack updated alignment assessment | Projects are active without clear strategic justification |
| **Portfolio Balance** | Distribution of projects across lifecycle stages, risk profiles, and strategic categories | Balanced distribution with deliberate portfolio composition | Concentration in a single stage or category | Portfolio dominated by a single project or category with no diversification |
| **Resource Utilization Rate** | Percentage of organizational capacity actively allocated to productive work | 70–85% utilization | 50–69% or 86–95% utilization | <50% (idle waste) or >95% (burnout risk) |
| **Cross-Project Dependency Health** | Status of identified inter-project dependencies | All dependencies tracked and on schedule | Some dependencies at risk | Dependency failures blocking multiple projects |

**Organizational Significance:** Portfolio metrics inform the Portfolio Organization's resource allocation, prioritization, and strategic tradeoff decisions. Degradation in portfolio metrics triggers portfolio-level reviews and potential reprioritization. These metrics are the primary input for the Human Founder's strategic oversight.

---

### 17.4 Product Metrics

**Purpose:** Evaluate how effectively the Product Organization transforms ideas into clear, actionable, and stable product definitions.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **Idea Throughput** | Number of ideas that progress from Proposal to approved Domain Vision within a defined period | Consistent flow of ideas through the discovery pipeline | Pipeline stalls — ideas accumulate without progressing | No ideas progressing; discovery pipeline is blocked |
| **Idea Approval Rate** | Percentage of submitted proposals that achieve Domain Vision approval | Reflects deliberate, quality-focused filtering (neither too high nor too low) | Approval rate is extremely high (insufficient filtering) or extremely low (excessive rejection) | Approval process is non-functional — either everything passes or nothing passes |
| **Design Package Quality** | Percentage of approved Design Packages that proceed through downstream gates without requiring significant rework | ≥85% pass downstream gates without major revision | 70–84% pass without major revision | <70% — indicating systemic quality issues in product definition |
| **Scope Stability** | Percentage of approved scope that remains unchanged through the execution phase | ≥85% scope stability after approval | 70–84% stability — scope creep is emerging | <70% — scope is unstable, undermining execution predictability |
| **Requirements Clarity Score** | Frequency with which Engineering requests clarification on approved requirements | Rare clarification requests — requirements are clear and complete | Regular clarification requests on non-trivial aspects | Frequent clarification requests — requirements are consistently ambiguous |

**Organizational Significance:** Product metrics evaluate the quality of the organization's upstream decision-making. Poor product metrics cascade into engineering rework, governance friction, and delivery delays. These metrics are the early warning system for downstream problems.

---

### 17.5 Engineering Metrics

**Purpose:** Evaluate the efficiency, quality, and discipline of the Engineering Organization's execution.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **Lead Time** | Elapsed time from work item assignment to approved Change Package delivery | Within planned estimates with acceptable variance | Consistently exceeding estimates by >25% | Lead times are unpredictable or consistently exceed estimates by >50% |
| **Review Cycle Time** | Elapsed time from Change Package submission to review completion | Within defined service level expectations | Approaching service level limits; queues forming | Exceeding service level expectations; reviews are a delivery bottleneck |
| **Defect Escape Rate** | Percentage of defects discovered after a Change Package passes its Quality Gate | <5% defect escape rate | 5–15% defect escape rate | >15% — Quality Gate is not catching defects effectively |
| **Architecture Decision Record Coverage** | Percentage of significant technical decisions with a completed ADR | ≥90% coverage | 70–89% coverage | <70% — significant decisions are being made without documentation |
| **Technical Debt Trajectory** | Direction of technical debt over time (increasing, stable, decreasing) | Stable or decreasing | Slowly increasing | Rapidly increasing without a remediation plan |
| **Build and Integration Success Rate** | Percentage of build and integration attempts that succeed without intervention | ≥95% success rate | 85–94% success rate | <85% — integration reliability is a concern |

**Organizational Significance:** Engineering metrics evaluate execution quality and discipline. They inform capacity planning, identify process bottlenecks, and provide early warning of quality degradation. Engineering metrics also contribute to organizational learning — patterns in these metrics reveal systemic issues that can be addressed through process improvement.

---

### 17.6 Operations Metrics

**Purpose:** Evaluate the reliability, responsiveness, and operational discipline of production systems and the Operations Organization.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **System Availability** | Percentage of time that production systems are operational and accessible | ≥99.5% availability | 99.0–99.4% availability | <99.0% availability |
| **Incident Count** | Number of production incidents within a defined period, categorized by severity | Trending stable or declining | Trending upward | Significant spike or sustained increase |
| **Mean Time to Resolve (MTTR)** | Average elapsed time from incident detection to resolution | Within defined service level targets | Approaching service level limits | Exceeding service level targets; resolution is consistently slow |
| **Mean Time to Detect (MTTD)** | Average elapsed time from incident occurrence to detection | Near real-time detection for critical systems | Detection delays for some incident types | Significant detection gaps — incidents are discovered by users or external signals |
| **Deployment Success Rate** | Percentage of deployments that complete without rollback or emergency intervention | ≥95% success rate | 85–94% success rate | <85% — deployment process reliability is a concern |
| **Post-Mortem Completion Rate** | Percentage of qualifying incidents that produce a completed post-mortem within the defined timeframe | 100% completion within timeframe | 80–99% completion or completion outside timeframe | <80% — the organization is losing incident learning opportunities |

**Organizational Significance:** Operations metrics measure the organization's ability to maintain reliable production systems. They also drive the incident learning loop — post-mortem coverage directly influences the organization's ability to prevent recurring failures. Operations metrics are a key input for release governance decisions.

---

### 17.7 Governance Metrics

**Purpose:** Evaluate the effectiveness, efficiency, and integrity of the organization's governance processes.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **Governance Compliance Rate** | Percentage of Work Packages that pass their applicable governance gates on first submission | ≥80% first-pass approval | 60–79% first-pass approval | <60% — either work quality or governance standards need review |
| **Architecture Compliance** | Percentage of engineering deliverables that conform to approved architectural decisions and standards | ≥90% compliance | 75–89% compliance | <75% — architectural governance is not effective |
| **Audit Finding Rate** | Number of substantive findings per compliance review | Low, declining finding rate (indicating improving compliance) | Stable finding rate (compliance is not improving) | Increasing finding rate (compliance is degrading) |
| **Decision Traceability Coverage** | Percentage of significant organizational decisions with complete decision records | ≥90% coverage | 75–89% coverage | <75% — the organization is making decisions without recording rationale |
| **Governance Gate Cycle Time** | Elapsed time from Work Package submission to governance decision | Within defined service level expectations | Approaching service level limits | Exceeding expectations — governance is becoming a bottleneck |
| **Artifact Hierarchy Violation Rate** | Number of detected cases where lower-level artifacts contradict higher-level artifacts | Zero violations | Rare, promptly remediated violations | Recurring or unresolved violations |

**Organizational Significance:** Governance metrics serve a dual purpose. They measure organizational compliance — are standards being followed? — and they measure governance efficiency — is governance achieving its purpose without becoming a bottleneck? The tension between compliance rate and cycle time is the key indicator of governance health. High compliance with fast cycle time indicates a well-calibrated governance process.

---

### 17.8 Knowledge Metrics

**Purpose:** Evaluate the health, growth, and impact of the organization's institutional memory and learning systems.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **Knowledge Reuse Rate** | Frequency with which existing organizational knowledge is consulted and applied in new decisions | Regular, documented reuse of organizational knowledge across projects | Knowledge exists but is rarely consulted; projects operate without referencing institutional memory | Knowledge is effectively unused — projects start from zero despite existing organizational precedent |
| **Decision Traceability** | Percentage of decisions that can be traced back to their rationale, alternatives, and approval through the knowledge system | ≥90% of decisions are fully traceable | 75–89% traceability | <75% — significant decisions lack traceable rationale |
| **Post-Mortem Coverage** | Percentage of qualifying events (incidents, project completions, major decisions) that produce learning artifacts | ≥95% coverage | 80–94% coverage | <80% — the organization is losing learning opportunities at a significant rate |
| **Knowledge Staleness Index** | Percentage of knowledge artifacts that have not been reviewed or confirmed within their defined review cycle | <10% stale artifacts | 10–25% stale artifacts | >25% — organizational memory is becoming unreliable |
| **Cross-Project Knowledge Flow** | Number of instances where knowledge from one project demonstrably informed decisions in another project | Regular, documented cross-project knowledge application | Occasional cross-project knowledge flow | Near-zero cross-project knowledge transfer — projects operate as silos |
| **Knowledge Compounding Indicator** | Measurable improvement in decision speed or quality attributable to accumulated organizational knowledge | New projects demonstrably benefit from existing knowledge — faster starts, fewer repeated mistakes | Benefit from existing knowledge is inconsistent | No measurable benefit — knowledge accumulation is not translating into organizational improvement |

**Organizational Significance:** Knowledge metrics are the measurement of Karsa's most distinctive organizational capability — its ability to become progressively smarter over time. Degradation in knowledge metrics is an early warning of organizational amnesia (Risk 16.2) and organizational fragmentation (Risk 16.6). The Knowledge Compounding Indicator is the ultimate measure of whether Karsa's institutional memory strategy is working.

---

### 17.9 AI Platform Metrics

**Purpose:** Evaluate the health, cost-effectiveness, and resilience of the AI capabilities that power Karsa's workforce.

| Metric | Definition | Healthy | Warning | Critical |
|---|---|---|---|---|
| **Cost Efficiency** | Cost per unit of organizational output, normalized across capability categories | Stable or improving cost-per-output ratio | Cost-per-output trending upward without corresponding quality improvement | Cost-per-output increasing significantly — operational model sustainability at risk |
| **Provider Health Score** | Composite score of provider availability, latency, and output quality | All active providers within defined service level expectations | One or more providers approaching service level thresholds | Provider(s) breaching service level expectations; fallback activation required |
| **Capability Success Rate** | Percentage of capability requests that are fulfilled successfully within quality and latency expectations | ≥98% success rate | 95–97% success rate | <95% — workforce reliability is a concern |
| **Quota Utilization** | Current quota consumption as a percentage of total available quota across all providers | 40–70% utilization with adequate headroom | 71–85% utilization — headroom is narrowing | >85% — quota exhaustion risk is elevated |
| **Provider Concentration Index** | Percentage of total capability demand served by the single largest provider | <60% concentration on any single provider | 60–75% concentration — diversification is weakening | >75% — critical single-provider dependency (Risk 16.8) |
| **Fallback Chain Coverage** | Percentage of critical capabilities with tested, active fallback providers | 100% coverage for critical capabilities | 80–99% coverage — some critical capabilities lack fallback | <80% — significant fallback gaps exist |
| **Capacity Forecast Accuracy** | Variance between forecasted and actual capability demand over planning periods | <15% variance | 15–30% variance | >30% variance — capacity planning is unreliable |

**Organizational Significance:** AI Platform metrics measure the health and sustainability of Karsa's operational foundation. Because the entire workforce runs on AI capabilities, these metrics have existential organizational importance. Cost Efficiency and Quota Utilization directly inform budget planning. Provider Concentration Index and Fallback Chain Coverage are the quantitative measures of AI Provider Dependency risk (Risk 16.8). Capacity Forecast Accuracy determines the organization's ability to plan reliably.

---

### 17.10 Organizational Health Dashboard

The following table summarizes the metrics that compose the overall organizational health assessment. This dashboard is the primary input for portfolio reviews and organizational evolution decisions.

| Organizational Function | Key Health Metrics | Review Frequency |
|---|---|---|
| **Portfolio** | Portfolio Health Index, Delivery Predictability, Resource Utilization Rate | Every portfolio review cycle |
| **Product** | Idea Throughput, Design Package Quality, Scope Stability | Every project phase transition |
| **Engineering** | Lead Time, Defect Escape Rate, Technical Debt Trajectory | Every milestone review |
| **Operations** | System Availability, MTTR, Post-Mortem Completion Rate | Continuous monitoring with periodic review |
| **Governance** | Compliance Rate, Decision Traceability Coverage, Gate Cycle Time | Every governance review cycle |
| **Knowledge** | Knowledge Reuse Rate, Staleness Index, Knowledge Compounding Indicator | Every portfolio review cycle |
| **AI Platform** | Cost Efficiency, Provider Health Score, Quota Utilization, Concentration Index | Continuous monitoring with periodic review |

### 17.11 How Metrics Support Organizational Improvement

Metrics are not endpoints — they are the **evidence base for organizational evolution**. The connection between metrics and improvement follows a defined cycle:

```
Measure → Detect → Investigate → Understand → Improve → Re-measure
```

1. **Measure** — Metrics are collected continuously or at defined intervals across all organizational functions
2. **Detect** — Metric thresholds identify when organizational health is shifting from Healthy to Warning, or from Warning to Critical
3. **Investigate** — Degradation triggers root cause investigation — not blame assignment, but systemic understanding
4. **Understand** — Investigation reveals whether the issue is structural (organizational design), procedural (workflow design), or circumstantial (temporary conditions)
5. **Improve** — Structural and procedural issues produce governed change proposals. Circumstantial issues produce corrective actions and monitoring adjustments
6. **Re-measure** — After improvement is implemented, the same metrics evaluate whether the improvement achieved its intended effect

This cycle ensures that organizational evolution is **evidence-based, not opinion-based**. The organization changes because the data shows it should, not because someone believes it should.

### 17.12 Metrics Anti-Patterns

The organization must guard against common metrics failures:

| Anti-Pattern | Description | Organizational Response |
|---|---|---|
| **Vanity metrics** | Metrics that always look good but do not reflect actual organizational health | Replace with metrics that have meaningful variance and connect to actionable decisions |
| **Gaming** | Behavior optimized to improve a metric without improving the underlying capability | Investigate when metrics improve but correlated organizational outcomes do not |
| **Metric overload** | Collecting more metrics than the organization can meaningfully act on | Periodically review all metrics and retire those that do not inform active decisions |
| **Measurement without action** | Metrics are collected and reported but never used to drive improvement | Every metric must have a defined owner, a defined response threshold, and a defined action when the threshold is breached |
| **Snapshot bias** | Drawing conclusions from a single measurement point rather than trends | Metrics are evaluated as trends over time, not as isolated values |

---

## Closing

This document defines how Karsa operates as an organization. It establishes the structures, authorities, governance processes, knowledge management practices, and operational principles that govern all organizational activity.

The Organizational Model is the second-highest artifact in Karsa's hierarchy — subordinate only to the Organizational Vision. All other organizational artifacts, processes, and decisions must be consistent with this model.

This model is designed to evolve. As the organization matures through its stages, the model will be refined, extended, and improved — always through governed change, always with recorded rationale, and always with human approval.

**The organization is the product. The model is its blueprint.**

---

*This document is maintained by the Organizational Design Agent and evolves as the organization matures. All changes require Human Founder approval.*
