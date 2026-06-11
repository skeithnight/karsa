# Data Model Design

## 1. Schema Definitions

### 1.1. ExecutionMetrics
Records the telemetry and cost of a single LLM request/response cycle.
- **`execution_id`** (`string`): Unique identifier (UUID).
- **`workflow_id`** (`string`): ID of the parent workflow.
- **`review_cycle_id`** (`string`): ID of the parent review cycle (models the Workflow -> Review Cycle -> Agent -> Execution hierarchy).
- **`agent_name`** (`string`): Name of the agent (e.g., `Reviewer`).
- **`provider`** (`string`): The actual provider used (e.g., `gemini`, `openai`).
- **`model`** (`string`): The specific model used (e.g., `gemini-2.5-flash`).
- **`key_fingerprint`** (`string`): Fingerprint of the API key utilized.
- **`status`** (`string`): `SUCCESS` or `ERROR`.
- **`duration_ms`** (`integer`): Execution time in milliseconds.
- **`timestamp`** (`string`): ISO 8601 timestamp.
- **`tokens`** (`TokenBreakdown`): Total token utilization.
- **`prompt_analytics`** (`PromptGrowthAnalytics`): Detailed token breakdown of prompt composition.
- **`cost`** (`CostBreakdown`): Cost utilization.

### 1.2. TokenBreakdown
High-level token counting logic.
- **`input_tokens`** (`integer`): Total tokens processed in the prompt.
- **`output_tokens`** (`integer`): Total tokens generated in the response.
- **`total_tokens`** (`integer`): Sum of input and output.
- **`accuracy`** (`string`): `EXACT` (via tokenizer) or `ESTIMATED` (heuristic).

### 1.3. PromptGrowthAnalytics
First-class support to explain exactly *why* a prompt became large. Measurements in exact tokens.
- **`context_tokens`** (`integer`): Base system instructions and project-level context.
- **`artifact_tokens`** (`integer`): Tokens consumed by the codebase or documentation artifacts injected.
- **`issue_tokens`** (`integer`): Tokens consumed by existing/new issue definitions.
- **`review_tokens`** (`integer`): Tokens consumed by review feedback and rulesets.
- **`history_tokens`** (`integer`): Tokens consumed by conversation/turn history.
- **`compression_ratio`** (`float`): Indicates savings if Context Compression/Diff strategies were applied to this prompt.

### 1.4. CostBreakdown
Monetary cost values in USD.
- **`input_cost`** (`float`): Cost for input tokens.
- **`output_cost`** (`float`): Cost for output tokens.
- **`total_cost`** (`float`): Sum of input and output costs.
- **`pricing_status`** (`string`): `CALCULATED` or `MISSING`.

### 1.5. WorkflowMetrics
Aggregated costs at the top level of the hierarchy.
- **`workflow_id`** (`string`): The workflow identifier.
- **`total_executions`** (`integer`): Total number of LLM calls made across all cycles.
- **`total_cost`** (`float`): Rolling sum of all execution costs.
- **`total_tokens`** (`integer`): Rolling sum of all tokens used.
- **`duration_ms`** (`integer`): Total workflow duration.

### 1.6. ReviewCycleMetrics
Aggregated costs for a single iterative loop within a workflow.
- **`workflow_id`** (`string`): Parent workflow.
- **`review_cycle_id`** (`string`): The specific iteration cycle ID.
- **`total_cost`** (`float`): Cost consumed in this specific review cycle.
- **`total_tokens`** (`integer`): Tokens consumed in this specific review cycle.

### 1.7. AgentMetrics
Aggregated historical cost per agent persona across cycles.
- **`agent_name`** (`string`): The persona name.
- **`total_executions`** (`integer`): All-time executions.
- **`total_cost`** (`float`): All-time cost.
- **`average_cost_per_execution`** (`float`): `total_cost / total_executions`.
- **`average_prompt_size`** (`integer`): Average input tokens per execution.

### 1.8. ProviderMetrics
Financial and utilization tracking for API keys and providers.
- **`provider_name`** (`string`): The provider (e.g., `anthropic`).
- **`key_fingerprint`** (`string`): The specific API key fingerprint.
- **`total_cost`** (`float`): Total money spent on this key.
- **`total_tokens`** (`integer`): Total tokens processed.
- **`quota_failures`** (`integer`): 429 error counts.

### 1.9. OptimizationMetrics
Metrics designed to drive future optimization decisions quantitatively. Maintained at the workflow or global level.
- **`cost_per_issue_found`** (`float`): Reviewer cost divided by issues raised.
- **`cost_per_issue_resolved`** (`float`): Coder/Fix cost divided by issues resolved.
- **`cost_per_review_cycle`** (`float`): Average cost to run a full review loop.
- **`cost_per_approval`** (`float`): Total cost spent to reach a successful approval state.
- **`cost_per_artifact_generated`** (`float`): Average cost to author a new artifact/file.

## 2. Ownership and Lifecycle

- **Updates**: Performed synchronously during the LLM execution lifecycle. `ExecutionMetrics` are immutable once written.
- **Aggregations**: `WorkflowMetrics`, `ReviewCycleMetrics`, `AgentMetrics`, and `OptimizationMetrics` are updated incrementally via event callbacks immediately post-execution.
