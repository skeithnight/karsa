# Event Store Validation Cleanup

## 1. Current Issues
The `test_event_journal_foundation.py` file introduced a fake `event_journal` schema by directly executing a `CREATE TABLE` statement within the test fixture. This bypassed the actual Alembic migrations, failing to prove that the real Event Store implementation was correct or replay-ready.

## 2. Removed Logic
The temporary `CREATE TABLE IF NOT EXISTS event_journal` and `DROP TABLE IF EXISTS event_journal` blocks have been completely removed from the `db_conn` fixture.

## 3. Real Validation Strategy
The test now expects the database to be pre-migrated via Alembic. It will insert natively into the schema produced by `alembic/versions/49_wave1_remediation.py`. This proves that the `sequence_id` primary key and the `stream_id` + `stream_version` unique constraints actually exist and function as expected.

## 4. Required Runtime Environment
Because the integration tests now require a fully initialized real database, and because we have strictly forbidden exposing the database ports to the host via `docker-compose.yml`, these tests must be run *inside* the backend container:
`docker-compose exec karsa-api uv run pytest tests/integration/test_event_journal_foundation.py`

## 5. Acceptance Criteria
*   Test does not create or destroy database schemas.
*   Test validates ordering and constraints against the actual Alembic tables.
*   `EVENT_STORE_VALIDATION_REMEDIATED` is achieved.
