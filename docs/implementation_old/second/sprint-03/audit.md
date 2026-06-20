# Sprint 3 Scope Validation Audit

## Overview
This audit challenges the architecture design for Sprint 3 (Producer Foundation) by evaluating whether the project should implement a full Virtual Investment Firm workflow sequence (Option B) or restrict itself strictly to the end-to-end CQRS pipeline proof (Option A), applying rigorous YAGNI principles based strictly on current repository reality.

## 1. Event Consumer Reality Check

**Proposed Genesis Lineage:**
1. `MarketSnapshotCapturedEvent`
2. `ResearchCreatedEvent`
3. `ThesisCreatedEvent`
4. `ForecastCreatedEvent`
5. `ReviewCompletedEvent`
6. `OrderFilledEvent`

**Analysis:**
1. **How many of these events currently have projections, read models, APIs, and dashboard consumers?**
   - **Exactly one:** `OrderFilledEvent`. It triggers `PortfolioProjectionService`, updates `ValuationRepository`, and is served by `/portfolio/summary` to the Karsa Web Dashboard.
   - The other five events have *no projection handlers*, *no read models*, *no APIs*, and their Karsa Web dashboard components are either missing or hardcoded to return empty arrays.
2. **Which events create immediate observable value?**
   - Only `OrderFilledEvent`.
3. **Which events are currently dead events?**
   - `MarketSnapshotCapturedEvent`, `ResearchCreatedEvent`, `ThesisCreatedEvent`, `ForecastCreatedEvent`, and `ReviewCompletedEvent` are all dead events. If emitted, they will rest unread in `event_journal`.
4. **Is emitting dead events compatible with YAGNI?**
   - **No.** Engineering complex Pydantic domain payloads for events that have zero downstream consumers violates YAGNI fundamentally. It is premature implementation.
5. **If Sprint 3 objective is only to populate the dashboard, populate `event_journal`, prove replayability, and prove projections, would a single `OrderFilledEvent` be sufficient?**
   - **Yes.** Emitting a single `OrderFilledEvent` perfectly exercises the entire Write and Read CQRS architecture backbone, achieving all MVP goals immediately.

---

## 2. Option Comparison

### Option A: `BootstrapProducer -> OrderFilledEvent`
- **Implementation Cost:** Very Low (Constructs and emits a single JSON payload).
- **Observable Value:** High (Instantly updates Karsa Web Total AUM).
- **Future Compatibility:** Acceptable (When upstream domains are built in future sprints, the database can be truncated and a full lineage seeded).
- **YAGNI Compliance:** Perfect. No code is written that doesn't immediately serve a feature.

### Option B: `BootstrapProducer -> Market -> Research -> Thesis -> Forecast -> Review -> OrderFilled`
- **Implementation Cost:** High (Requires defining, instantiating, and emitting five additional complex domain structures that do not fully exist).
- **Observable Value:** High (Exactly identical to Option A, as the first 5 events are invisible).
- **Future Compatibility:** High, but premature.
- **YAGNI Compliance:** Violated. Code is written for future consumers that do not exist.

---

## 3. Verdict

**Return: OPTION_A_RECOMMENDED**

### Evidence-Based Conclusion:
The current repository reality dictates that `OrderFilledEvent` is the only event capable of proving the projection pipeline all the way to Karsa Web. Therefore, under strict YAGNI, the Sprint 3 MVP must be restricted to a `karsa-bootstrap-producer` script that emits *only* an `OrderFilledEvent` (with a synthetic correlation ID) and exits. The full lineage should be deferred to a future sprint when the corresponding projections and read models are actually developed.
