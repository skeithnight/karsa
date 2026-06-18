# Sprint-42 Performance Attribution Engine Foundation Implementation

This document presents the implementation details of the ex-post **Performance Attribution Engine Foundation** context for Sprint-42.

---

## 1. Executive Summary

The Performance Attribution Engine Foundation has been implemented in accordance with the frozen architecture definitions. It handles multi-horizon performance attribution decomposition (selection, allocation, execution, beta, and residuals) using standardized compounding strategies (Frongello, Carino, Menchero). It utilizes immutable persistence patterns protected by database-level triggers, range-partitioned ledger tables, event versioning, deterministic replayability, and recomputation chains.

All implementation deliverables (source code, alembic migration schema, and test suite) are complete and verified.

---

## 2. Domain Model Mapping

The domain models are defined in [models.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/models.py).
* **AttributionSession**: The aggregate root that manages the lifecycle of ex-post horizon calculation runs. It transitions through standard states: `STAGED` $\to$ `COMPUTING` $\to$ `CALIBRATED` $\to$ `SEALED`.
* **PerformanceAttributionRecord**: A write-once ledger entity representing the multi-period attribution returns (selection, allocation, execution, beta, and residuals) for a specific asset associated with a session and ex-ante decision.

---

## 3. Aggregate Mapping

### AttributionSession
* `session_id` (UUID/String): Unique identifier.
* `horizon_start` (DateTime): Ex-post horizon lower bound.
* `horizon_end` (DateTime): Ex-post horizon upper bound.
* `state` (String): Active stage (`STAGED`, `COMPUTING`, `CALIBRATED`, `SEALED`).
* `compounding_strategy` (String): Smooth math strategy (`FRONGELLO`, `CARINO`, `MENCHERO`).
* `raw_input_manifest_hash` (String): SHA-256 hash of the ex-post input manifest.
* `aggregate_version` (Integer): Incremented for optimistic concurrency control (OCC).

### PerformanceAttributionRecord
* `record_id` (UUID/String): Unique identifier.
* `session_id` (UUID/String): Associated attribution run.
* `decision_id` (String): Source ex-ante decision URN.
* `thesis_urn` / `worker_urn` / `capability_urn` / `regime_urn` (String): Lineage tracking tags.
* `asset_urn` (String): Target asset identifier URN.
* `selection_return` / `allocation_return` / `execution_return` / `beta_return` / `liquidation_tracking_residual` (Decimal): Decomposed sub-period returns.
* `attribution_version` (Integer): Incremented for successive recalculations.
* `is_active` (Boolean): Active indicator (strictly transitions from `True` to `False` on invalidation).
* `superseded_by_version` (Integer, nullable): Points to the version that superseded this record. Populated during deactivation via `deactivate_old_versions`.
* `invalidated_by_version` (Integer, nullable): Points to the version that invalidated this record. Populated during deactivation via `deactivate_by_session`.
* `calculated_at` (DateTime): Timestamp of creation.
* `aggregate_version` (Integer): Incremented for state changes.

---

## 4. Value Object Mapping

Defined in [value_objects.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/value_objects.py).
* **BenchmarkSnapshot**: Frozen reference structures containing ex-post benchmark returns series (read-only; no construction or calculations performed).
* **CompoundingStrategy**: Interface for sub-period smoothing:
  * **FrongelloCompounding**: Multi-period compounding math. To prevent denominator collapse when return approaches $-100\%$, returns are capped at a safety floor of $-99.9999\%$.
  * **CarinoCompounding**: Adjusts sub-period weights using Carino scaling factors.
  * **MencheroCompounding**: Adjusts sub-period weights using Menchero scaling factors.
* **CanonicalManifestSerializer**: Deterministic JSON encoder. It lexicographically sorts all keys, normalizes timezones to UTC, and pads decimals to 12-digit string representations before generating SHA-256 hashes.

---

## 5. Event Mapping

Defined in [events.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/events/events.py).
* **AttributionCalculatedEvent** (v1): Broadcast when an `AttributionSession` transitions to `SEALED`. Contains all computed attribution record details.
* **AttributionSupersededEvent** (v1): Emitted when a record's `is_active` status is toggled to `False` during a recomputation.
* **AttributionInvalidatedEvent** (v1): Emitted when a session's records are invalidated.
* **AttributionRecomputedEvent** (v1): Broadcast when a recomputation completes.

---

## 6. Repository Mapping

Defined in [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/domain/model/repositories.py) and implemented in [repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/src/karsa/attribution/infrastructure/repositories.py).
* **AttributionSessionRepository**: Standard CRUD/OCC operations (`save`, `get_by_id`, `list_all`, `clear`).
* **PerformanceAttributionRepository**: Immutable batch save and query capabilities (`save`, `find_by_id`, `find_active_by_decision`, `find_by_session`, `list_all`, `deactivate_old_versions`, `deactivate_by_session`, `clear`).

---

## 7. Persistence Mapping

Three repository implementations are provided:
1. **InMemory repositories**: Fast, thread-safe memory storage using deep-copied entities to avoid reference mutations.
2. **File-based repositories**: Flat JSON files under `.karsa/attribution/` directory.
3. **PostgreSQL repositories**: Production-grade relational storage supporting triggers, partitioning, and transactional isolation.

---

## 8. PostgreSQL Schema Summary

* **attribution_sessions**:
  ```sql
  CREATE TABLE attribution_sessions (
      session_id UUID PRIMARY KEY,
      horizon_start TIMESTAMP NOT NULL,
      horizon_end TIMESTAMP NOT NULL,
      state VARCHAR(64) NOT NULL,
      compounding_strategy VARCHAR(64) NOT NULL,
      raw_input_manifest_hash VARCHAR(256) NOT NULL,
      aggregate_version INTEGER NOT NULL
  );
  ```
* **performance_attribution_records**:
  ```sql
  CREATE TABLE performance_attribution_records (
      record_id UUID NOT NULL,
      session_id UUID NOT NULL,
      decision_id VARCHAR(256) NOT NULL,
      thesis_urn VARCHAR(256) NOT NULL,
      worker_urn VARCHAR(256) NOT NULL,
      capability_urn VARCHAR(256) NOT NULL,
      regime_urn VARCHAR(256) NOT NULL,
      asset_urn VARCHAR(256) NOT NULL,
      selection_return NUMERIC NOT NULL,
      allocation_return NUMERIC NOT NULL,
      execution_return NUMERIC NOT NULL,
      beta_return NUMERIC NOT NULL,
      liquidation_tracking_residual NUMERIC NOT NULL,
      attribution_version INTEGER NOT NULL,
      is_active BOOLEAN NOT NULL,
      calculated_at TIMESTAMP NOT NULL,
      aggregate_version INTEGER NOT NULL,
      PRIMARY KEY (record_id, calculated_at)
  ) PARTITION BY RANGE (calculated_at);
  ```

---

## 9. Trigger Summary

* PL/pgSQL function `block_attribution_record_mutation()` enforces record immutability.
* It raises exceptions on `DELETE` and blocks updates unless it is a transition of `is_active` from `TRUE` to `FALSE` (with all other columns remaining identical to protect calculations).
* Trigger binding:
  ```sql
  CREATE TRIGGER enforce_record_immutability
  BEFORE UPDATE OR DELETE ON performance_attribution_records
  FOR EACH ROW EXECUTE FUNCTION block_attribution_record_mutation();
  ```

---

## 10. Partitioning Summary

* The `performance_attribution_records` table is range partitioned quarterly by `calculated_at` timestamps.
* A default catch-all table `performance_attribution_records_default` is created by default. Sub-partitions can be added dynamically without altering application logic.

---

## 11. Replayability Mapping

Lineage is deterministically validated:
`Transaction -> AttributionSession -> PerformanceAttributionRecord -> BenchmarkSnapshot -> ManifestHash`.
When a replay is requested, `AttributionReplayService` serializes the historical inputs using `CanonicalManifestSerializer` and compares the resulting hash against `session.raw_input_manifest_hash`. If matched, calculations are verified dynamically against persisted values.

---

## 12. Test Mapping

Comprehensive coverage is implemented under `tests/karsa/attribution/`:
1. **Attribution calculations**: [test_attribution_services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_attribution_services.py#L19)
2. **Frongello compounding**: [test_attribution_domain.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/domain/test_attribution_domain.py#L81)
3. **Benchmark floor protection**: [test_attribution_domain.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/domain/test_attribution_domain.py#L104)
4. **Canonical manifest hashing**: [test_attribution_domain.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/domain/test_attribution_domain.py#L138)
5. **Replayability**: [test_attribution_services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_attribution_services.py#L139)
6. **Version superseding**: [test_attribution_services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_attribution_services.py#L64)
7. **Invalidation propagation**: [test_attribution_services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_attribution_services.py#L111)
8. **Recomputation chains**: [test_attribution_integration.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/test_attribution_integration.py#L17)
9. **Immutability triggers**: [test_postgres_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/infrastructure/test_postgres_repository.py#L158)
10. **Partitioning validation**: [test_postgres_repository.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/infrastructure/test_postgres_repository.py#L158)
11. **Repository implementations**: [test_attribution_repositories.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/infrastructure/test_attribution_repositories.py#L15)
12. **Event publication**: [test_attribution_services.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_attribution_services.py#L104)
13. **Failure recovery**: [test_audit.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_audit.py#L14)
14. **Queue replay**: [test_audit.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_audit.py#L58)
15. **Multi-version reconstruction**: [test_audit.py](file:///Users/dwiki.nugraha/dwikicode/karsa/tests/karsa/attribution/application/test_audit.py#L112)

---

## 13. Known Limitations

* **Rounding Residues**: Small residuals may occur during high-precision divisions when smoothing extremely small returns (approaching $-100\%$). These are bound to the `liquidation_tracking_residual` key.
* **Calculated-At Bound Constraints**: Querying partitioned records requires filtering on `calculated_at` bounds to optimize partition pruning.

---

## 14. Final Status

* **Status**: `IMPLEMENTATION_COMPLETE`
* **Verdict**: `IMPLEMENTATION_COMPLETE`
* The ex-post Performance Attribution Engine Foundation is fully implemented, verified, and integrated into Karsa's repository pipeline.
