# Cost & Token Observability Architecture

## 1. Overview

The Cost & Token Observability subsystem transforms Karsa into a quantitatively measurable, cost-aware platform. It acts as the authoritative source for token usage, estimated costs, provider utilization, and granular workflow attribution.

## 2. Core Components

### 2.1. Token Usage Collector
- **Responsibilities**: Intercepts LLM requests/responses to calculate exact token usage and prompt composition.
- **Data Flow**: Sits between `LLMClient` and `ObservabilityManager`. Calls provider-specific tokenizers. Analyzes the prompt payload to separate and count `artifact_tokens`, `issue_tokens`, `review_tokens`, and `history_tokens` to provide Prompt Growth Analytics.

### 2.2. Cost Attribution Engine
- **Responsibilities**: Maps executed tokens to monetary cost using a dynamic pricing registry.
- **Data Flow**: Looks up current rates (e.g., cost per 1M input/output tokens) based on model identifier. Calculates exact costs in USD.

### 2.3. Execution Metrics Repository (Forensic Preservation)
- **Responsibilities**: Stores the lowest level of granularity: per-execution metrics, while completely preserving raw diagnostic artifacts.
- **Storage Model**: **Does not replace the current `executions/` directory structure.** Instead, it adds a structured `execution_metrics.json` inside the existing `.karsa/executions/<execution_id>/` directory. This preserves `request.txt` and `response.txt` for deep forensic debugging.
- **Data Stored**: Exact tokens, prompt growth analysis, cost, duration, and the full workflow hierarchy mapping.

### 2.4. Workflow Hierarchy & Aggregation Engine
- **Responsibilities**: Explicitly models and aggregates the cost across the hierarchy: **Workflow -> Review Cycle -> Agent -> Execution**.
- **Storage Model**: Maintains rolling counters in structural JSON files (`workflow_metrics.json`, `review_cycle_metrics.json`, `agent_metrics.json`) to provide O(1) reads for CLI analytics without reparsing thousands of historical executions.
- **Data Flow**: Listens to the `ExecutionMetricsRepository` via event callbacks to increment hierarchy totals dynamically.

### 2.5. Optimization Measurement Engine
- **Responsibilities**: Derives Optimization Readiness Metrics (`cost_per_issue_found`, `cost_per_issue_resolved`, etc.).
- **Data Flow**: Tracks state transitions (e.g., when an issue flips to RESOLVED or an approval is granted) and divides the aggregated cost consumed up to that point by the unit of work accomplished.

### 2.6. Cost Analytics Service
- **Responsibilities**: Exposes APIs and data views for the CLI to query cost health, prompt growth, and ROI metrics.

## 3. Future Cost Optimization Support

The architecture is explicitly designed so that future optimizations can be measured quantitatively. The `PromptGrowthAnalytics` (tracking `artifact_tokens`, `review_tokens`, etc.) serves as the baseline measurement tool.

When future strategies are implemented:
- **Artifact Diff Reviews & Patch-Based Revisions**: We will immediately measure the drop in `output_tokens` and `artifact_tokens` (since only diffs are transmitted) against the historical baseline.
- **Review Delta Strategies**: We will measure the drop in `review_tokens` and `context_tokens` for the Reviewer agent as it shifts to evaluating isolated diffs instead of full context.
- **Context Compression**: The `compression_ratio` metric will track the raw pre-compression tokens vs. post-compression tokens sent to the LLM, directly calculating dollars saved per execution.
