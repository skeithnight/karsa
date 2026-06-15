# Technical Debt Register

## Non-Blocking Technical Debt
| ID | Bounded Context | Description | Classification | Impact | Target Remediation |
|---|---|---|---|---|---|
| TD-50-01 | `karsa.regime` | Stale tests in `test_regime_repositories_batch2.py` violate new domain OCC transition logic introduced in Sprint-48/49 (`IllegalStateTransitionError`). | stale tests | NON_BLOCKING_TECHNICAL_DEBT | Sprint-51 / Future testing sprint |
| TD-50-02 | `karsa.regime` | SQLite test engines lack native `Decimal` casting capabilities required by the PostgreSQL repository (`test_occ_conflict`, `test_natural_key_uniqueness`). | SQLite/PostgreSQL fixture mismatch | NON_BLOCKING_TECHNICAL_DEBT | Sprint-51 / Future testing sprint |
| TD-50-03 | `karsa.regime` | The integration test `test_natural_key_uniqueness` directly asserts `sqlalchemy.exc.IntegrityError` instead of the domain abstraction `ImmutableUpdateError`. | stale tests | NON_BLOCKING_TECHNICAL_DEBT | Sprint-51 / Future testing sprint |
