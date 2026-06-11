---
status: active
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: 2026-09-11
---

# Single Source of Truth (SSOT) Matrix

To prevent cognitive drift and artifact sprawl, the following mapping defines the **strict** canonical source for every major platform concept. No other document may redefine these concepts; they may only link to the canonical source.

| Major Concept | Canonical Document | Referencing Documents |
|---|---|---|
| **System Overview** | `architecture/01-system-overview.md` | All READMEs |
| **Workflow State Machine** | `architecture/02-execution-platform.md` | `sprint-02-fsm-durability/*` |
| **Execution Hierarchy** | `architecture/02-execution-platform.md` | `sprint-01-observability/*` |
| **Domain Models** | `architecture/02-execution-platform.md` | `sprint-01-observability/*` |
| **Event Flow** | `architecture/02-execution-platform.md` | `sprint-01-observability/*`, `sprint-02-fsm-durability/*` |
| **Persistence Model** | `architecture/02-execution-platform.md` | `sprint-02-fsm-durability/*` |
| **Governance Rules** | `architecture/03-governance-platform.md` | `sprint-03-governance/*` |
| **Failure Taxonomy** | `architecture/03-governance-platform.md` | `sprint-03-governance/*` |
| **Cost Estimation** | `architecture/03-governance-platform.md` | `sprint-03-governance/*` |
| **Execution Contracts** | `architecture/03-governance-platform.md` | `sprint-03-governance/*` |
| **Pricing Registry** | `architecture/04-observability-platform.md` | `sprint-01-observability/*` |
| **Metrics & Telemetry** | `architecture/04-observability-platform.md` | `sprint-01-observability/*` |
| **Sandbox & Recovery** | `architecture/05-sandbox-and-recovery.md` | `sprint-02-fsm-durability/*` |
| **Roadmap** | `roadmap/ROADMAP.md` | `PROJECT_DASHBOARD.md` |
| **Project Status** | `PROJECT_DASHBOARD.md` | `README.md` |
