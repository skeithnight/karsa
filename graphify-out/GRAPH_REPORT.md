# Graph Report - .  (2026-06-21)

## Corpus Check
- 480 files · ~390,147 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 128 nodes · 151 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Attribution & Performance|Attribution & Performance]]
- [[_COMMUNITY_Governance Documentation|Governance Documentation]]
- [[_COMMUNITY_Governance Engine & Decisions|Governance Engine & Decisions]]
- [[_COMMUNITY_Execution & Cost Infrastructure|Execution & Cost Infrastructure]]
- [[_COMMUNITY_Provider & Thesis Lifecycle|Provider & Thesis Lifecycle]]
- [[_COMMUNITY_Observability & Tracing|Observability & Tracing]]
- [[_COMMUNITY_Capability Security|Capability Security]]
- [[_COMMUNITY_Workspace & Sandbox Execution|Workspace & Sandbox Execution]]
- [[_COMMUNITY_CIO Dashboard & Investment|CIO Dashboard & Investment]]
- [[_COMMUNITY_Persistence & Events|Persistence & Events]]
- [[_COMMUNITY_Observability Foundation|Observability Foundation]]

## God Nodes (most connected - your core abstractions)
1. `Workflow Rules` - 8 edges
2. `Governance Engine` - 8 edges
3. `Attribution Engine` - 8 edges
4. `Documentation Style Guide` - 7 edges
5. `Engineering Standards` - 7 edges
6. `Karsa Investment Firm Agent Dashboard - Comprehensive Audit & Enhancement Report` - 6 edges
7. `Thesis Engine` - 6 edges
8. `ADR-022: Governance Engine Ownership and Context Boundaries` - 5 edges
9. `ADR-023: PDP-PEP Interception and Replay Bypass Architecture` - 5 edges
10. `Provider Registry` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Evidence Before Status` --semantically_similar_to--> `Quality Assurance Thresholds`  [INFERRED] [semantically similar]
  WORKFLOW_RULES.md → ENGINEERING_STANDARDS.md
- `Karsa Documentation Index` --references--> `Documentation Style Guide`  [EXTRACTED]
  README.md → DOCUMENTATION_STYLE_GUIDE.md
- `Workflow Rules` --references--> `Directory Enforcement`  [EXTRACTED]
  WORKFLOW_RULES.md → DOCUMENTATION_STYLE_GUIDE.md
- `Meta-Governance` --conceptually_related_to--> `ADR Governance and Lifecycle`  [INFERRED]
  ENGINEERING_STANDARDS.md → DOCUMENTATION_STYLE_GUIDE.md
- `Traceability Matrix` --conceptually_related_to--> `Sprint Lifecycle`  [INFERRED]
  TRACEABILITY_MATRIX.md → WORKFLOW_RULES.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Core Governance Document Trinity** — docs_documentation_style_guide, docs_engineering_standards, docs_workflow_rules [EXTRACTED 1.00]
- **Execution Isolation Mechanisms** — docs_docker_sandbox_execution, docs_git_worktree_sandbox, docs_execution_contracts, docs_execution_planner [INFERRED 0.75]
- **Capability Lifecycle Governance** — docs_capability_based_security, docs_capability_urn_identity, docs_capability_registration_governance, docs_capability_definition_aggregate, docs_capability_owner [INFERRED 0.85]
- **Observability Cross-Context Correlation** —  [EXTRACTED 1.00]
- **Governance PDP-PEP Interception Pattern** —  [EXTRACTED 1.00]
- **Thesis Lifecycle with Cross-Engine Boundaries** —  [EXTRACTED 1.00]

## Communities (11 total, 1 thin omitted)

### Community 0 - "Attribution & Performance"
Cohesion: 0.12
Nodes (25): ADR-020: Capability Registry Identity, Lifecycle, and Governance, ADR-021: Capability Dependency Resolution and Cycle Prevention, ADR-027: Attribution Engine Context Ownership and Boundaries, ADR-028: Multi-Dimensional Cost Attribution Model, ADR-031: Performance Engine Context Ownership and Boundaries, AttributionAdjustment, Attribution Engine, AttributionRecord (+17 more)

### Community 1 - "Governance Documentation"
Cohesion: 0.12
Nodes (21): ADR-010: Phase 1 Architecture Freeze, ADR Governance and Lifecycle, Architecture Freeze, Automated Governance Checks, Commit Traceability, Directory Enforcement, Documentation Closure Gate, Documentation Is Source of Truth (+13 more)

### Community 2 - "Governance Engine & Decisions"
Cohesion: 0.14
Nodes (15): ADR-019: Provider Routing, Failover, Telemetry, and Cost Tracking, ADR-022: Governance Engine Ownership and Context Boundaries, ADR-023: PDP-PEP Interception and Replay Bypass Architecture, GovernanceAuditChain, GovernanceBudgetCache, GovernanceDecision Aggregate, Governance-Re-evaluated Failover, PDP-PEP Interception Architecture (+7 more)

### Community 3 - "Execution & Cost Infrastructure"
Cohesion: 0.15
Nodes (15): ADR-004: Cost Governance, ADR-005: Execution Contracts, ADR-012: Artifact vs Evidence, ADR-014: Execution Planner, ADR-015: Job Queue Architecture, ADR-017: Capability Execution Contracts and Replay Decoupling, Artifact vs Evidence, CapabilityJob Serialization (+7 more)

### Community 4 - "Provider & Thesis Lifecycle"
Cohesion: 0.20
Nodes (12): ADR-018: Provider Identity, Registry, and Lifecycle Governance, ADR-029: Thesis Engine Bounded Context and Ownership Boundaries, ADR-030: Thesis Lifecycle State Machine and Version Evolution, ProviderDefinition, ProviderHealthState, Provider Lifecycle FSM, ThesisDefinition, ThesisExecutionBinding (+4 more)

### Community 5 - "Observability & Tracing"
Cohesion: 0.22
Nodes (10): ADR-024: Observability Trace and Span Model, ADR-025: Cross-Context Correlation Strategy, ADR-026: Trace Retention and Archival Architecture, Adaptive Sampling, Cross-Context Correlation Strategy, Event Streaming Platform, Observability Trace and Span Model, Three-Tiered Trace Retention and Archival (+2 more)

### Community 6 - "Capability Security"
Cohesion: 0.22
Nodes (9): ADR-003: Capability-Based Security, ADR-007: Governance Layer, ADR-016: Capability Identity and Registration Governance, Capability-Based Security, CapabilityDefinition Aggregate, CapabilityOwner Value Object, Capability Registration Governance Gate, Capability URN Identity (+1 more)

### Community 7 - "Workspace & Sandbox Execution"
Cohesion: 0.25
Nodes (8): ADR-001: Workspace Lineage, ADR-006: Docker Sandbox Execution, ADR-008: Multi-Agent Coordination, ADR-013: Git Worktree Sandbox, Docker Sandbox Execution, Git Worktree Sandbox, Multi-Agent Coordination, Workspace Lineage

### Community 8 - "CIO Dashboard & Investment"
Cohesion: 0.38
Nodes (7): CIO Dashboard Component Hierarchy, IDX Domain Context, Investment Workflow Pipeline, Multi-Agent Debate Mechanism, Three-Layer Knowledge System, Karsa Investment Firm Agent Dashboard - Comprehensive Audit & Enhancement Report, CIO 5-Second Comprehension Design Rationale

### Community 9 - "Persistence & Events"
Cohesion: 0.50
Nodes (4): ADR-002: Hybrid Persistence, ADR-011: EventBus Design, Hybrid Persistence, Synchronous Singleton EventBus

## Knowledge Gaps
- **36 isolated node(s):** `Naming Conventions`, `Commit Traceability`, `Zero-Tolerance Secrets Policy`, `Release and Deployment Governance`, `Automated Governance Checks` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Governance Engine` connect `Attribution & Performance` to `Governance Engine & Decisions`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `Attribution Engine` connect `Attribution & Performance` to `Governance Engine & Decisions`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `Thesis Engine` connect `Attribution & Performance` to `Provider & Thesis Lifecycle`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **What connects `Naming Conventions`, `Commit Traceability`, `Zero-Tolerance Secrets Policy` to the rest of the system?**
  _43 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Attribution & Performance` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._
- **Should `Governance Documentation` be split into smaller, more focused modules?**
  _Cohesion score 0.12380952380952381 - nodes in this community are weakly interconnected._
- **Should `Governance Engine & Decisions` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._