# Sprint-04: Firm Intelligence Platform Implementation Plan

## 1. Executive Summary
The Sprint-04 Implementation Plan translates the frozen Firm Intelligence Platform architecture into an executable roadmap. It provides exact schema definitions for the Slowly Changing Dimension (SCD2) Data Mart, precise materialized view definitions for autonomous agent APIs, and rigorous deterministic replay testing strategies. By adhering strictly to the Read-Only CQRS constraints defined in ADR-093 through ADR-098, this implementation guarantees zero business domain leakage while providing the foundational `O(1)` intelligence layer required by Sprint-58.

## 2. Repository Inventory Matrix
| Module | Path | Status | Action Required |
| :--- | :--- | :--- | :--- |
| **Intelligence Domain** | `src/karsa/firm_intelligence/` | Missing | Create module boundary |
| **Data Mart Schemas** | `src/karsa/infrastructure/persistence/alembic/` | Needs Extension | Create Alembic migration `006` |
| **Projections** | `src/karsa/firm_intelligence/projections.py` | Missing | Implement `DataMartProjectionService` |
| **Query Repositories** | `src/karsa/firm_intelligence/repository/` | Missing | Implement `PostgresIntelligenceDataMartRepository` |
| **DTOs** | `src/karsa/firm_intelligence/api/dtos.py` | Missing | Define read-only Pydantic models |
| **APIs** | `src/karsa/firm_intelligence/api/routes.py` | Missing | Implement FastAPI endpoints |
| **Query Service** | `src/karsa/firm_intelligence/application/` | Missing | Implement `FirmIntelligenceQueryService` |
| **Tests** | `tests/karsa/firm_intelligence/` | Missing | Implement Replay and SCD2 tests |
| **Karsa Web** | `karsa-web/src/app/intelligence/` | Needs Extension | Build CIO Dashboards |

## 3. Implementation Delta Matrix
| Component | Existing Base | Target Implementation |
| :--- | :--- | :--- |
| **Read Models** | 3NF flat tables | Centralized SCD2 Star-Schema (Data Mart) |
| **Projections** | Upsert-only handlers | Complex SCD2 maintenance + `is_current` toggling |
| **APIs** | Standard GET endpoints | Point-in-Time queries via `effective_date` inputs |

## 4. Projection Implementation Plan
**Component:** `DataMartProjectionService`
*   **Responsibilities:** Listens to `WorkerLifecycleTransitionedEvent`, `WorkerAlphaRecordedEvent`, `CreditAllocatedEvent`, etc.
*   **SCD2 Dimension Maintenance:** When a worker's classification changes, the projection must:
    1. `UPDATE dim_worker SET effective_to = :now, is_current = FALSE WHERE worker_urn = :urn AND is_current = TRUE`
    2. `INSERT INTO dim_worker (worker_urn, classification, effective_from, effective_to, is_current) VALUES (:urn, :new_class, :now, '9999-12-31', TRUE)`
*   **Fact Append Logic:** Facts strictly `INSERT` into `fact_` tables. Foreign keys MUST resolve to the exact `dim_id` (surrogate key) that was `is_current = TRUE` at the time of the event.
*   **Idempotency Strategy:** `fact_` tables maintain a `UNIQUE(event_sequence)` constraint to safely ignore duplicate processing.
*   **Checkpoint Locking:** Uses existing `projection_checkpoints` logic via `lock_checkpoint('firm_intelligence_mart')`.

## 5. Data Mart Schema Design
```sql
-- Dimensions (SCD2)
CREATE TABLE dim_worker (
    dim_worker_id SERIAL PRIMARY KEY,
    worker_urn VARCHAR(255) NOT NULL,
    subject_type VARCHAR(50) NOT NULL,
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59',
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_dim_worker_urn ON dim_worker(worker_urn);

CREATE TABLE dim_regime (
    dim_regime_id SERIAL PRIMARY KEY,
    regime_urn VARCHAR(255) NOT NULL,
    regime_type VARCHAR(50) NOT NULL,
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59',
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

-- Facts
CREATE TABLE fact_alpha_generation (
    fact_id BIGSERIAL PRIMARY KEY,
    dim_worker_id INT REFERENCES dim_worker(dim_worker_id),
    dim_regime_id INT REFERENCES dim_regime(dim_regime_id),
    alpha_delta FLOAT NOT NULL,
    cumulative_alpha FLOAT NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    event_sequence BIGINT NOT NULL UNIQUE
) PARTITION BY RANGE (event_timestamp);

-- Graph
CREATE TABLE edge_swarm_attribution (
    edge_id BIGSERIAL PRIMARY KEY,
    parent_worker_urn VARCHAR(255),
    child_worker_urn VARCHAR(255) NOT NULL,
    attribution_urn VARCHAR(255) NOT NULL,
    skill_ratio FLOAT NOT NULL,
    event_sequence BIGINT NOT NULL UNIQUE
);
```

## 6. Materialized View Design
*   **`vw_cio_capital_allocation_readiness`**
    *   *Source:* Joins `dim_worker` (where `is_current=TRUE`), `fact_capability_transition`, `dim_regime`.
    *   *Refresh:* Asynchronous `REFRESH MATERIALIZED VIEW CONCURRENTLY` triggered via cron or high-watermark events.
    *   *Latency:* `< 10ms` for API reads.
*   **`vw_governance_suspension_audit`**
    *   *Source:* Filters `fact_capability_transition` where `authority = 'RISK_OFFICER'`.
*   **`vw_swarm_diagnostic_tree`**
    *   *Source:* Uses `WITH RECURSIVE` CTE traversing `edge_swarm_attribution`. Evaluated dynamically on read or cached hourly depending on payload size.

## 7. Repository Design
**`PostgresIntelligenceDataMartRepository`**
Strictly issues `SELECT` statements against `vw_` views or raw `fact_` joins for Point-In-Time queries. Never utilizes SQLAlchemy ORM Session writes; uses purely raw SQL text queries mapped to DTOs for extreme performance.

## 8. DTO Design
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class AllocationReadinessDTO(BaseModel):
    worker_urn: str
    subject_type: str
    current_capability_score: float
    deployment_limit: float
    regime_type: str

class IntelligenceResponseDTO(BaseModel):
    data: List[AllocationReadinessDTO]
    last_processed_sequence: int = Field(..., description="Sequence ID of latest event mapped")
    generated_at: datetime
```

## 9. API Design
*   `GET /intelligence/cio/allocation-readiness?regime_type=BEAR`
*   `GET /intelligence/governance/suspensions?since=2024-01-01`
*   `GET /intelligence/swarms/{urn}/diagnostics`
*(All routes return `IntelligenceResponseDTO` wrappers).*

## 10. Query Service Design
**`FirmIntelligenceQueryService`**
Receives API parameters, applies sorting and pagination, and executes the read from the Repository. Exposes `query_point_in_time(date_target)` which explicitly injects `WHERE event_timestamp <= :dt AND effective_from <= :dt AND effective_to > :dt` into the SQL execution layer. No business math is calculated.

## 11. Replay Validation Plan
1.  **Populate:** Run integration suite generating thousands of Sprint 01-03 events across Swarms, Lifecycle transitions, and Alpha captures.
2.  **Assert:** Query `GET /intelligence/cio/allocation-readiness`. Save state snapshot.
3.  **Destroy:** `TRUNCATE TABLE dim_worker CASCADE; TRUNCATE fact_alpha_generation CASCADE; UPDATE projection_checkpoints SET last_processed_sequence = 0;`
4.  **Replay:** Wait for projection worker to consume all events.
5.  **Verify:** `GET /intelligence/cio/allocation-readiness` must precisely match the saved snapshot. Row counts across all `fact_` tables must perfectly equal pre-destruction counts.

## 12. Test Strategy
*   **SCD2 Tests:** Emit two conflicting classification updates for the same worker. Assert `dim_worker` contains 2 rows, exactly one with `is_current = TRUE` and correctly bounded `effective_` timestamps.
*   **Materialized View Tests:** Assert `REFRESH CONCURRENTLY` correctly surfaces newly appended facts without locking read transactions.
*   **Point-In-Time Tests:** Emit events over simulated days. Query `date_target = Day 2`. Assert Day 3 facts are completely masked from the response payload.

## 13. Production Readiness Checklist
- [ ] Partition `fact_` tables by monthly `event_timestamp`.
- [ ] Index `is_current` and `worker_urn` on all Dimensions.
- [ ] Schedule `REFRESH MATERIALIZED VIEW` pg_cron jobs.
- [ ] Verify Checkpoint isolation for the Intelligence sink.
- [ ] Attach Grafana dashboards monitoring `last_processed_sequence` lag to detect stale intelligence.

## 14. Technical Debt Register
*   **None.**

## 15. Scope Compliance Report
*   **No Aggregates Introduced:** Verified.
*   **No Commands Introduced:** Verified.
*   **No Events Emitted:** Verified.
*   **CQRS Preserved:** Verified.
*   **ADR-093 (No Aggregates):** Compliant.
*   **ADR-094 (Star Schema):** Compliant.
*   **ADR-095 (Ephemeral Aggregation):** Compliant.
*   **ADR-096 (Analytics vs Decisions):** Compliant. APIs strictly read.
*   **ADR-097 (Dimension Ownership):** Compliant. `dim_worker` strictly tracks identity keys and time bounds.
*   **ADR-098 (SCD2 Enforcement):** Compliant. `effective_from` and `effective_to` are mandatory schema columns.

## 16. Final Verdict
IMPLEMENTATION_READY
