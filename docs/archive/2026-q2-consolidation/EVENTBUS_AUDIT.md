# EventBus Audit

## Publish Flow
1. An event object (e.g., `ExecutionCompletedEvent`) is instantiated.
2. `EventBus().publish(event)` is invoked.
3. The EventBus uses Python's `dataclasses.asdict()` to serialize the payload to JSON.
4. The JSON is appended synchronously to `events.jsonl` via file I/O.
5. The EventBus iterates through the list of `handlers` registered in `_subscribers[event_type]`.
6. Each handler is executed synchronously on the main thread.

## Subscriber Flow
1. During `MetricsAggregator` initialization, it calls `EventBus().subscribe(ExecutionCompletedEvent, self.handle_execution_completed)`.
2. When the event is routed, the `handle_execution_completed` method reads the `workflow_metrics.json` and `agent_metrics.json` files, updates the dataclasses, and overwrites the JSON files.

## Exception Handling Behavior
**There is no exception handling.** 
If `json.dump()` fails due to a disk space error, or if `asdict()` fails due to an un-serializable type, the exception propagates unhandled up the stack, crashing the `ObservabilityManager.record_execution()` method and halting the workflow instantly. 

## Tests Covering Subscriber Failures
**None.** The test script (`test_sprint1.py`) only evaluates the happy path. There are no pytest cases or unit tests to verify if a failing subscriber prevents other subscribers from executing, or if it corrupts the `events.jsonl` append.
