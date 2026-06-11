# Benchmark & Cost Observability Architecture

## 1. Vision & Purpose

Karsa's core value proposition is that an autonomous, multi-agent workflow engine can produce code that is **cheaper, faster, and of higher quality** than a developer using a standard direct CLI/LLM chat interface (like Aider or raw ChatGPT). 

To prove this quantitatively, we must build a Benchmark Observability Foundation that runs identical tasks through both Karsa and a baseline "Direct CLI" framework, collecting identical telemetry for an apples-to-apples comparison.

## 2. Observability Architecture (Benchmark Extension)

The existing Cost Observability architecture will be extended to track "Experiment Runs".

### 2.1. The Benchmark Harness
- **Purpose**: A test runner that sets up isolated sandbox environments, checks out specific Git SHAs, and feeds the identical prompt to both the `BaselineExecutor` and the `KarsaExecutor`.
- **Component**: `BenchmarkHarness` (CLI orchestrator).
- **Isolation**: Each benchmark run creates an immutable snapshot of the `.karsa/executions` telemetry.

### 2.2. Baseline Executor Simulation
- **Purpose**: Simulates "Direct CLI" usage.
- **Behavior**: It takes the task and passes it zero-shot (or single-shot) to the LLM along with the codebase context, without any Reviewer agents, planning cycles, or iterative feedback loops.
- **Telemetry**: Records `total_cost`, `total_tokens`, `duration_ms`, and `diff_size` using the exact same `ObservabilityManager` used by Karsa, ensuring apples-to-apples metrics.

### 2.3. Benchmark Metrics Repository
- **Purpose**: A dedicated datastore for comparative results.
- **Storage**: `.karsa/benchmarks/benchmark_registry.json`
- **Data Model**:
  - `benchmark_id`: UUID
  - `scenario_id`: The ID of the specific test case.
  - `karsa_metrics`: The aggregated WorkflowMetrics from Karsa's run.
  - `baseline_metrics`: The aggregated ExecutionMetrics from the Baseline run.
  - `delta`: The calculated difference in Cost, Speed, and Quality.

## 3. Data Collection Model

For every benchmark execution, we collect the following quantitative metrics across both systems:

### 3.1. Cost & Token Data
- `input_tokens` / `output_tokens`
- `total_usd_cost`
- `prompt_growth_analytics` (To prove Karsa's context management is more efficient than a human pasting files repeatedly).

### 3.2. Speed & Execution Data
- `wall_clock_duration_ms`: Total time from prompt submission to final diff application.
- `llm_compute_time_ms`: Time spent waiting for API responses.

### 3.3. Quality & Output Data
- `diff_lines_added` / `diff_lines_removed`
- `static_analysis_errors`: Post-execution lint/type-checker errors.
- `tests_passed` / `tests_failed`: Run against a hidden suite.
- `convergence_cycles`: Number of iterations needed to reach success.

## 4. Automation & CI Integration
- The Benchmark Harness will run as a GitHub Action on every major release.
- It will automatically generate a `BENCHMARK_REPORT.md` artifact showing the exact % improvement or regression of Karsa versus the Direct CLI baseline.
