# Cost & Token Observability Audit

## 1. Executive Summary

The current implementation of Karsa features foundational observability, including execution tracking, provider polling, and timeline generation. However, it lacks any native support for token counting, cost estimation, and granular cost attribution. This audit evaluates the current state and identifies key architectural gaps that prevent Karsa from functioning as an enterprise-grade, cost-aware multi-agent platform.

## 2. Current State Analysis

### 2.1. Observability Manager (`src/karsa/observability/manager.py`)
- **Execution Tracking**: The `record_execution` method captures `input_chars` and `output_chars` by counting string lengths, not actual tokens. 
- **Missing Token/Cost Data**: No tracking of input tokens, output tokens, or estimated cost in USD.
- **Attribution Breakage**: The `provider` field is hardcoded to `"karsa-llm"` instead of capturing the actual underlying provider (e.g., `gemini`, `openai`). The `key_fingerprint` parameter defaults to `"none"` and is not effectively populated during standard executions.

### 2.2. Provider Pool & Registry (`src/karsa/llm/pool.py`)
- **Key Tracking**: The `ProviderPool` tracks key status (`ACTIVE`/`SUSPENDED`), `total_requests`, and `quota_failures`.
- **Missing Resource Accounting**: The registry lacks any mechanism to accumulate token usage or cost per key. It only tracks raw request counts, which is insufficient for cost distribution analysis.

### 2.3. LLM Client & Provider Manager (`src/karsa/llm/client.py`, `src/karsa/llm/provider.py`)
- **Execution Logging Gap**: In `LLMClient.generate_with_obs` and `ProviderManager.generate_with_obs`, the call to `self.obs.record_execution` does not pass the `key_fingerprint`. As a result, every execution defaults to `key_fingerprint: "none"`.
- **Model Agnosticism Issues**: While the system attempts to be model-agnostic, the tight coupling of `GeminiClient` with `ProviderPool` (which assumes API keys) and the lack of a standardized token counting interface across different providers hinders future expansion to models like OpenAI or Anthropic which use different tokenizers (e.g., `tiktoken`).

### 2.4. Workflow & Review Engine
- **No Cost Aggregation**: Workflows and review cycles span multiple executions, but there is no mechanism to aggregate cost or token usage at the workflow or review cycle level. 
- **No Agent-level Budgets**: The system cannot answer which agent (e.g., `Reviewer`, `Coder`) is the most expensive or consumes the most context.

### 2.5. CLI Status Reporting
- The `get_status_info` method returns execution counts and runtimes but provides zero visibility into token consumption or accumulated costs. 

## 3. Identified Gaps

1. **Missing Data**: No exact token counts (input/output) or cost estimations.
2. **Incorrect Attribution**: `provider` is hardcoded; `key_fingerprint` is lost during execution logging.
3. **Architectural Gaps**: Lack of a `Tokenizer` interface to calculate accurate token counts prior to/after LLM calls. Lack of a pricing registry to map `model` -> `cost_per_1k_tokens`.
4. **Scalability Concerns**: Writing separate `metadata.json`, `request.txt`, and `response.txt` for every single execution without any rolling aggregations will lead to massive I/O overhead and complex analytics aggregation logic as workflows scale.

## 4. Recommendations

1. **Introduce Tokenizer Abstraction**: Create a tokenizer interface that providers implement to yield exact token counts.
2. **Fix Attribution Plumbing**: Ensure `ProviderManager` passes down the active `provider_name` and `key_fingerprint` to the `ObservabilityManager`.
3. **Implement Cost Engine**: Create a service that calculates cost dynamically based on the model, provider, and token counts.
4. **Aggregate Metrics**: Introduce rolling aggregations for Agent, Workflow, and Provider to answer cost questions in O(1) time without parsing thousands of `metadata.json` files.
