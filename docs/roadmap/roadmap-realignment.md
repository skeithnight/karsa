# Sprint-43 Roadmap Realignment Decision Report

This report presents Karsa's roadmap realignment decision audit, analyzing options to address the dependency gaps identified in the Performance and Review Engines prior to implementing Capital Allocation.

---

## 1. Executive Summary

A roadmap realignment decision audit was performed to evaluate two alternatives for Karsa's sprint sequence. 

The audit concludes that **Option B** (separating Performance Engine Foundation and Review & Post-Mortem Foundation into isolated sprints) represents the superior path. It respects bounded context boundaries, preserves strict single-writer persistence rules, isolates aggregate root ownership, and mitigates the risk of boundary leakage.

**Verdict**: `ROADMAP_REALIGNMENT_APPROVED`

---

## 2. Current Roadmap Assessment

The baseline roadmap scheduled Sprint-43 as Capital Allocation Engine Foundation. However, the roadmap alignment review identified that:
1. **Performance Engine** uses mocked ex-post Brier score stubs.
2. **Review Engine** lacks structured quantitative scoring (generating text-only reviews).
3. **Capital Allocation** mathematically requires actual ex-post Brier scores (from Performance) and quantitative Review scores (from Review) to scale capital weights.

Proceeding directly with Capital Allocation in Sprint-43 would force implementation against mock stubs, violating critical path integrity. A realignment of the roadmap is required.

---

## 3. Dependency Analysis

The downstream Capital Allocation Engine target architecture integrates ex-post results using:
- **Brier Score ($BS$)**: Measures forecast accuracy to calibrate agent confidence:
  $$\text{Calibrated Confidence} = \text{Raw Confidence} \times (1.0 - BS)$$
- **Review Score ($RS$)**: Derived from Convergence audits, defining the weight multiplier:
  $$\text{Review Multiplier} = 0.5 + 0.5 \times RS$$

- **Performance Engine** must be fully upgraded to process ex-ante Decision Journal confidence parameters and calculate actual Brier scores dynamically.
- **Review Engine** must be upgraded to generate structured numeric `ReviewScore` fields.
- **Dependency Sequencing**: Performance calculations feed into Attribution factors, which propagate into Review Engine convergence audits.

---

## 4. Ownership Boundary Analysis

- **Performance Engine Boundary**: Authoritatively owns position returns, confidence limits, and forecast prediction scoring (Brier Score/CRPS).
- **Review Engine Boundary**: Authoritatively owns ex-post audit trails, convergence audits, and qualitative/quantitative review score records.
- **Capital Allocation Boundary**: Consumes ex-post scores to optimize budgets.

To prevent boundary leakage, Performance return scoring and Review audit scoring must be kept strictly separated in distinct relational schemas, tables, and services.

---

## 5. Critical Path Analysis

The VIF learning loop critical path flows as:
$$\text{Performance} \to \text{Attribution} \to \text{Review} \to \text{Post-Mortem} \to \text{Governance} \to \text{Capital Allocation}$$

Upgrading Karsa requires resolving the stubs along this critical path sequentially. We must harden the Performance Engine return calculations first, then build quantitative Review convergence scores, and finally implement Capital Allocation optimization.

---

## 6. Option A Assessment

* **Sequence**:
  - Sprint-43: Performance & Review Hardening (Combined)
  - Sprint-44: Capital Allocation Engine Foundation
* **Pros**:
  - Reduces the total sprint count by combining Performance and Review changes into a single sprint.
* **Cons**:
  - **Boundary Leakage**: Mixing the Performance and Review Engine changes in a single sprint leads to blurred responsibilities, violating bounded context isolation.
  - **Implementation Congestion**: High risk of rushed domain modeling and trigger validations, leading to technical debt.
  - **Testing Debt**: Hardening both engines in a single sprint makes write-once triggers and replayability validations difficult to isolate.

---

## 7. Option B Assessment

* **Sequence**:
  - Sprint-43: Performance Engine Foundation
  - Sprint-44: Review & Post-Mortem Foundation
  - Sprint-45: Capital Allocation Foundation
* **Pros**:
  - **Context Isolation**: Strictly separates return accuracy scoring (Performance) from audit convergence checks (Review), maintaining single-writer rules.
  - **Replayability Protection**: Each sprint defines its own separate schemas, triggers, and replayability tests.
  - **Scalability**: Allows each context database (e.g., `db_performance` vs `db_review`) to scale separately under isolated partitioning strategies.
* **Cons**:
  - Extends the timeline by adding one additional sprint before implementing Capital Allocation.

---

## 8. Recommended Roadmap

We select **Option B** as the approved realignment sequence. The new consolidated sprint roadmap is:

1. **Sprint-43**: Performance Engine Foundation
   - *Scope*: Postgres-backed database schemas, ex-ante Decision Journal integration, dynamic ex-post Brier score calculations, immutability triggers, and deterministic replayability.
2. **Sprint-44**: Review & Post-Mortem Foundation
   - *Scope*: Quantitative Review Score models, convergence audits, and Post-Mortem action ledger integrations.
3. **Sprint-45**: Capital Allocation Engine Foundation
   - *Scope*: Optimization solvers, Append-Only Allocation policy ledgers, and top-down risk-budgeting.
4. **Sprint-46**: Regime Engine Foundation
5. **Sprint-47**: Thesis Engine Evolution

---

## 9. Architecture Delta Analysis

- **Architecture Delta = NONE**  
  Option B resolves the roadmap dependencies using the frozen VIF architecture definitions without altering system boundaries or database interfaces.

---

## 10. Risks

- **Sprint Overhead**: Option B increases the roadmap by one sprint, requiring additional design and audit reviews.
  - *Remediation*: Bounded context designs are kept tight and focused on foundation tables and core triggers.

---

## 11. Final Verdict

### **`ROADMAP_REALIGNMENT_APPROVED`**
*Option B is approved. The sprint sequence will be realigned to implement Sprint-43 Performance Engine Foundation and Sprint-44 Review & Post-Mortem Foundation before starting Capital Allocation.*
