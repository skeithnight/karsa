# Cost Observability Implementation Plan

## Phase 1: Observability Correctness & Forensic Preservation
**Scope**: Fix the core attribution plumbing so that the active provider and key fingerprint correctly cascade down to the observability logs. Update the execution logger to append `execution_metrics.json` without overwriting the existing `request.txt` and `response.txt` diagnostic files.
**Dependencies**: Modifying `LLMClient.generate_with_obs`, `ProviderManager`, and `ObservabilityManager.record_execution`.
**Risks**: Minor risk of breaking existing tests that mock the client and do not expect new parameters.
**Acceptance Criteria**: 
- `metadata.json` reflects the active `provider` (e.g., `gemini`).
- The exact `key_fingerprint` used for the request is saved.
- `.karsa/executions/<execution_id>/` retains all raw text logs alongside the new JSON metrics.

## Phase 2: Token Accounting & Prompt Growth Analytics
**Scope**: Introduce the `Tokenizer` abstraction. Implement Prompt Growth Analytics to identify how much of the prompt is consumed by `artifact_tokens`, `issue_tokens`, `review_tokens`, and `history_tokens`.
**Dependencies**: Phase 1. Integration with provider SDK token APIs. Parsing logic to isolate prompt sections.
**Risks**: Accurately isolating prompt sections for tokenization may require standardizing the prompt building logic across all agents.
**Acceptance Criteria**:
- `ExecutionMetrics` logs exact `input_tokens` and `output_tokens`.
- The system correctly outputs the `PromptGrowthAnalytics` breakdown.
- Token logging functions seamlessly during mock/testing execution.

## Phase 3: Cost Attribution & Hierarchy Aggregation
**Scope**: Implement the Pricing Registry, Cost Attribution Engine, and the `Workflow -> Review Cycle -> Agent -> Execution` aggregation model.
**Dependencies**: Phase 2.
**Risks**: Pricing changes over time. Hierarchy aggregation logic requires well-defined workflow and review cycle IDs passed to the client.
**Acceptance Criteria**:
- Executions include calculated USD cost.
- Provider Pool tracks total cost per `key_fingerprint`.
- `ReviewCycleMetrics` and `WorkflowMetrics` accurately roll up total execution costs.

## Phase 4: CLI Analytics & Optimization Metrics
**Scope**: Enhance Karsa CLI to surface cost, token data, and the new Optimization Readiness Metrics (`cost_per_issue_found`, `cost_per_approval`).
**Dependencies**: Phase 3. Requires integration with issue tracking and review states to trigger metric division.
**Risks**: Calculating optimization metrics dynamically requires accurate tracking of issue/resolution states alongside cost.
**Acceptance Criteria**:
- CLI `status` command displays total run cost.
- CLI provides a `cost-breakdown` command showing spend by Workflow, Review Cycle, Agent, and Provider.
- Optimization Metrics accurately report `cost_per_issue_resolved` and `cost_per_approval`.

## Phase 5: Future Optimization Readiness
**Scope**: Finalize the baseline measurement foundation. Prepare the telemetry so that when Artifact Diff Reviews or Review Delta Strategies are implemented, the `compression_ratio` and savings are immediately visible.
**Dependencies**: Phase 4.
**Acceptance Criteria**:
- The platform can export a quantitative "Cost & Growth Report" proving where token bloat originates, allowing engineers to confidently prioritize the next optimization roadmap item.
