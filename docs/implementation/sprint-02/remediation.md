---
status: active
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: Never (Immutable)
---

# Sprint 2 Closure Report & Remediation

## 1. Acceptance Criteria Verification

| Exit Criterion | Status | Evidence Verification |
|---|---|---|
| **`WorkflowState` fully matches architecture matrix** | PASS | Validated in `audit.md` (FSM valid/invalid execution tests). The Enum correctly strictly enforces `IDEA -> DRAFT` and rejects jumps. |
| **Hybrid persistence is operational** | PASS | Validated in `audit.md` (Snapshot & Event Journal Evidence). Files are written natively to `.karsa/workflows/<id>/`. |
| **Crash recovery exactly rehydrates state** | PASS | Validated in `audit.md` (`test_hybrid_persistence_and_recovery` in Pytest output). |
| **Audit evidence produced** | PASS | Full execution logs, raw JSON outputs, and layout proofs captured in `sprint-02/audit.md`. |

## 2. Technical Debt Register

| Debt Item | Description | Consequence if Ignored |
|---|---|---|
| **Journal Compaction** | `EventJournalRepository` appends to `events.jsonl` endlessly. There is no automated compaction merging it into `snapshot.json`. | Large, long-running autonomous workflows will encounter extreme file I/O latency when parsing megabytes of string-based JSON. |
| **Snapshot Schema Migration** | We capture `schema_version`, but `RecoveryEngine` has no intelligence to upgrade a `schema_version: 1` payload to a future `schema_version: 2`. | Backwards incompatibility during future platform updates will corrupt active in-flight workflows. |
| **Lock Heartbeat Strategy** | `WorkflowLockManager` uses a fixed static TTL. Long-running LLM inferences might naturally exceed the TTL, allowing another process to blindly overwrite the lock. | Dual-brain split concurrency causing corrupt, interspersed `events.jsonl` lines. |
| **Recovery Determinism Validation** | Events are replayed without explicitly hashing the transition logic. If the platform logic is updated midway through a crash, replaying old events might yield a different state. | State machine integrity corruption during hot-restarts across platform versions. |

## 3. Risks Deferred To Future Sprints

| Risk Domain | Owner | Severity | Target Sprint | Remediation Strategy |
|---|---|---|---|---|
| **Dual-Brain Lock Corruption** | Karsa Platform Eng | HIGH | Sprint 3 / Governance | Replace fixed TTL with a background heartbeat thread, or shift locking to `fcntl` OS-level file locking. |
| **Event Journal Infinite Growth** | Karsa Data Eng | MEDIUM | Sprint 4 / Optimization | Implement a snapshot threshold (e.g. compact to `snapshot.json` every 50 events). |
| **Lack of Snapshot Schema Upgrades** | Karsa Architecture | LOW | Sprint 5 / Routing | Implement a `MigrationEngine` interceptor on the `SnapshotRepository.load()` method. |

## 4. Sprint Closure Verdict

**PASS**

**Justification**: Sprint 2 successfully delivered all core required capabilities of the FSM and Durability Blueprint without modifying Sprint 1 observability systems or violating the Architecture Freeze. The technical debt introduced is heavily isolated (e.g., locking TTL logic, compaction thresholds) and does not structurally compromise the hybrid persistence design or the state transition enforcer. 

The architecture holds, the execution behaves mathematically perfectly as proven by the `audit.md`, and the workspace is officially prepared to proceed to **Sprint 3: Governance**.
## 5. Repository Hygiene Review

### Overview
A comprehensive repository hygiene review was conducted to ensure no ephemeral runtime data, execution logs, or local secrets pollute the source control system. The `.gitignore` was entirely refactored into strict categorical blocks.

### Protected Artifacts Verification
The `.gitignore` has been successfully hardened while strictly ensuring the following files **remain tracked**:
- Architecture models (`docs/architecture/*.md`)
- ADRs (`docs/adr/*.md`)
- Roadmap and sprint implementation files (`docs/implementation/sprint-XX/*.md`)
- Source code (`src/karsa/**/*.py`)

### Ignore Rule Justifications

| Category | Rules | Justification |
|---|---|---|
| **Runtime Workspaces** | `workspace/`, `.karsa/`, `test_workspace*/` | Prevents the commit of heavy, ephemeral sandbox git clones or test outputs generated during `pytest` executions. |
| **Workflow Data** | `**/workflows/`, `**/metrics/`, `*.jsonl` | Prevents the commit of active FSM state locks, crash recovery snapshots, and potentially sensitive prompt strings inside event journals. |
| **Python Tooling** | `__pycache__/`, `.pytest_cache/`, `*.pyc` | Prevents polluting diffs with machine-specific byte-compiled caches. |
| **Virtual Environments** | `.venv/`, `venv/` | Blocks the commitment of thousands of pip dependency files that belong in `uv.lock`. |
| **IDE / OS Files** | `.vscode/`, `.DS_Store` | Prevents local developer configurations and OS metadata from forcing conflicts. |
| **Local Secrets** | `.env`, `*.pem`, `*.key` | Critical security boundary to prevent LLM API keys (`GEMINI_API_KEY`) from leaking. |

### `.karsa/` Isolation Strategy Recommendation

**Recommendation: OPTION A (Fully Ignored)**

*Justification*: The `.karsa/` directory within the platform repository itself is purely used for local development testing, containing transient metrics ledgers and mock snapshots. Fully ignoring it ensures test artifacts never leak. Any structural configuration required for the platform (like `pricing.json` bounds) should be shipped as `src/karsa/config/pricing.default.json` and selectively instantiated by users in their own target repositories, rather than tracking `.karsa/` globally in Karsa's source tree.
