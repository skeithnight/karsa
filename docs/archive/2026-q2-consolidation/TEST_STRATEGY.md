# Test Strategy

## 1. Overview

Testing the Cost & Token Observability subsystem requires precision. We are measuring financial attribution, which means rounding errors, incorrect provider tracking, and unhandled exceptions can lead to severe misrepresentations of platform cost.

## 2. Test Domains

### 2.1. Provider & Key Attribution
**Objective**: Ensure that the exact provider and API key used for an execution are securely and accurately logged.
- **Test Scenarios**:
  - `test_attribution_default_flow`: Verify single-provider execution logs the correct `provider` and `key_fingerprint`.
  - `test_attribution_key_rotation`: Force a `429 Quota Exceeded` on Key A, forcing fallback to Key B. Verify the `ObservabilityManager` correctly logs the execution against Key B's fingerprint.
  - `test_attribution_provider_fallback`: Force a total failure of Provider X, falling back to Provider Y. Verify the cost is attributed solely to Provider Y and its respective key.

### 2.2. Token Collection
**Objective**: Guarantee that token counting accurately reflects the prompt and response size.
- **Test Scenarios**:
  - `test_tokenizer_exact_match`: Pass a known prompt and assert the `input_tokens` matches the exact value returned by the provider SDK.
  - `test_tokenizer_fallback_heuristic`: Force the SDK tokenizer to fail (e.g., mock network timeout) and verify the system gracefully falls back to the `ESTIMATED` character-based ratio, avoiding workflow failure.
  - `test_zero_token_handling`: Handle edge cases where output is empty or blocked due to safety filters, ensuring `output_tokens` safely records `0`.

### 2.3. Cost Calculation
**Objective**: Validate the Cost Attribution Engine's arithmetic and pricing registry lookups.
- **Test Scenarios**:
  - `test_cost_calculation_standard`: Given 1M input tokens and $0.50 pricing, assert cost is exactly $0.50.
  - `test_cost_calculation_missing_pricing`: Provide a non-existent model name. Verify cost is `0.0` and `pricing_status` is `MISSING`.
  - `test_cost_calculation_local_model`: Provide a configured local model. Verify cost is `$0.00` and `pricing_status` is `CALCULATED`.

### 2.4. Workflow & Agent Aggregation
**Objective**: Ensure rolling counters do not drift over time.
- **Test Scenarios**:
  - `test_workflow_cost_aggregation`: Fire 10 parallel mock executions for the same workflow. Verify the workflow's total cost equals the exact sum of individual execution costs.
  - `test_agent_cost_aggregation`: Execute across multiple agents (`Reviewer`, `Coder`). Verify `AgentMetrics` accurately splits the cost.

### 2.5. Migration & Compatibility
**Objective**: Ensure backward compatibility with existing Karsa artifacts.
- **Test Scenarios**:
  - `test_legacy_execution_parse`: Ensure the new CLI analytics commands do not crash when reading old `metadata.json` files that lack `cost` and `tokens` fields.

## 3. Execution Environment
- Cost calculation tests must run offline using a mocked pricing registry.
- Tokenizer tests should use injected, deterministic mocks to prevent flake caused by dynamic model behavior.
