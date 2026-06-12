# Sprint 5 Plan

## Software Delivery Quality & Review Convergence

### 1. Capability Gap Analysis
**Current State (End of Sprint 4):**
- Infrastructure is fully built, tested, and frozen.
- Event sourcing, state transitions, failovers, and multi-file persistence work flawlessly.

**Capability Gaps:**
- **Product Engineer Prompt Deficiencies:** The prompt lacks defensive boundaries against hallucinated imports, lacks instructions on writing resilient test suites, and does not enforce strict standard library usage.
- **Review Agent Complacency:** The Review Agent currently issues "APPROVED" too easily or loops indefinitely because its prompt lacks explicit criteria for evaluating completeness.
- **Observability Void:** There is currently no standardized way to collect or export metrics regarding cycle iterations, review scores, or test-pass rates across multiple concurrent project generations.

### 2. Benchmark Strategy (Phase 1 Complete)
To prove Karsa can deliver actual working software without infinite looping or crashing, we will execute five diverse Benchmark Missions. We have introduced a lightweight `BenchmarkSuiteRunner` capable of aggregating metrics cleanly across multiple sandbox executions.
**Benchmark Scenarios:**
1. Duplicate File Finder CLI
2. Expense Tracker CLI
3. Todo REST API
4. Markdown Static Site Generator
5. CSV Data Analysis Utility

**Acceptance Criteria:** 4 out of 5 projects must reach the FSM `APPROVED` state and pass all generated Pytest scenarios.

### 3. Evaluation Framework & Metrics
We will introduce a lightweight metrics collection script (executed via CLI, not impacting core FSM infrastructure) to aggregate event logs. 
**Tracked Metrics:**
- `project_success_rate`
- `review_cycles_per_project`
- `approval_rate`
- `failed_generation_rate`
- `recovery_success_rate`
- `test_pass_rate`

### 4. Quality Improvement Plan
- **PE Prompt Enhancements:** Add strict constraints enforcing standard libraries, README generation, and defensive testing.
- **Review Prompt Enhancements:** Require explicit verification that every test case exercises edge cases, and enforce a rule to output REVISE if pytest fails.

### 5. Go / No-Go Recommendation
**Recommendation:** GO
**Justification:** The infrastructure from Sprint 4 is proven. Sprint 5's focus on benchmarking and prompt-tuning is the exact correct next step.