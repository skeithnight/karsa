---
status: active
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: Never (Immutable)
---

# Sprint 2 Evidence Package

## 1. FSM Evidence

### Valid Transition Example
The FSM correctly processes allowed transitions (e.g., `IDEA` -> `DRAFT`).
```text
Valid transition: IDEA -> DRAFT
```

### Invalid Transition Example
The FSM throws a strict exception when attempting to jump states (e.g., `IDEA` -> `APPROVED`).
```text
Invalid transition exception: InvalidTransitionError - Cannot transition from IDEA to APPROVED
```

## 2. Snapshot Evidence

The initial `snapshot.json` captures the baseline state of a workflow.

```json
{
  "workflow_id": "w_demo",
  "state": "IDEA",
  "data": {},
  "schema_version": 1,
  "last_sequence_number": 1
}
```
*Note: `schema_version` and `workflow_id` and `state` are explicitly captured.*

## 3. Event Journal Evidence

As transitions occur, the `events.jsonl` continuously logs incremental events with monotonically increasing sequence numbers.

```jsonl
{"event_type": "StateTransitionedEvent", "payload": {"workflow_id": "w_demo", "previous_state": "IDEA", "new_state": "DRAFT", "reason": "", "sequence_number": 2}}
{"event_type": "StateTransitionedEvent", "payload": {"workflow_id": "w_demo", "previous_state": "DRAFT", "new_state": "REVIEW", "reason": "", "sequence_number": 3}}
```

## 4. Recovery Evidence

**Step-by-Step Replay Process:**
1. A crash occurs. The `RecoveryEngine` reads `snapshot.json`. The snapshot's `last_sequence_number` is `1` (State: `IDEA`).
2. The `RecoveryEngine` scans `events.jsonl` and finds events with sequence numbers `2` and `3`.
3. It replays these events over the snapshot sequentially. Event 2 transitions it to `DRAFT`. Event 3 transitions it to `REVIEW`.
4. The final recovered state perfectly matches the moment before the crash.

```text
Recovered state: REVIEW
Recovered sequence: 3
```

## 5. Lock Evidence

The `WorkflowLockManager` prevents overlapping executions.

### `lock.json` Example
```json
{
  "workflow_id": "w_demo",
  "process_id": "proc1",
  "acquired_at": 1781189948.423528,
  "expires_at": 1781189949.423528
}
```

### Lock Reacquisition and TTL Expiration
If a second process attempts to acquire the lock before `expires_at`, it throws an exception:
```text
Lock block exception: Workflow w_demo is currently locked by process proc1
```
After 1 second has elapsed (the TTL), the second process safely overwrites the lock:
```text
Sleeping 2 seconds for TTL expiration...
Lock re-acquired after TTL.
```

## 6. Test Evidence

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/dwiki.nugraha/dwikicode/karsa
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_fsm_durability.py::test_fsm_valid_transitions PASSED          [ 20%]
tests/test_fsm_durability.py::test_fsm_invalid_transitions PASSED        [ 40%]
tests/test_fsm_durability.py::test_workflow_lock PASSED                  [ 60%]
tests/test_fsm_durability.py::test_hybrid_persistence_and_recovery PASSED [ 80%]
tests/test_fsm_durability.py::test_recovery_from_events_only PASSED      [100%]

============================== 5 passed in 0.24s ===============================
```

## 7. File Tree Evidence

```text
src/karsa/
├── domain/
│   ├── events.py
│   ├── models.py
│   └── persistence.py
└── workflow/
    ├── fsm.py
    ├── lock.py
    └── recovery.py
```

## 8. Known Gaps
- **Journal Compaction**: `EventJournalRepository` appends indefinitely without compacting into the snapshot file.
- **In-Memory Thread Safety**: The `WorkflowLockManager` guarantees filesystem exclusion but does not natively prevent multiple threads *in the same process* from colliding.
- **Enum Deserialization**: Custom serialization logic is currently used for Enums. A standardized Marshmallow or Pydantic serialization layer would be more robust.