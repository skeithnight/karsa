# Workflow State Tracking Audit

## Root Cause Analysis

### Bug 1: Incorrect Cycle Reporting in `karsa status`

**Symptom**: `karsa status` reported `Current Cycle: 1` even though review_metrics.json showed 2 cycles executed (DECISION_001=REJECT, DECISION_002=APPROVE).

**Root Cause**: The status command in `cli.py` read the cycle count from `ObservabilityManager.get_status_info()`, which calculated `revision_count` by counting files in `docs/revisions/`:

```python
# BEFORE (cli.py:154)
typer.echo(f"Current Cycle: {info['revision_count']}")

# BEFORE (manager.py:142-145)
revision_count = 0
revisions_dir = self.karsa_dir.parent / "docs" / "revisions"
if revisions_dir.exists():
    revision_count = len(list(revisions_dir.glob("*.md")))
```

This was wrong because:
1. Revision files are written by `ProductEngineerAgent.revise_design()` which only runs on REJECT cycles (not on the final APPROVE cycle)
2. Cycle 1 = first review (no revision file yet), Cycle 2 = second review → only REVISION_001.md exists → `revision_count = 1` → reports "Current Cycle: 1"

**Fix**: State controller now persists `current_cycle` as an authoritative field in `state.json`. The engine updates it at the start of each review cycle via `self.state.update_cycle(cycle)`. The status command reads directly from `state.json`.

### Bug 2: `state.json` Missing Critical Fields

**Symptom**: `state.json` only contained `current_state` and `idea`, making it impossible to reconstruct workflow status without re-scanning artifact directories.

**Root Cause**: The `StateController.initialize()` method only set two fields:
```python
# BEFORE
initial_state = {
    "current_state": WorkflowState.IDEA.value,
    "idea": idea
}
```

**Fix**: Extended to include all canonical workflow state fields.

### Bug 3: Decision Reason Always "Unknown"

**Symptom**: Decision files (DECISION_001.md, DECISION_002.md) contained `Reason: Unknown`.

**Root Cause**: The engine's reason extraction regex looked for `# Rejection Reason` or `# Approval Reason` headings:
```python
# BEFORE (engine.py:115)
reason_match = re.search(r'# (?:Rejection|Approval) Reason\n(.*?)(?:\n#|$)', review_text, re.DOTALL)
```

But the review format uses `# Summary` for the reason text, not `# Rejection Reason`. The regex never matched, so `reason` stayed as `"Unknown"`.

**Fix**: Added `_extract_decision_reason()` with multiple fallback patterns:
1. Try `# Rejection Reason` / `# Approval Reason`
2. Try `## Rejection Reason` / `## Approval Reason`
3. Try `# Summary` / `## Summary`
4. Synthesize from outcome and metrics (guaranteed non-empty)

### Bug 4: Missing Provider Rotation Trace Events

**Symptom**: Provider rotation was working correctly but `trace.log` didn't record key-level events (which key was selected, suspended, recovered, or rotated).

**Root Cause**: `ProviderPool` had no observability hooks. `ProviderManager` logged high-level events (`ProviderRequestStarted`, `FallbackActivated`) but not key-specific events.

**Fix**: Added `trace_fn` callback to `ProviderPool` and injected specific events: `KeySelected`, `KeySuspended`, `KeyRecovered`, `QuotaExceeded`. Added `KeyRotated` and `ProviderUnavailable` events to `ProviderManager`.

---

## Before vs After

### state.json

**Before:**
```json
{
    "current_state": "APPROVED",
    "idea": "Build a notes app"
}
```

**After:**
```json
{
    "current_state": "APPROVED",
    "idea": "Build a notes app",
    "current_cycle": 2,
    "latest_decision": "APPROVE",
    "open_blocking_issues": 0,
    "open_non_blocking_issues": 0,
    "resolved_issues": 1,
    "last_updated_timestamp": "2026-06-11T11:00:00.000+00:00",
    "provider_summary": {}
}
```

### Decision Files

**Before:**
```
Decision ID: 001
Agent: ReviewAgent
Decision: REJECT
Reason:
Unknown
Evidence:
Review text
Provider: mock-llm
Key Fingerprint: none
Source: karsa-agent
Confidence: 0.85
Timestamp: 2026-06-11T11:00:00.000+00:00
```

**After:**
```
Decision ID: 001
Agent: ReviewAgent
Decision: REJECT
Reason:
Review rejected: 1 blocking issues remain unresolved. 0 non-blocking issues. 0 issues resolved.
Evidence:
1 blocking issues, 0 non-blocking.
Provider: mock-llm
Key Fingerprint: none
Source: karsa-agent
Confidence: 0.85
Timestamp: 2026-06-11T11:00:00.000+00:00
```

### Status Command

**Before:**
```
Current Cycle: 1          ← WRONG (inferred from revision file count)
Latest Decision: APPROVE  ← Correct (read from decision files)
```

**After:**
```
Current Cycle: 2          ← CORRECT (read from state.json)
Latest Decision: APPROVE  ← Correct (read from state.json)
```

### trace.log

**Before:**
```
2026-06-11T11:00:00.000Z
ProviderRequestStarted

2026-06-11T11:00:00.100Z
ProviderRequestSucceeded

2026-06-11T11:00:00.200Z
FallbackActivated
```

**After:**
```
2026-06-11T11:00:00.000Z
KeySelected:397339b1

2026-06-11T11:00:00.050Z
ProviderRequestStarted

2026-06-11T11:00:00.100Z
QuotaExceeded

2026-06-11T11:00:00.100Z
KeySuspended:397339b1

2026-06-11T11:00:00.150Z
KeyRotated:397339b1->eaa0f0b4

2026-06-11T11:00:00.150Z
FallbackActivated

2026-06-11T11:00:00.200Z
KeySelected:eaa0f0b4

2026-06-11T11:00:00.250Z
ProviderRequestStarted

2026-06-11T11:00:00.350Z
ProviderRequestSucceeded
```

---

## State Model Documentation

### Schema: `.karsa/state.json`

| Field | Type | Description |
|-------|------|-------------|
| `current_state` | string (enum) | Current workflow state: IDEA, DRAFT, REVIEW, REVISION, APPROVED, ESCALATED, IMPLEMENTATION, RELEASE, DONE, FAILED, AWAITING_PROVIDER |
| `idea` | string | The original idea/project description |
| `current_cycle` | int | The last executed review cycle number (1-indexed). 0 = no reviews yet |
| `latest_decision` | string | Latest review decision: NONE, APPROVE, REJECT |
| `open_blocking_issues` | int | Count of currently open blocking issues |
| `open_non_blocking_issues` | int | Count of currently open non-blocking issues |
| `resolved_issues` | int | Count of resolved issues |
| `last_updated_timestamp` | string (ISO 8601) | Last time state was updated |
| `provider_summary` | object | Optional provider status summary |

### Invariants

1. `current_cycle` is updated at the **start** of each review cycle
2. `latest_decision` is updated after each review outcome is determined
3. `open_blocking_issues`, `open_non_blocking_issues`, `resolved_issues` are synced after each review
4. `last_updated_timestamp` is auto-updated on every `save_state()` call
5. `state.json` is the **single source of truth** — status command reads only from it

---

## Trace Event Documentation

### Pool-Level Events (from `ProviderPool`)

| Event | Format | Description |
|-------|--------|-------------|
| `KeySelected` | `KeySelected:{fingerprint}` | A key was selected from the pool for a request |
| `KeySuspended` | `KeySuspended:{fingerprint}` | A key was suspended due to quota exhaustion |
| `KeyRecovered` | `KeyRecovered:{fingerprint}` | A previously suspended key was recovered (retry_after elapsed) |
| `QuotaExceeded` | `QuotaExceeded:{fingerprint}` | A key hit a quota limit (429 error) |

### Manager-Level Events (from `ProviderManager`)

| Event | Format | Description |
|-------|--------|-------------|
| `KeyRotated` | `KeyRotated:{old_key}->{new_key}` | Provider fell back from one key/provider to another |
| `FallbackActivated` | `FallbackActivated` | A fallback provider was activated |
| `ProviderUnavailable` | `ProviderUnavailable` | All providers exhausted, no more fallbacks |
| `ProviderRequestStarted` | `ProviderRequestStarted` | An LLM request was initiated |
| `ProviderRequestSucceeded` | `ProviderRequestSucceeded` | An LLM request completed successfully |
| `ProviderRequestFailed` | `ProviderRequestFailed` | An LLM request failed |
| `ProviderRecovered` | `ProviderRecovered` | A provider recovered after retries |
| `QuotaExceeded` | `QuotaExceeded` | Quota exceeded at provider manager level |
| `RetryStarted` | `RetryStarted` | A retry attempt is beginning |
| `RetryCompleted` | `RetryCompleted` | A retry backoff period completed |

---

## Status Command Behavior

### Before (Broken)
```
Current Cycle: {count of files in docs/revisions/}    ← INFERRED, INCORRECT
Open Blocking Issues: {from review_metrics.json}      ← INFERRED
Latest Decision: {parsed from last decision file}     ← INFERRED
```

### After (Fixed)
```
Current Cycle: {state.json.current_cycle}              ← AUTHORITATIVE
Open Blocking Issues: {state.json.open_blocking_issues} ← AUTHORITATIVE
Latest Decision: {state.json.latest_decision}          ← AUTHORITATIVE
```

The status command still reads provider health, model info, runtime, and convergence data from `ObservabilityManager` — those are operational metrics that don't need authoritative state persistence.

---

## Test Matrix

| # | Test Name | Category | Scenario |
|---|-----------|----------|----------|
| 1 | `test_initialize_creates_full_state` | State Model | Init creates all required fields |
| 2 | `test_update_cycle` | State Model | Cycle update persists correctly |
| 3 | `test_update_decision` | State Model | Decision update persists correctly |
| 4 | `test_update_issues` | State Model | Issue counts update correctly |
| 5 | `test_update_provider_summary` | State Model | Provider summary updates |
| 6 | `test_get_current_cycle` | State Model | Getter returns correct cycle |
| 7 | `test_get_latest_decision` | State Model | Getter returns correct decision |
| 8 | `test_transition_preserves_extended_fields` | State Model | Transitions don't erase new fields |
| 9 | `test_last_updated_timestamp_changes` | State Model | Timestamp updates on save |
| 10 | `test_approve_on_cycle_1` | Cycle Tracking | Approve first cycle → cycle=1 |
| 11 | `test_approve_on_cycle_2` | Cycle Tracking | Reject→Approve → cycle=2 |
| 12 | `test_approve_on_cycle_3` | Cycle Tracking | Reject→Reject→Approve → cycle=3 |
| 13 | `test_escalation_after_max_cycles` | Cycle Tracking | 3 rejects → escalation, cycle=3 |
| 14 | `test_resume_workflow_preserves_cycle` | Cycle Tracking | Cycle survives controller reload |
| 15 | `test_status_reads_authoritative_cycle` | Status Command | Status reads cycle from state.json |
| 16 | `test_status_reads_authoritative_decision` | Status Command | Status reads decision from state.json |
| 17 | `test_reason_never_unknown` | Decision Provenance | No decision has reason "Unknown" |
| 18 | `test_decision_contains_required_fields` | Decision Provenance | All provenance fields present |
| 19 | `test_extract_decision_reason_with_summary` | Decision Provenance | Extracts from # Summary |
| 20 | `test_extract_decision_reason_fallback_synthesis` | Decision Provenance | Synthesizes from metrics |
| 21 | `test_extract_decision_reason_approve` | Decision Provenance | Approve reason mentions resolution |
| 22 | `test_key_selected_event` | Provider Trace | KeySelected logged on key pick |
| 23 | `test_key_suspended_and_quota_exceeded_events` | Provider Trace | Quota events logged on failure |
| 24 | `test_key_recovered_event` | Provider Trace | Recovery event logged |
| 25 | `test_key_rotated_event_on_fallback` | Provider Trace | KeyRotated on provider fallback |
| 26 | `test_provider_unavailable_event` | Provider Trace | ProviderUnavailable when all fail |
| 27 | `test_full_trace_sequence` | Provider Trace | Complete event sequence |
| 28 | `test_state_survives_reload` | Persistence | State recoverable after reload |
| 29 | `test_state_json_schema_completeness` | Persistence | All required keys present |
| 30 | `test_cycle_not_inferred_from_revision_files` | Regression | Extra files don't affect cycle |
| 31 | `test_decision_reason_not_unknown_after_review` | Regression | Reason never "Unknown" in files |
| 32 | `test_status_cycle_matches_last_executed_review` | Regression | Cycle reflects actual execution |

---

## Files Modified

| File | Change |
|------|--------|
| `src/karsa/workflow/controller.py` | Extended state model with `current_cycle`, `latest_decision`, issue counts, timestamp, provider summary. Added update/get methods. |
| `src/karsa/workflow/engine.py` | Added `_extract_decision_reason()`. Engine now updates authoritative state (cycle, decision, issues) during review loop. |
| `src/karsa/cli.py` | Status command reads cycle, decision, and issues from `state.json` instead of inferring from file counts / observability. Pool constructors now pass `trace_fn`. |
| `src/karsa/llm/pool.py` | Added `trace_fn` callback. Emits `KeySelected`, `KeySuspended`, `KeyRecovered`, `QuotaExceeded` events. |
| `src/karsa/llm/provider.py` | Added `KeyRotated`, `ProviderUnavailable`, `QuotaExceeded` trace events. Improved fallback logging. |
| `src/karsa/llm/client.py` | `GeminiClient` wires pool `trace_fn` to observability manager. |
| `tests/test_state_tracking.py` | New comprehensive test suite (32 tests). |
| `docs/WORKFLOW_STATE_AUDIT.md` | This audit document. |
