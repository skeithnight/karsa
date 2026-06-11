# Failure Taxonomy

## 1. Overview

Karsa assumes that failure in autonomous systems is the default state. The Governance Engine relies on a standardized taxonomy to determine whether an error is a temporary network glitch or a catastrophic policy violation requiring immediate abortion.

## 2. Taxonomy Definitions

### 2.1. `BudgetExceeded`
* **Description**: The rolling total USD cost of the current workflow has breached the `max_workflow_cost_usd` defined in the governance policy.
* **Severity**: `CRITICAL`
* **Retryability**: `FALSE`
* **Recovery Strategy**: None. The workflow must be instantly aborted to prevent further financial drain.
* **Governance Action**: Transition to `ABORTED`. Alert human operator.
* **Observability Requirements**: Must log the exact total cost vs the maximum limit, and the agent that triggered the final breach.

### 2.2. `TokenLimitExceeded`
* **Description**: A single execution has requested a context window larger than the `max_tokens_per_execution` limit.
* **Severity**: `HIGH`
* **Retryability**: `FALSE` (Unless a summarization agent is injected).
* **Recovery Strategy**: Abort the execution. If Prompt Summarization (Phase I) is active, attempt to compress history and retry. Otherwise, terminate.
* **Governance Action**: Transition to `ABORTED` (or intercept via Summarization).
* **Observability Requirements**: Log exact `context_tokens` requested vs the limit.

### 2.3. `ReviewCycleExceeded`
* **Description**: The workflow has bounced between `REVIEW` and `REVISE` more times than the `max_review_cycles` threshold, indicating an infinite loop.
* **Severity**: `HIGH`
* **Retryability**: `FALSE`
* **Recovery Strategy**: Abort. Human intervention required to break the loop.
* **Governance Action**: Transition to `ABORTED`.
* **Observability Requirements**: Dump the review history of the final 2 cycles to show the cyclic hallucination.

### 2.4. `ProviderUnavailable`
* **Description**: The LLM API endpoint returned a 50x error or timed out entirely.
* **Severity**: `MODERATE`
* **Retryability**: `TRUE`
* **Recovery Strategy**: Utilize `ProviderManager` retry logic with exponential backoff.
* **Governance Action**: Increment `total_retries`. If all retries fail, transition to `FAILED`.
* **Observability Requirements**: Log exact HTTP status and latency.

### 2.5. `ProviderQuotaExceeded`
* **Description**: The LLM API endpoint returned a 429 Quota Exceeded error.
* **Severity**: `MODERATE`
* **Retryability**: `TRUE`
* **Recovery Strategy**: Key Rotation. Suspend the active key, fallback to the next available key in the `ProviderPool`.
* **Governance Action**: If pool is empty, transition to `FAILED`.
* **Observability Requirements**: Log `KeyRotated` and the fingerprints involved.

### 2.6. `PatchApplyFailed`
* **Description**: The agent generated a diff/patch, but the format was malformed or the target file had drifted, causing the applicator to reject it.
* **Severity**: `HIGH`
* **Retryability**: `TRUE` (Limited).
* **Recovery Strategy**: Ask the agent to regenerate the entire file (fallback) or strictly instruct it to fix the malformed hunk. Max 1 retry.
* **Governance Action**: If retry fails, transition to `FAILED`.
* **Observability Requirements**: Log the raw malformed patch text.

### 2.7. `VerificationFailed`
* **Description**: The generated code failed to compile, failed unit tests, or introduced SonarQube blockers.
* **Severity**: `LOW` (This is expected behavior in an iterative loop).
* **Retryability**: `TRUE`.
* **Recovery Strategy**: Push the exact error logs back into the `REVIEW` state and demand a `REVISE`.
* **Governance Action**: Increment the cycle counter. Check against `ReviewCycleExceeded`.
* **Observability Requirements**: Log `cost_per_issue_resolved` mapping.

### 2.8. `HumanRejected`
* **Description**: The founder explicitly clicked "Reject" or provided negative feedback that cannot be autonomously resolved.
* **Severity**: `HIGH`
* **Retryability**: `FALSE` (By default, requires new `IDEA`).
* **Recovery Strategy**: Halt. Await human to supply a new `IDEA` or manual intervention.
* **Governance Action**: Transition to `FAILED`.
* **Observability Requirements**: Record human rationale to improve future instructions.
