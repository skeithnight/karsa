# Sprint Roadmap Alignment Review Report

This report presents Karsa's roadmap alignment review before initiating Sprint-43, checking compliance against the Virtual Investment Firm (VIF) target architecture.

---

## 1. Current Roadmap Assessment

The current closed and proposed future roadmap (as defined in [ROADMAP.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/roadmap/ROADMAP.md)) is structured as follows:
- **Sprint-41**: Governance Engine Foundation (Closed & Protected)
- **Sprint-42**: Attribution Engine Foundation (Closed & Protected)
- **Sprint-43**: Capital Allocation Engine Foundation (Proposed Target)
- **Sprint-44**: Regime Engine Foundation (Proposed Future)
- **Sprint-45**: Thesis Engine Evolution (Proposed Future)

While the implementation of Governance (Sprint-41) and Attribution (Sprint-42) has successfully established compliance PDP verification and ex-post performance return decomposition, the proposed start of Capital Allocation in Sprint-43 presents a sequencing gap relative to its direct upstream inputs.

---

## 2. VIF Architecture Comparison

The Virtual Investment Firm target architecture defines a sequential 12-stage learning loop:

$$\text{Research} \to \text{Thesis} \to \text{Decision Journal} \to \text{CIO} \to \text{Execution} \to \text{Portfolio} \to \text{Performance} \to \text{Attribution} \to \text{Review} \to \text{Post-Mortem} \to \text{Governance} \to \text{Capital Allocation} \to \text{CIO}$$

Comparing the current repository implementation state against this target loop:
* **Governance Engine**: Fully implemented and compliant.
* **Attribution Engine**: Fully implemented (decomposing selections, allocations, execution, and beta returns).
* **Performance Engine**: **PARTIAL / Mocked Brier**. The engine does not calculate ex-post prediction accuracy dynamically; it utilizes a hardcoded Brier score stub ($0.8$).
* **Review Engine**: **PARTIAL / Text-Only**. It generates text summaries rather than the quantitative review scores required for weight scaling.
* **Capital Allocation**: **PARTIAL / Mock-Model**. It lacks database persistence, optimization solvers, and real-time integration.

---

## 3. Dependency Analysis

The Capital Allocation Engine target design ([20-capital-allocation-engine.md](file:///Users/dwiki.nugraha/dwikicode/karsa/docs/architecture/20-capital-allocation-engine.md)) relies on the following mathematical inputs:
1. **Calibrated Confidence**:
   $$\text{Calibrated Confidence} = \text{Raw Confidence} \times (1.0 - \text{Brier Score})$$
2. **Adjusted Return**:
   $$\text{Adjusted Return} = \text{Realized Return} \times \text{Attribution Factor} \times (1.0 - \text{Brier Score})$$
3. **Scoring Weight**:
   $$\text{Final Weight} = \text{Adjusted Return} \times \text{Review Multiplier} \times \text{Governance Multiplier} \times \text{Post-Mortem Multiplier}$$
   where:
   - $\text{Review Multiplier} = 0.5 + 0.5 \times \text{Review Score}$

Because the **Performance Engine** provides a mocked Brier score and the **Review Engine** lacks structured numeric scores, the Capital Allocation Engine cannot execute its ex-post scaling calculations dynamically without relying on stubs. Building Capital Allocation in Sprint-43 under the current roadmap introduces a dependency violation.

---

## 4. Critical Path Analysis

The critical path for learning loop completion requires that each calculation stage consumes actual ex-post data from its preceding node.
- **Blocked Path**: `Performance (Mocked Brier) -> Attribution (Complete) -> Review (Text-Only) -> PM (Complete) -> Gov (Complete) -> Capital Allocation`
- To resolve this block and prevent writing the Capital Allocation Engine against mocked database endpoints, we must upgrade the Performance Engine (integrating ex-post Brier score calculations) and the Review Engine (generating quantitative scores) before or during the Capital Allocation implementation.

---

## 5. Sprint Ordering Analysis

* **Is Sprint-43 still correctly defined?**  
  No. Defining Sprint-43 as purely implementing Capital Allocation solvers ignores the fact that the solvers' mathematical inputs (Brier scores and Review multipliers) are currently mock placeholders.
* **Does Sprint-43 violate any closed sprint protections?**  
  No. Capital Allocation reads from the Governance (Sprint-41) and Attribution (Sprint-42) engines using read-only adapters, which preserves closed sprint protections.
* **Should Performance Engine precede Capital Allocation Engine?**  
  **Yes**. Realized returns and Brier score accuracy are primary inputs for capital scaling.
* **Should Review/Post-Mortem Engine precede Capital Allocation Engine?**  
  **Yes**. Quantitative review scores are required to scale allocation multipliers.

---

## 6. Risks

* **Mock Proliferation**: Implementing Capital Allocation before Performance and Review Engine upgrades forces the developer to write unit and integration tests against static mock stubs, accumulating technical debt.
* **Integration Regression**: Upgrading Performance/Review engines later will require refactoring Capital Allocation integration tests, violating interface stability.

---

## 7. Recommended Sprint Sequence

To ensure complete, end-to-end learning loop integrity, the roadmap should be realigned. We propose inserting a **Performance & Review Engine Hardening** phase before Capital Allocation, or combining them:

1. **Sprint-43 (Realigned)**: Performance & Review Engine Hardening
   - *Scope*: Implement dynamic Brier score calculations in the Performance Engine, and structure numeric scoring in the Review Engine.
2. **Sprint-44**: Capital Allocation Engine Foundation
   - *Scope*: Build mean-variance/covariance solvers and Append-Only Allocation ledgers.
3. **Sprint-45**: Regime Engine Foundation
4. **Sprint-46**: Thesis Engine Evolution

---

## 8. Architecture Delta Analysis

- **Architecture Delta = NONE**  
  This review proposes a realignment of the *sprint sequence* only, ensuring dependency compliance without mutating the frozen Virtual Investment Firm architecture designs.

---

## 9. Final Verdict

### **`ROADMAP_REALIGNMENT_REQUIRED`**
*The roadmap must be realigned to implement/remediate Performance Engine Brier scores and Review Engine scoring before Capital Allocation is finalized.*
