# KARSA Revamp — Development Plan

**Status:** PLANNING
**Generated:** 2026-06-21
**Source:** Revamp documentation audit + Sprint-11/12 architecture baseline
**Principle:** Extend existing architecture. Do not rebuild.

---

## 1. WORKFLOW ARCHITECTURE

Every development unit follows this cycle:

```
┌─────────────────────────────────────────────────────────┐
│                    WORKFLOW CYCLE                         │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐    │
│  │ ARCHITECT│──▶│  AUDIT   │──▶│ IMPLEMENTATION   │    │
│  │ DESIGN   │   │ (review) │   │ PLAN             │    │
│  └──────────┘   └──────────┘   └────────┬─────────┘    │
│                                          │              │
│                                          ▼              │
│                                  ┌──────────────┐       │
│                                  │IMPLEMENTATION│       │
│                                  │  (code)      │       │
│                                  └──────┬───────┘       │
│                                         │               │
│                                         ▼               │
│                                  ┌──────────────┐       │
│                                  │    AUDIT      │       │
│                                  │ (verify)      │       │
│                                  └──────────────┘       │
│                                                          │
│  CIO VALIDATION GATE at each phase transition           │
└─────────────────────────────────────────────────────────┘
```

### Phase Gates

| Gate | Owner | Criteria |
|---|---|---|
| Design → Audit | Architect | Design complete, ADR drafted |
| Audit → Plan | Auditor | No critical findings, ADR accepted |
| Plan → Implementation | PM | Tasks broken down, dependencies clear |
| Implementation → Audit | Coder | Code complete, tests passing |
| Audit → Done | Auditor + CIO | All criteria met, CIO validates output |

---

## 2. PERSONA AGENTS

### 2.1 PM (Product Manager)

**Responsibilities:**
- Break down features into implementable tasks
- Define acceptance criteria
- Track sprint progress
- Prioritize backlog
- Write PRD sections for each phase

**Skills:**
- Task decomposition
- Dependency mapping
- Acceptance criteria writing
- Sprint planning

**Output:** Task lists, acceptance criteria, sprint plans

**Validation:** CIO approves scope and priorities

---

### 2.2 Architect

**Responsibilities:**
- Design bounded context extensions
- Write ADRs for new modules
- Define port interfaces and contracts
- Ensure DDD compliance
- Map revamp proposals to existing architecture

**Skills:**
- DDD modeling
- Event sourcing design
- CQRS pattern application
- Port/adapter architecture
- ADR writing

**Output:** ADRs, domain models, contract definitions, architecture diagrams

**Validation:** Auditor reviews ADRs; CIO validates business logic correctness

---

### 2.3 Coder (Implementation Engineer)

**Responsibilities:**
- Implement domain models, services, repositories
- Write unit and integration tests
- Follow existing code conventions
- Implement transport endpoints
- Wire dependencies via bootstrap

**Skills:**
- Python 3.12+ / FastAPI / Pydantic
- DDD implementation (aggregates, events, VOs)
- Event sourcing (write-once, outbox pattern)
- CQRS (projections, read models)
- Test-driven development

**Output:** Source code, tests, migrations

**Validation:** Auditor reviews code quality; all tests must pass

---

### 2.4 Auditor

**Responsibilities:**
- Verify ADR compliance
- Run architecture boundary checks
- Verify test coverage
- Check dependency direction
- Validate production readiness
- Review security surface

**Skills:**
- Architecture audit
- Dependency analysis
- Test coverage assessment
- Security review
- Performance analysis

**Output:** Audit reports with findings (Critical/Major/Minor)

**Validation:** CIO approves remediation for critical findings

---

### 2.5 CIO (User / Domain Validator)

**Responsibilities:**
- Validate investment domain correctness
- Review CIO dashboard output
- Confirm risk mandate rules
- Validate IDX domain context
- Approve decision workflow logic
- Sign off on each phase

**Skills:**
- Investment domain expertise
- Risk management knowledge
- IDX market understanding
- Executive decision-making

**Output:** Validation sign-offs, domain correction feedback

**Validation:** Self (business owner)

---

## 3. DEVELOPMENT PHASES

### Phase 0: Foundation Alignment (Week 1)

**Objective:** Map revamp domain knowledge to existing architecture.

| Task | Owner | Output |
|---|---|---|
| Extract IDX domain context from revamp docs | Architect + CIO | `docs/investment_context/MANDATE.md` |
| Extract risk policy rules | Architect + CIO | `docs/investment_context/RISK_POLICY.md` |
| Extract decision framework | Architect + CIO | `docs/investment_context/DECISION_PROCESS.md` |
| Map revamp features to existing bounded contexts | Architect | Feature-to-module mapping table |
| Identify gaps (what doesn't exist yet) | Architect | Gap analysis document |
| CIO validates domain knowledge accuracy | CIO | Sign-off |

**Gate:** Auditor reviews mapping. CIO validates domain accuracy.

---

### Phase 1: Investment Workflow Extension (Weeks 2-4)

**Objective:** Extend `workflow/` module to support investment-specific decision pipelines.

#### 1A: Architecture Design

| Task | Owner |
|---|---|
| ADR: Investment decision workflow bounded context | Architect |
| Design investment workflow aggregate | Architect |
| Define investment decision events | Architect |
| Design analyst role port interfaces | Architect |

#### 1B: Audit

| Task | Owner |
|---|---|
| Review ADR for DDD compliance | Auditor |
| Verify no conflicts with existing workflow module | Auditor |
| CIO validates workflow matches investment process | CIO |

#### 1C: Implementation Plan

| Task | Owner |
|---|---|
| Break into Sprint-13 tasks | PM |
| Define acceptance criteria per task | PM |
| Map dependencies (which existing modules to extend) | PM |

#### 1D: Implementation

| Task | Owner |
|---|---|
| Create `src/karsa/investment_workflow/` bounded context | Coder |
| Implement `InvestmentDecision` aggregate | Coder |
| Implement decision events (Proposed, Debated, Approved, Rejected) | Coder |
| Implement analyst role port interfaces | Coder |
| Implement workflow state machine (PROPOSED → DEBATING → DECIDING → APPROVED) | Coder |
| Wire bootstrap and ports | Coder |
| Write unit tests (aggregates, events, VOs) | Coder |
| Write integration tests (workflow end-to-end) | Coder |

#### 1E: Audit

| Task | Owner |
|---|---|
| Architecture boundary verification | Auditor |
| Test coverage assessment (target: 90%+) | Auditor |
| ADR compliance check | Auditor |
| CIO validates decision workflow correctness | CIO |

**Gate:** All tests pass. No architecture violations. CIO sign-off.

---

### Phase 2: Knowledge System (Weeks 5-6)

**Objective:** Extend `memory/` module to support investment-specific knowledge retrieval.

#### 2A: Architecture Design

| Task | Owner |
|---|---|
| ADR: Investment knowledge bounded context | Architect |
| Design research document aggregate | Architect |
| Design knowledge retrieval port interface | Architect |
| Define knowledge events (Loaded, Queried, Archived) | Architect |

#### 2B: Audit

| Task | Owner |
|---|---|
| Review ADR | Auditor |
| Verify no conflicts with existing memory module | Auditor |
| CIO validates knowledge categories match investment needs | CIO |

#### 2C: Implementation Plan

| Task | Owner |
|---|---|
| Break into Sprint-14 tasks | PM |
| Define acceptance criteria | PM |

#### 2D: Implementation

| Task | Owner |
|---|---|
| Create `src/karsa/investment_knowledge/` bounded context | Coder |
| Implement `ResearchDocument` aggregate | Coder |
| Implement knowledge repository port (ABC) | Coder |
| Implement in-memory test double | Coder |
| Implement Postgres repository (with pgvector if available) | Coder |
| Implement knowledge retrieval service | Coder |
| Wire bootstrap | Coder |
| Write tests | Coder |

#### 2E: Audit

| Task | Owner |
|---|---|
| Architecture verification | Auditor |
| Test coverage | Auditor |
| CIO validates knowledge retrieval quality | CIO |

**Gate:** All tests pass. CIO sign-off.

---

### Phase 3: Investment Memos (Weeks 7-8)

**Objective:** Extend `review_engine/` or create new bounded context for investment memos.

#### 3A: Architecture Design

| Task | Owner |
|---|---|
| ADR: Investment memo bounded context | Architect |
| Design memo aggregate (thesis, conviction, entry/exit, realized return) | Architect |
| Define memo events (Drafted, Approved, Rejected, Closed) | Architect |
| Design memo-to-performance feedback loop | Architect |

#### 3B-3E: Same cycle as above.

**Gate:** All tests pass. CIO validates memo format matches investment process.

---

### Phase 4: CIO Dashboard (Weeks 9-11)

**Objective:** Build CIO dashboard pages in `karsa-web/`.

#### 4A: Architecture Design

| Task | Owner |
|---|---|
| Design 3-tier dashboard layout (Summary → Analysis → Detail) | Architect |
| Define API contracts (queries) for dashboard data | Architect |
| Design component hierarchy | Architect |
| Map dashboard widgets to existing projection data | Architect |

#### 4B: Audit

| Task | Owner |
|---|---|
| Review API contracts for completeness | Auditor |
| Verify projections provide required data | Auditor |
| CIO validates dashboard layout matches executive needs | CIO |

#### 4C: Implementation Plan

| Task | Owner |
|---|---|
| Break into Sprint-15/16 tasks | PM |
| Define component-level acceptance criteria | PM |
| Map components to API endpoints | PM |

#### 4D: Implementation

| Task | Owner |
|---|---|
| Create `karsa-web/src/app/cio-dashboard/` pages | Coder |
| Implement `PortfolioStatusCard` component | Coder |
| Implement `RiskTrafficLight` component | Coder |
| Implement `StockDecisionCard` component | Coder |
| Implement `HoldingsTable` component (AG Grid) | Coder |
| Implement `PerformanceAttribution` chart (Recharts) | Coder |
| Implement `RiskHeatmap` component | Coder |
| Implement TanStack Query hooks for data fetching | Coder |
| Implement DTO → ViewModel mappers | Coder |
| Implement API endpoints in transport layer | Coder |
| Write component tests (Vitest) | Coder |
| Write mapper unit tests | Coder |

#### 4E: Audit

| Task | Owner |
|---|---|
| Component test coverage | Auditor |
| API endpoint verification | Auditor |
| Performance check (load time < 2s) | Auditor |
| CIO validates dashboard usability | CIO |
| CIO validates data accuracy | CIO |

**Gate:** All tests pass. Dashboard loads < 2s. CIO sign-off.

---

### Phase 5: Governance & Risk Integration (Weeks 12-13)

**Objective:** Extend `governance/` module with investment mandate rules.

#### 5A: Architecture Design

| Task | Owner |
|---|---|
| ADR: Investment mandate governance | Architect |
| Design mandate rule evaluation service | Architect |
| Design risk officer veto workflow | Architect |
| Define governance events (MandateChecked, VetoIssued, Escalated) | Architect |

#### 5B-5E: Same cycle.

**Gate:** All tests pass. CIO validates mandate rules match fund requirements.

---

### Phase 6: Performance Attribution (Weeks 14-15)

**Objective:** Extend `attribution_engine/` with investment-specific attribution.

#### 6A: Architecture Design

| Task | Owner |
|---|---|
| ADR: Investment performance attribution | Architect |
| Design attribution decomposition (selection, allocation, beta, residual) | Architect |
| Design realized return tracking | Architect |
| Design backtest framework | Architect |

#### 6B-5E: Same cycle.

**Gate:** All tests pass. CIO validates attribution decomposition accuracy.

---

### Phase 7: IDX Domain Enhancement (Weeks 16-17)

**Objective:** Inject IDX-specific domain knowledge into agents and dashboard.

#### 7A: Architecture Design

| Task | Owner |
|---|---|
| Design IDX context injection mechanism | Architect |
| Define conglomerate group mappings | Architect |
| Design MSCI float tracking | Architect |
| Design dividend calendar integration | Architect |

#### 7B-7E: Same cycle.

**Gate:** All tests pass. CIO validates IDX domain accuracy.

---

## 4. SPRINT MAPPING

| Sprint | Phase | Focus | Key Deliverables |
|---|---|---|---|
| Sprint-13 | Phase 1 | Investment Workflow | Decision aggregate, events, workflow state machine |
| Sprint-14 | Phase 2 | Knowledge System | Research document aggregate, retrieval service |
| Sprint-15 | Phase 3 | Investment Memos | Memo aggregate, approval workflow, realized returns |
| Sprint-16 | Phase 4a | CIO Dashboard Backend | API endpoints, query services, projections |
| Sprint-17 | Phase 4b | CIO Dashboard Frontend | Dashboard pages, components, data hooks |
| Sprint-18 | Phase 5 | Governance & Risk | Mandate rules, veto workflow, compliance checks |
| Sprint-19 | Phase 6 | Performance Attribution | Attribution decomposition, backtest framework |
| Sprint-20 | Phase 7 | IDX Domain | Conglomerate maps, MSCI tracking, dividend calendar |

---

## 5. AGENT WORKFLOW SCRIPTS

### 5.1 Design Phase Script

```
INPUT: Feature description from revamp docs
PROCESS:
  1. Architect reads feature description
  2. Architect maps to existing bounded contexts
  3. Architect writes ADR (new module or extension)
  4. Architect defines domain model (aggregate, events, VOs)
  5. Architect defines port interfaces
  6. Auditor reviews ADR for DDD compliance
  7. CIO validates domain correctness
OUTPUT: Accepted ADR + domain model
```

### 5.2 Implementation Phase Script

```
INPUT: Accepted ADR + domain model
PROCESS:
  1. PM breaks into tasks with acceptance criteria
  2. Coder implements in order: VOs → Events → Aggregates → Repos → Services → Tests
  3. Coder runs tests after each component
  4. Coder wires bootstrap and transport
  5. Auditor runs architecture boundary check
  6. Auditor runs test coverage check
  7. CIO validates output matches domain expectations
OUTPUT: Working code + passing tests + audit report
```

### 5.3 Audit Phase Script

```
INPUT: Implemented code
PROCESS:
  1. Auditor checks dependency direction (grep imports)
  2. Auditor checks aggregate boundaries (no cross-aggregate mutation)
  3. Auditor checks event immutability (frozen dataclasses)
  4. Auditor checks test coverage (pytest --cov)
  5. Auditor checks OpenAPI schema (if transport added)
  6. Auditor produces findings report (Critical/Major/Minor)
  7. CIO validates business logic correctness
OUTPUT: Audit report + CIO sign-off
```

---

## 6. EXTENSION POINTS (Not Rebuilds)

| Revamp Proposal | Extension Point | New Module? |
|---|---|---|
| Investment analyst agents | `workflow/` extension + new port interfaces | Yes: `investment_workflow/` |
| Three-layer knowledge | `memory/` extension | Yes: `investment_knowledge/` |
| Investment memos | `review_engine/` extension or new context | Yes: `investment_memo/` |
| CIO Dashboard | `karsa-web/` new pages | No: extend existing |
| Risk mandate rules | `governance/` extension | No: extend existing |
| Performance attribution | `attribution_engine/` extension | No: extend existing |
| IDX domain context | `docs/investment_context/` + prompt injection | No: documentation only |
| Broker integration | `execution/` (already has port) | No: implement existing port |

---

## 7. DEPENDENCY GRAPH

```
Phase 0 (Foundation)
    │
    ▼
Phase 1 (Workflow) ──────────────────────┐
    │                                     │
    ▼                                     ▼
Phase 2 (Knowledge) ──▶ Phase 3 (Memos)
    │                     │
    └──────────┬──────────┘
               │
               ▼
         Phase 4 (Dashboard) ◀── needs data from all above
               │
               ▼
         Phase 5 (Governance) ◀── extends governance module
               │
               ▼
         Phase 6 (Attribution) ◀── extends attribution module
               │
               ▼
         Phase 7 (IDX Domain) ◀── documentation + prompt injection
```

---

## 8. RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Revamp docs over-scope features | High | High | PM enforces MVP-first approach |
| Architecture drift from DDD principles | Medium | High | Auditor gates at every phase |
| CIO unavailable for validation | Medium | Medium | Async validation via documented criteria |
| IDX domain knowledge inaccurate | Low | High | CIO validates all domain content |
| Existing modules can't extend cleanly | Medium | Medium | Architect reviews extension feasibility in Phase 0 |

---

## 9. SUCCESS CRITERIA

### Per Phase

- [ ] ADR accepted (Auditor)
- [ ] Domain model correct (CIO)
- [ ] Implementation complete (Coder)
- [ ] Tests passing (Auditor)
- [ ] Architecture boundaries clean (Auditor)
- [ ] CIO sign-off (CIO)

### Overall

- [ ] Investment decision workflow operational
- [ ] Knowledge system retrievable
- [ ] Investment memos with realized return tracking
- [ ] CIO dashboard loadable in < 2s
- [ ] Risk mandate rules enforced
- [ ] Performance attribution decomposed
- [ ] IDX domain context injected
- [ ] All existing tests still pass (559+)
- [ ] No architecture violations
- [ ] Production-ready deployment

---

**Status:** READY FOR PHASE 0
**Next Step:** Extract IDX domain context from revamp docs → `docs/investment_context/`
