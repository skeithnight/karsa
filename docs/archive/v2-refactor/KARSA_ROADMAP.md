---
status: active
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: 2026-06-25
---

# Karsa Implementation Walkthrough & Roadmap

## 1. Current Platform Assessment

### What Karsa Can Currently Do
Based on the current repository artifacts, Karsa has successfully established the skeleton of an autonomous multi-agent workflow. 
- **Agent Orchestration**: Outlines transition between Product (Discovery), Engineering (Architecture/Execution), and Governance (Quality Review).
- **Provider Pooling**: Basic `ProviderManager` handles key rotation and naive fallback loops.
- **Execution Logging**: `ObservabilityManager` tracks raw execution IDs, agent names, models, and runtimes into `.karsa/executions`.

### What Karsa Cannot Do
- **Financial Measurement & Governance**: It cannot track tokens, map them to exact USD costs, or halt workflows when budgets are blown. An autonomous agent can currently spend unbounded money if it enters an infinite review loop.
- **Quantitative Benchmarking**: It lacks a harness to mathematically prove whether an agentic workflow is cheaper, faster, or higher quality than a human using direct CLI assistants.
- **Cost Optimization**: It currently replaces full artifacts instead of patching, driving up output token costs exponentially.
- **External Repository Integration**: The platform assumes localized, toy environments and lacks the CI/CD context to operate on external customer repos like `stock-bot`.

### Current Maturity Level
**Pre-Alpha / Proof of Concept**. The governance theory is well-defined, but the economic guardrails and empirical telemetry engines required to run it safely in the real world are missing.

### Current Production Readiness Level
**Not Production Ready**. Deploying Karsa against real-world repos right now would result in opaque token burns, infinite loops, and unmeasurable ROI. 

---

## 2. Critical Path Analysis

**Target State**: *“Karsa can autonomously analyze, review, revise, and implement changes in external repositories with measurable cost efficiency.”*

**The Shortest Path (Why we sequence this way):**
1. **Measurement First (Phase A, B)**: You cannot optimize what you cannot measure. Observability and Benchmarking are the strict prerequisites.
2. **Safety Second (Phase C)**: You cannot run autonomous agents without hard economic limits. Cost Governance prevents catastrophic API bills.
3. **Cheap Wins Third (Phase D)**: Model Routing is prioritized over complex engineering optimizations because routing trivial tasks to cheaper models yields immediate 10x ROI with very low effort.
4. **Structural Preparation Fourth (Phase E, F)**: Before we can compress tokens, we must structure the prompt deterministically (Prompt Builder) and cache the static parts (Context Cache).
5. **Deep Optimization Fifth (Phase G, H, I)**: Patch-Based revisions and Review Deltas require complex diff application logic.
6. **External Integration Last (Phase J-M)**: Only after Karsa is cheap, safe, and measurable do we point it at complex external repositories like `stock-bot`.

---

## 3. Updated Roadmap

This roadmap supersedes all previous implementation plans. It is strictly sequential.

### Phase A – Cost & Token Observability Foundation
* **Objective**: Measure exact token usage and USD cost across the entire workflow hierarchy.
* **Why it exists**: To stop flying blind.
* **Dependencies**: None.
* **Risks**: Pricing registry drift.
* **Deliverables**: Tokenizer plugin, Cost Attribution Engine, `PromptGrowthAnalytics`.
* **Success Metrics**: `execution_metrics.json` shows exact USD cost and accurate `key_fingerprint` attribution.

### Phase B – Benchmark Harness Foundation
* **Objective**: Establish the quantitative baseline against "Direct CLI" usage.
* **Why it exists**: To mathematically prove Karsa's ROI.
* **Dependencies**: Phase A.
* **Deliverables**: `BenchmarkHarness`, `TestEvaluator`, `BENCHMARK_REPORT.md` generator.
* **Success Metrics**: Ability to run a Bug Fix scenario automatically and yield a comparative matrix of Cost, Time, and Quality.

### Phase C – Cost Governance Foundation
* **Objective**: Implement hard economic guardrails to prevent infinite autonomous spending.
* **Why it exists**: A runaway agent in a review loop will bankrupt the project.
* **Dependencies**: Phase A.
* **Risks**: Overly aggressive budgets halting valid but complex work.
* **Deliverables**: 
  - `max_workflow_cost_usd` & `max_execution_cost_usd` constraints.
  - `max_review_cycles` hard limits.
  - `max_tokens_per_execution` ceiling.
  - Hard stop conditions and budget exceeded exception handling.
  - Governance telemetry dashboards.
* **Success Metrics**: The harness successfully aborts and flags an injected infinite-loop workflow before it exceeds the predefined USD budget.

### Phase D – Model Routing
* **Objective**: Route simple tasks (e.g., syntax linting) to cheap, fast models, and complex tasks (e.g., architecture) to premier models.
* **Why it exists**: Highest ROI for the lowest engineering effort. Yields immediate cost savings before deep token optimizations are built.
* **Dependencies**: Phase A.
* **Deliverables**: Dynamic Router, Model Capability Matrix.
* **Success Metrics**: Total workflow cost drops by 30% for routine tasks without loss of quality.

### Phase E – Structured Prompt Builder
* **Objective**: Standardize prompt compilation by strictly separating `system instructions`, `workflow rules`, `repository context`, `artifact context`, `issue context`, `review history`, and the `user request`.
* **Why it exists**: A prerequisite for advanced token optimization. We cannot selectively compress or attribute token growth if the prompt is a single unstructured blob of text.
* **Dependencies**: Phase A.
* **Deliverables**: Modular Prompt Builder Engine.
* **Success Metrics**: `PromptGrowthAnalytics` accurately attributes exact token counts to each prompt segment.

### Phase F – Context Cache Strategy
* **Objective**: Design native support for LLM Prompt Caching APIs (e.g., Anthropic/Gemini caching).
* **Why it exists**: To drastically reduce input costs and latency on massive repositories by caching the static `repository context` and `system instructions`.
* **Dependencies**: Phase E.
* **Deliverables**: Cacheable prompt sections, metrics for `cache_hit_ratio`, `cache_miss_ratio`, and `cache_savings_estimation`.
* **Success Metrics**: 50% reduction in billed input tokens on iterative review loops for the same task.

### Phase G – Patch-Based Revision
* **Objective**: Shift code generation from full file replacements to unified diffs/patches.
* **Why it exists**: Massive reduction in expensive output tokens.
* **Dependencies**: Phase E.
* **Deliverables**: Diff generation prompt standard, strict patch applicator.

### Phase H – Review Delta Strategy
* **Objective**: Reviewers evaluate isolated diffs against specific issues, not the entire file context.
* **Why it exists**: Input token reduction during quality checks.
* **Dependencies**: Phase G.
* **Deliverables**: Delta-context injector.

### Phase I – Prompt Summarization
* **Objective**: Compress historical memory into dense summaries for long-running workflows.
* **Dependencies**: Phase H.

### Phase J – Repository Analysis Workflow
* **Objective**: First step of external integration. Karsa clones an external repo (e.g., `stock-bot`) and builds a structural AST/Graph map.
* **Dependencies**: Phase I.

### Phase K – Architecture Delta Analysis Workflow
* **Objective**: Karsa reads a feature request and maps out exactly what files in the external repo must change.
* **Dependencies**: Phase J.

### Phase L – Implementation Workflow
* **Objective**: The Coder agent processes the Architecture Delta against the external repo.
* **Dependencies**: Phase K.

### Phase M – Verification Workflow
* **Objective**: Karsa runs the external repo's native test suite and linters in an isolated sandbox.
* **Dependencies**: Phase L.

### Phase N – Acceptance Workflow
* **Objective**: Karsa packages the diffs into a clean Pull Request with auto-generated documentation and assigns it to a human reviewer.
* **Dependencies**: Phase M.

### Phase O – Optional Future RAG / Semantic Retrieval
* **Objective**: Index massive enterprise repositories. Deferred due to complexity and unproven ROI for small-to-medium repos.

---

## 4. Cost Optimization Strategy

Based on the observability audit, the strategy is now sequenced to harvest low-hanging fruit before complex engineering:

1. **Model Routing (ROI: Very High | Effort: Low)**
   - Expected Reduction: N/A (Price arbitrage). Up to 10x savings on simple tasks.
2. **Context Cache Strategy (ROI: High | Effort: Moderate)**
   - Expected Reduction: 50%+ reduction on billed input tokens per iteration loop.
3. **Patch-Based Revision (ROI: High | Effort: High)**
   - Expected Reduction: 70%+ reduction in Output Tokens. High risk of patch application failure.
4. **Review Delta Strategy (ROI: High | Effort: High)**
   - Expected Reduction: 50-80% Input Tokens during review cycles.
5. **Prompt Summarization (ROI: Moderate | Effort: Low)**
   - Expected Reduction: Prevents unbounded token scaling in history.
6. **RAG (ROI: Unknown | Effort: Very High)**
   - Deferred.

---

## 5. Benchmark Strategy

To mathematically prove Karsa is superior, the Benchmark Harness evaluates Karsa against:
* Direct CLI usage (Zero-shot)
* Aider-like workflows (1-retry allowed)
* Single-agent workflows

**Key Metrics Tracked:**
- **Cost-Per-Success**: Total USD spent. Failed runs result in "Infinite" cost-per-success.
- **First Pass Success Rate**: Does it compile and pass tests immediately?
- **Failure Metric**: Number of human interventions required to fix hallucinations.
- **Token Efficiency Ratio**: Baseline Tokens / Karsa Tokens.

---

## 6. Future Stock-Bot Integration Strategy

When Karsa is ready to act upon `stock-bot`, it will operate as an external CI-like agent:
1. **Repository Analysis**: Clones `stock-bot`, uses the Phase J mapper to understand the directory tree.
2. **Architecture Reviews**: Generates a Change Blueprint for adding a trading strategy. Enforces human approval.
3. **Implementation**: Uses Phase G Patch-Based Revisions to edit trading algorithms.
4. **Verification**: Executes `stock-bot`'s native `pytest` framework inside the isolated Sandbox. Fails automatically if trading math breaks.
5. **Acceptance**: Never pushes to `main`. Opens a clean Pull Request on GitHub.

---

## 7. Architecture Delta

| Gap | Current Karsa Architecture | Target Autonomous Delivery Platform | Priority |
|---|---|---|---|
| **1. Missing Economic Measurement** | No token tracking. Hardcoded `karsa-llm`. | Dynamic `PricingRegistry`, `Tokenizer`, `ExecutionMetrics`. | **Critical** |
| **2. Missing Cost Guardrails** | Infinite review loops possible. Unlimited budget. | `CostGovernanceEngine`, hard limits (`max_workflow_cost_usd`). | **Critical** |
| **3. Missing Empirical Proof** | No comparative testing layer. | `BenchmarkHarness`, automated `BaselineExecutor`. | High |
| **4. Monolithic Prompts** | Unstructured text blobs. Cannot cache chunks. | `StructuredPromptBuilder`, `ContextCacheStrategy`. | High |
| **5. Full File Rewrites** | Massive output token waste. | Unified diff generation, robust Patch Applicator. | Medium |
| **6. Monolithic Models** | Fixed premier models. | Intelligent `ModelRouter` for price arbitrage. | Medium |
| **7. Missing CI/CD Integration** | Local execution only. | PR Generator, Git isolation, native sandbox test execution. | Low |

---

## 8. Execution Blueprint

### Sprint 1: Cost & Token Observability (COMPLETED)
* **Scope**: Fix provider attribution. Measure tokens.
* **Deliverables**: Tokenizer plugin, Cost Attribution Engine.
* **Exit Criteria**: `status` accurately reports USD spent per execution.

### Sprint 2: Benchmark Harness
* **Scope**: Build the test runner.
* **Deliverables**: `BenchmarkHarness`, Sandboxes, `BENCHMARK_REPORT.md`.
* **Exit Criteria**: Can successfully evaluate Karsa vs Baseline.

### Sprint 3: Cost Governance
* **Scope**: Implement economic kill-switches.
* **Deliverables**: Circuit breakers for `max_workflow_cost_usd` and infinite loop detectors.
* **Exit Criteria**: A runaway workflow is cleanly killed and reported when budget exceeds $1.00.

### Sprint 4: Model Routing
* **Scope**: Implement dynamic switching to flash models.
* **Deliverables**: Model capability matrix, router.

### Sprint 5: Structured Prompt Builder
* **Scope**: Refactor prompt generation into strictly separate context blocks.
* **Deliverables**: Prompt Builder Engine.

### Sprint 6: Context Cache Strategy
* **Scope**: Integrate LLM caching APIs into the Prompt Builder.
* **Deliverables**: Cache-aware clients.

### Sprint 7: Patch-Based Revision
* **Scope**: Shift to diff generation.

### Sprint 8: Review Delta Strategy
* **Scope**: Review isolated diffs against specific issues.

### Sprint 9: Prompt Summarization
* **Scope**: Compress long histories.

### Sprint 10: Repository Analysis Workflow
* **Scope**: AST/Graph parsing of external repositories.

### Sprint 11: Architecture Delta Workflow
* **Scope**: Change Blueprint generator.

### Sprint 12: Implementation Workflow
* **Scope**: Execute diffs against external repos.

### Sprint 13: Verification Workflow
* **Scope**: Run external unit tests in a sandbox.

### Sprint 14: Acceptance Workflow
* **Scope**: Auto-generate PRs and assign reviewers.

### Sprint 15+: Optional RAG / Semantic Retrieval
* **Scope**: Index large repos.

---

## 9. Recommended Immediate Implementation Scope

**The Next Implementation Must ONLY Cover:**
1. **Cost & Token Observability**
2. **Cost Governance Foundations**

**Why?**
All other work (Model Routing, Prompt Caching, Benchmark Harness) requires precise, empirical telemetry to prove they actually function. If you build the Benchmark Harness without exact token measurements, the benchmark is useless. If you build Model Routing without Governance, a cheap model might hallucinate and enter an infinite loop, still causing massive API bills. 

Therefore, establishing the **Observability** (to measure) and the **Governance** (to protect the budget) are the strict, unskippable prerequisites. All subsequent sprints must remain design-only until these two core capabilities are live, tested, and actively protecting the platform's economics.
