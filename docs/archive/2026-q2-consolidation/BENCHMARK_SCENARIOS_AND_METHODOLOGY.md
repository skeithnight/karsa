# Benchmark Scenarios, Methodology & Comparison Framework

## 1. Experiment Methodology

To definitively prove Karsa's superiority, experiments must be statistically significant, deterministic, and isolated.

### 1.1. Controlled Variables
- **Model**: Both Baseline and Karsa MUST use the exact same underlying LLM (e.g., `gemini-2.5-flash`).
- **Starting State**: Both systems start from the identical git commit.
- **Context Injection**: The Baseline receives all relevant files dumped into the prompt (simulating a developer using `<file>` tags). Karsa uses its native discovery and retrieval mechanisms.

### 1.2. The Null Hypothesis
*Karsa is equal to or worse than Direct CLI usage in Cost, Speed, and Quality.*
Our objective is to reject the null hypothesis by proving statistically significant improvements across our success metrics.

## 2. Benchmark Scenarios

Scenarios range from trivial (where baseline might win on speed) to complex (where Karsa's multi-agent review loop proves its worth).

### Scenario 1: The Single-File Bug Fix (Trivial)
- **Task**: Fix an off-by-one error in a specific utility function.
- **Hypothesis**: Baseline will be faster and cheaper. Karsa will be equal in quality but slightly more expensive due to Reviewer overhead.

### Scenario 2: The Multi-File Refactor (Moderate)
- **Task**: Rename a core data model and update all 15 references across 4 different directories.
- **Hypothesis**: Baseline will fail to find all references or hallucinate file paths. Karsa will succeed in 2 review cycles, proving significantly higher quality, though cost may be equal.

### Scenario 3: The Ambiguous Feature Implementation (Complex)
- **Task**: "Implement a rate-limiter for the API" (No implementation details provided).
- **Hypothesis**: Baseline will write a naive, untested script. Karsa will query the user/context, write tests, implement the logic, and pass quality gates. Karsa drastically outperforms Baseline in Quality and "Cost to Success".

### Scenario 4: The SonarQube Debt Cleanse (Forensic)
- **Task**: Fix 5 specific Code Smells and 1 Vulnerability in an existing legacy class.
- **Hypothesis**: Baseline will break existing tests while fixing smells. Karsa will fix smells and ensure tests pass, proving higher reliability.

## 3. Success Metrics (The Comparison Framework)

The framework evaluates the `Karsa / Baseline` ratio across three primary pillars:

### 3.1. Financial Efficiency (Is it Cheaper?)
- **`cost_to_success`**: The total cost spent to reach a passing state. (If Baseline fails, its cost to success is technically infinite, but we cap it at the cost of the failed attempt).
- **`token_efficiency_ratio`**: `Baseline_Tokens / Karsa_Tokens`. A score > 1.0 means Karsa used fewer tokens.

### 3.2. Execution Velocity (Is it Faster?)
- **`time_to_success_ms`**: Wall-clock time to achieve 100% test pass rate.
- **`human_intervention_count`**: How many times a human had to clarify or fix the output. (Baseline often requires 3+ human follow-ups; Karsa aims for 0).

### 3.3. Output Quality (Is it Better?)
- **`first_pass_success_rate`**: Does the code compile and pass tests on the very first try?
- **`cyclomatic_complexity_delta`**: Did the agent write spaghetti code?
- **`bug_introduction_rate`**: Did the change break an unrelated, previously passing test?

## 4. The Final Evaluation Matrix

A successful benchmark run generates a comparative matrix:

| Metric | Direct CLI (Baseline) | Karsa | Delta (%) | Winner |
|--------|-----------------------|-------|-----------|--------|
| **Total USD Cost** | $0.15 | $0.08 | -46% | Karsa |
| **Wall Clock Time** | 12s | 45s | +275% | Baseline |
| **Test Pass Rate** | 40% | 100% | +150% | Karsa |
| **Bugs Introduced** | 2 | 0 | -100% | Karsa |
| **Cost to Success** | $0.45 (3 tries) | $0.08 (1 try)| -82% | Karsa |

**Conclusion Framework**: If Karsa proves cheaper and higher quality, a slight degradation in raw wall-clock speed is considered an acceptable trade-off for autonomous reliability.
