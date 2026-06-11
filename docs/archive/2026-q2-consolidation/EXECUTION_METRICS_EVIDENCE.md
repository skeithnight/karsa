# Execution Metrics Evidence

## Actual Execution Metrics (`metadata.json`)
*Note: The implementation merged ExecutionMetrics into `metadata.json` rather than creating a separate `execution_metrics.json` file as dictated by the architecture. This is logged as a gap.*

```json
{
  "execution_id": "0002",
  "agent_name": "Coder",
  "model": "gemini-2.5-flash",
  "key_fingerprint": "abc-123",
  "provider": "karsa-llm",
  "duration_ms": 1500,
  "timestamp": "2026-06-11T14:06:59.534+00:00",
  "started_at": "2026-06-11T14:06:59.534+00:00",
  "completed_at": "2026-06-11T14:06:59.534+00:00",
  "input_chars": 88,
  "output_chars": 20,
  "input_tokens": 22,
  "output_tokens": 5,
  "cost_usd": 0.00000315,
  "prompt_hash": "e674b20a02efccdb2c9438063717df3d4d42b9c51a1d9b3a32f6b86ce4ec2c4b",
  "status": "SUCCESS"
}
```

## Actual Workflow Metrics (`workflow_metrics.json`)
```json
{
  "workflow_id": "default",
  "total_executions": 1,
  "total_tokens": 27,
  "total_cost_usd": 0.00000315,
  "total_duration_ms": 1500,
  "status": "PENDING"
}
```

## Actual Agent Metrics (`agent_metrics.json`)
```json
{
  "Coder": {
    "agent_name": "Coder",
    "total_executions": 1,
    "total_tokens": 27,
    "total_cost_usd": 0.00000315
  }
}
```

## Actual Review Cycle Metrics (`review_cycle_metrics.json`)
```json
{}
```
*Note: The file is initialized but not populated because the `MetricsAggregator` lacks the logic to map an execution to a specific `review_cycle_id`.*
