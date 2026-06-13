# Sprint-15 Performance Engine Foundation - Architecture Revision v5

## Executive Summary of Changes
This Revision v5 aggressively refines the boundaries of the Performance Engine, elevating it from a simple fractional-PNL aggregator into a fully context-aware, relative-performance evaluator. It introduces benchmark-awareness to isolate true alpha from market beta, formally inserts the `ThesisPerformanceProfile` to differentiate between bad execution and bad ideas, strictly delineates quantitative Performance from qualitative Review, and explicitly formalizes the projection layer consumed by the future Capital Allocation Engine. The underlying CQRS, Replay, and Layered Pipeline architectures remain unchanged.

---

## Finding 1: Performance vs Attribution Boundary

### Challenge
Relying solely on `AttributionCalculatedEvent` means the Performance Engine blindly praises a worker for generating +$100, even if the market benchmark returned +$300. Attribution defines "who gets the fractional credit for the absolute dollars." Performance must define "whether the execution of the decision was objectively good."

### Boundary Analysis & Dependency Model
- **Attribution Engine**: Owns Absolute Fractional PNL. (e.g., "Worker A receives 60% of the $1,000 profit = $600.")
- **Performance Engine**: Owns Contextual Relative Alpha. (e.g., "Worker A's $600 profit represents an annualized return of 10%, but the benchmark returned 15%. The decision produced negative alpha.")

### Required Inputs for Performance
To generate true performance intelligence, the `DecisionPerformanceRecord` must consume:
1. `InvestmentOutcomeRealizedEvent` (Absolute Risk Taken, Duration)
2. `AttributionCalculatedEvent` (Worker's Fractional Cut)
3. `BenchmarkRealizedEvent` (Market/Index Return over the same duration)

### Decision & ADR-15.10: Contextual Performance Anchor
**Performance is Anchored to Relative Alpha.** The Performance Engine structurally rejects absolute PNL as the sole arbiter of success. The `DecisionPerformanceRecord` mathematically fuses Attribution inputs with broader Outcome and Benchmark events to calculate Risk-Adjusted Alpha.

---

## Finding 2: Missing Thesis Performance Layer

### Challenge
Without evaluating the Thesis itself, the firm cannot distinguish between a brilliant thesis ruined by terrible timing/execution, or a terrible thesis saved by luck. 

### Thesis Performance Model & Hierarchy Analysis
The `ThesisPerformanceProfile` is introduced as a mandatory intermediate projection. A single Thesis may spawn multiple Decisions (e.g., scale in, partial exit, full exit). 

**Updated Projection Hierarchy:**
1. `DecisionPerformanceRecord` (Root)
2. **`ThesisPerformanceProfile`** (Groups all decisions executed under one Thesis)
3. `WorkerPerformanceProfile` 
4. `StrategyPerformanceProfile`
5. `RegimePerformanceProfile`

### Compatibility Analysis
By inserting `ThesisPerformanceProfile`, the system seamlessly bridges the `Thesis Engine` (which owns the content of the idea) with the future `Review Engine`. The Review Engine can directly query the `ThesisPerformanceProfile` to definitively answer: *"Was the thesis correct?"* before investigating the execution decisions.

---

## Finding 3: Performance vs Review Boundary

### Challenge
The roadmap indicates the Review Engine will handle Root Cause Analysis and Decision Journals. The boundary between Performance and Review must be heavily fortified to prevent logic duplication.

### Performance vs Review Boundary Matrix
| Engine | Core Question | Domain Responsibility | Data Type |
|--------|---------------|-----------------------|-----------|
| **Performance Engine** | *What* happened? | Generates objective statistics, hit-rates, Brier scores, alpha, and regime correlations. | Quantitative, Algorithmic, Deterministic. |
| **Review Engine** | *Why* did it happen? | Conducts post-mortems, root cause analyses, classifies errors (Execution vs Thesis flaw), and logs journal entries. | Qualitative, Human-in-the-loop, Narrative. |

### Conclusion
**Performance owns the Math. Review owns the Narrative.**
The Performance Engine will never attempt to classify *why* a decision failed. It simply flags the decision as a severe mathematical outlier (e.g., max drawdown exceeded, confidence wildly uncalibrated) and explicitly routes a `ReviewTriggeredEvent` to the downstream Review Engine.

---

## Finding 4: Capital Allocation Dependency Risk

### Challenge
If the Capital Allocation Engine consumes raw performance metrics (like Brier Scores and Regime Win Rates), it is forced to perform massive internal synthesis to decide virtual account sizes. This leaks performance synthesis logic out of the Performance Engine.

### Alternatives Considered
- **Option A**: Capital Allocation derives everything itself. (Causes logic leakage).
- **Option B**: Performance publishes allocation-ready projections.
- **Option C**: Dedicated allocation-input projection layer.

### Decision
**Option B is selected.** The Performance Engine owns the final synthesis of performance data into a discrete, allocation-ready score. 

### Architecture Impact
The Performance Engine introduces the **`CapitalAllocationSynthesisProfile`**.
This profile mathematically reduces a worker's multi-dimensional performance into normalized, bounded allocation multipliers:
- `regime_adjusted_multiplier` (0.0 - 2.0)
- `calibration_adjusted_multiplier` (0.0 - 1.0)
- `drawdown_penalty_multiplier` (0.0 - 1.0)

### ADR-15.11: Synthesized Allocation Projections
The Performance Engine is explicitly responsible for translating raw quantitative metrics into synthesized, allocation-ready multipliers. The Capital Allocation Engine's sole responsibility is applying those multipliers against the firm's total available capital pool to generate dollar-value portfolio limits.

---

## Architecture Delta Analysis
- **Delta 1**: Shifted Performance anchor from absolute PNL (Attribution) to Relative Alpha (Attribution + Benchmark) via ADR-15.10.
- **Delta 2**: Inserted `ThesisPerformanceProfile` into the CQRS Projection Hierarchy to isolate execution variance from thesis accuracy.
- **Delta 3**: Formalized the Quantitative (Performance) vs Qualitative (Review) boundary.
- **Delta 4**: Created the `CapitalAllocationSynthesisProfile` (ADR-15.11) to shield the Capital Engine from raw statistical synthesis.

## Final Verdict
**READY_FOR_ARCHITECTURE_REVIEW**

*Justification*: Architecture Revision v5 definitively seals all remaining bounded-context ambiguities across the entire Virtual Investment Firm roadmap. By aligning Performance to relative alpha, inserting the Thesis layer, isolating Review concerns, and packaging the outputs for Capital Allocation, the foundation is structurally flawless and fully compatible with the long-term firm architecture.
