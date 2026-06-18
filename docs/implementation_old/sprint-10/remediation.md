# Remediation Log - Sprint 10

## Known Technical Debt

### WP-3: Postgres Integration Testing
- **Description**: The `test_postgres_repository_contract` in `tests/karsa/allocation/infrastructure/storage/test_allocation_repository.py` relies on `testcontainers` to spin up a physical PostgreSQL 15 database instance to verify raw SQL syntax and `JSONB` serialization paths.
- **Cause**: The local development environment lacks a running Docker daemon/socket, causing `PostgresContainer` initialization to fail (`FileNotFoundError`).
- **Remediation Plan**: Ensure that a PostgreSQL service or Docker engine is available in the CI pipeline. The tests are written and structurally sound, but require environment support to execute without being marked as `SKIPPED`. Until then, Postgres testing is confined to syntax checking rather than physical execution.