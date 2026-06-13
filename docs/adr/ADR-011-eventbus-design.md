---
status: ACTIVE
owner: Karsa Architecture Team
created: 2026-06-11
last_reviewed: 2026-06-11
next_review: 2027-06-11
---

# ADR-011: EventBus Design

Context: Need to decouple metrics aggregation.
Decision: Implement synchronous singleton EventBus.
Tradeoffs: Lacks exception isolation.