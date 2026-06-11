# Benchmark Execution Blueprint

## 1. Overview

This blueprint defines the execution lifecycle and structural architecture of the Karsa Benchmark Harness. It guarantees that any comparative testing between Karsa and direct CLI baselines is rigorous, deterministic, and highly reproducible.

## 2. Benchmark Runner Architecture

### 2.1. Core Components
- **`BenchmarkHarness`**: The master orchestrator. Reads benchmark definitions, initializes workspaces, and coordinates test execution.
- **`ExecutionSandbox`**: A strict isolation layer. Every run (baseline or Karsa) occurs inside an ephemeral Git worktree or cloned directory to prevent cross-contamination.
- **`TestEvaluator`**: The post-execution judge. Responsible for parsing diffs, running hidden test suites, and running static analysis to derive the Quality Score.
- **`TelemetryAggregator`**: Intercepts the `ObservabilityManager` output to lock in cost, token counts, and execution duration per run.

### 2.2. Baseline Definitions
To ensure an apples-to-apples comparison, baselines must represent realistic alternative paths a user might take:
- **`Baseline-ZeroShot`**: A single raw LLM call with the task prompt and all relevant files concatenated into the prompt. No iteration, no tests.
- **`Baseline-AiderSim`**: Simulates a standard CLI coding assistant. Allows for 1 immediate revision if the user (simulated) says "this failed to compile."
- **`Karsa-Standard`**: Full autonomous multi-agent loop with Reviewer and iterative feedback enabled.

## 3. Benchmark Execution Lifecycle

The lifecycle guarantees identical starting conditions for every runner.

1. **Initialization (`PREPARE`)**:
   - The Harness reads the Benchmark Scenario (e.g., `scenario_001_bug_fix.yaml`).
   - Resolves the target repository and the exact Git SHA required for the starting state.
2. **Isolation (`SANDBOX`)**:
   - The Harness spins up two isolated, ephemeral workspaces: one for Baseline, one for Karsa.
   - Clears any existing `.karsa/executions` telemetry inside the sandboxes.
3. **Execution (`RUN`)**:
   - Dispatches the identical task prompt to both executors concurrently or sequentially.
   - Wait for completion or a predefined timeout (e.g., 5 minutes).
4. **Evaluation (`JUDGE`)**:
   - The `TestEvaluator` kicks in. It compiles the code, runs the specific target unit tests, and captures linters/SonarQube results.
5. **Telemetry Extraction (`CAPTURE`)**:
   - The `TelemetryAggregator` extracts cost, tokens, duration, and prompt growth metrics from both sandboxes.
6. **Teardown (`CLEANUP`)**:
   - Ephemeral workspaces are destroyed. Data is merged into the global `benchmark_registry.json`.

## 4. Reproducibility Guarantees

To prevent benchmark flakiness and ensure scientific validity:
- **Locked Dependency Versions**: Benchmark environments run in pinned container images or virtual environments.
- **Deterministic API Routing**: The LLM client overrides temperature to `0.0` (or the lowest possible) during benchmark mode.
- **Fixed Model Versions**: Benchmarks specify explicit model versions (e.g., `gemini-2.5-flash-001`), never rolling aliases like `latest`.
- **Statelessness**: The `.karsa/` observability cache is wiped at the start of `SANDBOX` phase. Agents cannot "remember" previous runs.

## 5. Cost Per Success Methodology

Raw cost is misleading if the baseline completes cheaply but produces broken code. We measure **Cost Per Success**:
- If a run passes 100% of quality gates, `Cost_Per_Success = Total_Execution_Cost`.
- If a run fails, the run is flagged as `FAILED_TO_CONVERGE`. The cost is recorded, but the `Cost_Per_Success` is marked as `INFINITE` (or explicitly nullified in successful aggregation averages).
- If the `Baseline-AiderSim` requires 3 simulated "try again" prompts to reach success, the `Cost_Per_Success` is the aggregate sum of all 3 attempts.

## 6. Quality Scoring Model

The `TestEvaluator` grades output on a strict scale (0 to 100):
- **Compilation/Syntax (30 pts)**: Does the code parse and build? (Binary: 0 or 30).
- **Test Pass Rate (40 pts)**: Percentage of hidden unit tests passing. (e.g., 2/4 passed = 20 pts).
- **Static Analysis / Debt (20 pts)**: No new SonarQube blockers, smells, or regressions. (-5 pts per new issue).
- **Diff Parsability (10 pts)**: Did the agent follow strict artifact patching rules, or did it hallucinate formatting?

A run must score a **100** to be considered a "Success" for the `Cost_Per_Success` metric.

## 7. Report Generation Design

The Harness automatically synthesizes the extracted telemetry into a standard `BENCHMARK_REPORT.md` artifact.

### Structure of the Report:
1. **Executive Summary**: Headline percentage wins/losses (e.g., "Karsa is 40% cheaper and 2x more reliable than ZeroShot CLI").
2. **Detailed Matrix**: A table comparing Karsa vs. Baselines across the Quality Score, Cost ($), Time (s), and Tokens.
3. **Failure Analysis**: If Karsa or the Baseline failed, an automated extraction of the exact error (e.g., "Baseline hallucinated missing variable `user_id`").
4. **Prompt Growth Graph**: A text-based or Mermaid chart showing how Karsa's context size evolved vs. the Baseline's context size. 

This report will be attached to Pull Requests affecting Karsa's agent logic, allowing developers to quantitatively measure if a new prompt change degraded platform intelligence.
