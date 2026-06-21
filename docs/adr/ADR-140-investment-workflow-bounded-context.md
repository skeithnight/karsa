# ADR-140: Investment Workflow Bounded Context

**Status:** PROPOSED
**Date:** 2026-06-21
**Sprint:** 13
**Decision Makers:** Architect, CIO

---

## Context

The platform needs to support investment-specific decision workflows: analyst parallel analysis, bull/bear debate, portfolio manager synthesis, risk officer veto, and committee chair approval. The existing `workflow/` module handles generic code-review workflows (IDEA → DRAFT → REVIEW → APPROVED) and is not suitable for investment domain logic.

The revamp documentation proposes a 7-phase investment workflow. This ADR designs the bounded context that implements it.

---

## Decision

Create `src/karsa/investment_workflow/` as a new bounded context following the established DDD+CQRS+Event Sourcing pattern.

### Why Not Extend `workflow/`

The existing `workflow/` module is tightly coupled to code-review semantics:
- `AgentOrchestrator` calls LLM providers for PE/review generation
- `ToolExecutor` runs pytest
- State machine (IDEA → DRAFT → REVIEW) reflects code review lifecycle
- Event types (PE_COMPLETE, REVIEW_COMPLETE) are code-review specific

Investment workflows have fundamentally different:
- States (ANALYZING → DEBATING → DECIDING → APPROVED)
- Agent roles (Fundamental Analyst, Technical Analyst, etc.)
- Decision criteria (conviction scoring, mandate compliance)
- Output format (investment memos, not code)

Attempting to generalize `workflow/` would violate the Single Responsibility Principle and create a god module.

### Architecture

```
investment_workflow/
  __init__.py
  application/
    __init__.py
    investment_decision_service.py    # Command handler
    analyst_orchestration_service.py  # Parallel analyst execution
    debate_service.py                 # Bull/Bear debate coordination
  domain/
    __init__.py
    aggregates/
      __init__.py
      investment_decision.py          # Main aggregate
    entities/
      __init__.py
      analyst_output.py               # Child entity
      debate_round.py                 # Child entity
    events/
      __init__.py
      investment_workflow_events.py   # 8 domain events
    value_objects/
      __init__.py
      enums.py                        # Decision states, analyst types, conviction
      conviction_score.py             # Conviction scoring (STRONG/MEDIUM/WEAK)
      analyst_score.py                # Individual analyst score (0-10)
      decision_memo.py                # Investment memo value object
    exceptions.py
  infrastructure/
    __init__.py
    repositories/
      __init__.py
      investment_decision_repository.py   # ABC
    persistence/
      __init__.py
      in_memory_investment_decision_repository.py
  projections/
    __init__.py
    investment_decision_projection.py
```

---

## Domain Model

### Aggregate: InvestmentDecision

Write-once aggregate (same pattern as `CapabilityEvolution`).

**Identity:** `decision_id` (URN)

**Business Key:** `(capability_family_id, ticker, decision_date)`

**States:**

| State | Description | Terminal |
|---|---|---|
| `PROPOSED` | Decision initiated, analysis pending | No |
| `ANALYZING` | Analyst agents running in parallel | No |
| `DEBATING` | Bull/Bear debate in progress | No |
| `DECIDING` | Portfolio Manager synthesizing | No |
| `RISK_REVIEW` | Risk Officer reviewing | No |
| `COMMITTEE_REVIEW` | Committee Chair final review | No |
| `APPROVED` | Decision approved for execution | Yes |
| `REJECTED` | Decision rejected | Yes |
| `REVISED` | Sent back for re-analysis | No |
| `SUSPENDED` | Paused (governance or manual) | No |

**Transitions:**

| From | Allowed Targets |
|---|---|
| PROPOSED | ANALYZING, REJECTED |
| ANALYZING | DEBATING, REJECTED, SUSPENDED |
| DEBATING | DECIDING, REJECTED, SUSPENDED |
| DECIDING | RISK_REVIEW, REJECTED, REVISED, SUSPENDED |
| RISK_REVIEW | COMMITTEE_REVIEW, REJECTED, REVISED, SUSPENDED |
| COMMITTEE_REVIEW | APPROVED, REJECTED, REVISED, SUSPENDED |
| REVISED | ANALYZING |
| SUSPENDED | ANALYZING, DEBATING, DECIDING, REJECTED |
| APPROVED | (terminal) |
| REJECTED | (terminal) |

### Child Entities

**AnalystOutput** (stored as JSONB within aggregate):
- `analyst_type`: Fundamental | Technical | Sentiment | Risk | Market
- `score`: 0.0-10.0
- `confidence`: 0.0-1.0
- `output_text`: str
- `tools_used`: List[str]
- `model_version`: str
- `analyzed_at`: datetime

**DebateRound** (stored as JSONB within aggregate):
- `round_number`: int
- `bull_memo`: str
- `bear_memo`: str
- `bull_conviction`: ConvictionScore
- `bear_conviction`: ConvictionScore
- `debated_at`: datetime

### Value Objects

**ConvictionScore** (frozen):
- `level`: STRONG | MEDIUM | WEAK
- `numeric_score`: float (0.0-10.0)
- `analyst_agreement`: int (how many analysts agree)

**AnalystScore** (frozen):
- `analyst_type`: AnalystType enum
- `score`: float (0.0-10.0)
- `confidence`: float (0.0-1.0)
- `metrics`: Dict[str, Any]

**DecisionMemo** (frozen):
- `ticker`: str
- `decision`: BUY | HOLD | SELL | PASS
- `conviction`: ConvictionScore
- `entry_price`: Optional[Decimal]
- `exit_target`: Optional[Decimal]
- `stop_loss`: Optional[Decimal]
- `position_size_pct`: Optional[float]
- `thesis`: str
- `key_metrics`: Dict[str, Any]
- `risks`: List[str]
- `next_review_date`: Optional[date]

### Events (8)

1. **InvestmentDecisionProposedEvent** — decision created
2. **AnalystOutputRecordedEvent** — individual analyst completes
3. **DebateCompletedEvent** — bull/bear debate finishes
4. **DecisionMemoCreatedEvent** — PM creates memo
5. **RiskVetoIssuedEvent** — risk officer rejects/requests revision
6. **DecisionApprovedEvent** — committee approves
7. **DecisionRejectedEvent** — decision rejected
8. **DecisionRevisedEvent** — sent back for re-analysis

### Enums

**DecisionState**: PROPOSED, ANALYZING, DEBATING, DECIDING, RISK_REVIEW, COMMITTEE_REVIEW, APPROVED, REJECTED, REVISED, SUSPENDED

**AnalystType**: FUNDAMENTAL, TECHNICAL, SENTIMENT, RISK, MARKET

**ConvictionLevel**: STRONG, MEDIUM, WEAK

**DecisionType**: BUY, HOLD, SELL, PASS

---

## Transaction Boundaries

### Transaction C: Decision Creation

1. Create InvestmentDecision aggregate
2. Save to repository
3. Save outbox event

### Transaction D: Analyst Recording

1. Load InvestmentDecision
2. Record analyst output (append to aggregate)
3. Update aggregate state
4. Save outbox event

### Transaction E: Decision Finalization

1. Load InvestmentDecision
2. Record debate/memo/approval
3. Update aggregate state
4. Save outbox event
5. Update version registry (if applicable)

---

## Integration Points

| From | To | Mechanism |
|---|---|---|
| `investment_workflow/` | `governance/` | Port interface for mandate checking |
| `investment_workflow/` | `investment_memo/` | Event: DecisionApprovedEvent triggers memo creation |
| `investment_workflow/` | `transport/` | Via facade (Wave-4 pattern) |
| External | `investment_workflow/` | Via contracts (Wave-8 pattern) |

---

## ADR Compliance

| ADR | Compliance |
|---|---|
| ADR-125 (Identity) | UUIDv4 for all identifiers |
| ADR-126 (Rebuild) | TRUNCATE+INSERT for projections |
| ADR-130 (Transaction) | Strict A/B/C/D/E boundaries |
| ADR-133 (Canonical) | Version registry for canonical decisions |
| ADR-135 (Replay) | Context snapshots for deterministic replay |
| ADR-136 (Ordering) | Monotonic evaluation_sequence |

---

## Consequences

### Positive

- Clean separation from code-review workflow
- Investment domain logic isolated in its own bounded context
- Follows established DDD+CQRS+Event Sourcing patterns
- Testable with in-memory repositories

### Negative

- New bounded context to maintain
- Some structural similarity to `workflow/` (acceptable duplication for domain isolation)

### Risks

- Scope creep into agent/LLM integration (mitigated: agent logic lives in application layer, not domain)
- Performance of parallel analyst execution (mitigated: asyncio in application layer)

---

## Acceptance Criteria

- [ ] InvestmentDecision aggregate with 10 states and transition rules
- [ ] 8 domain events with frozen dataclasses
- [ ] 3 child entities (AnalystOutput, DebateRound, DecisionMemo)
- [ ] 4 value objects (ConvictionScore, AnalystScore, DecisionMemo, enums)
- [ ] Repository ABC with in-memory test double
- [ ] Application service for decision lifecycle
- [ ] Unit tests: 50+ tests covering aggregates, events, VOs
- [ ] Integration tests: end-to-end decision flow
- [ ] No imports from `workflow/` module
- [ ] No imports from `governance/` module (port interfaces only)
