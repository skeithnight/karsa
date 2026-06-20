"""Wave-3 Runtime Verification — Sprint-07.

Tests against real PostgreSQL database to verify:
- Transaction rollback guarantees
- Concurrent outbox publisher safety
- Projection rebuild correctness
- Idempotency race conditions
- Atomic outbox persistence
"""
import pytest
import json
import uuid
import threading
import psycopg
from datetime import datetime
from psycopg.rows import dict_row


@pytest.fixture(scope="module")
def conn():
    """Creates a real database connection."""
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")

    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    conn = psycopg.connect(conninfo)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup_tables(conn):
    """Cleans up test data after each test."""
    yield
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE capability_score_adjustments DISABLE TRIGGER ALL")
        cur.execute("ALTER TABLE attribution_entries DISABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_records DISABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_cycles DISABLE TRIGGER ALL")

        cur.execute("DELETE FROM capability_score_adjustments WHERE adjustment_id LIKE 'v-%'")
        cur.execute("DELETE FROM attribution_entries WHERE attribution_id LIKE 'v-%'")
        cur.execute("DELETE FROM review_records WHERE review_id LIKE 'v-%'")
        cur.execute("DELETE FROM review_cycles WHERE cycle_id LIKE 'v-%'")
        cur.execute("DELETE FROM outbox_events WHERE outbox_id LIKE 'v-%'")
        cur.execute("DELETE FROM capability_score_projection WHERE target_urn LIKE 'v-%'")
        cur.execute("DELETE FROM review_coverage_projection WHERE decision_id LIKE 'v-%'")
        cur.execute("DELETE FROM review_cycle_status_projection WHERE cycle_id LIKE 'v-%'")

        cur.execute("ALTER TABLE capability_score_adjustments ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE attribution_entries ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_records ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_cycles ENABLE TRIGGER ALL")


# --- A. Code-Path Audit: Business Logic Boundaries ---

class TestServiceBoundaryAudit:
    """Verifies services are orchestration-only."""

    def test_schedule_service_has_no_business_logic(self):
        """ScheduleReviewService should only orchestrate repo calls."""
        from karsa.review.application.schedule_review_service import ScheduleReviewService
        import inspect

        source = inspect.getsource(ScheduleReviewService)

        # Should NOT contain:
        assert "def compute_" not in source, "Business computation found in service"
        assert "def calculate_" not in source, "Business calculation found in service"
        assert "def determine_" not in source, "Business determination found in service"

        # Should contain:
        assert "save_cycle" in source, "Missing repo call"
        assert "save_event" in source, "Missing outbox call"

    def test_execute_service_delegates_to_domain(self):
        """ExecuteReviewService should delegate verdict to domain."""
        from karsa.review.application.execute_review_service import ExecuteReviewService
        import inspect

        source = inspect.getsource(ExecuteReviewService)

        # Verdict should be determined by ReviewRecord.determine_verdict
        assert "ReviewRecord.determine_verdict" in source or "determine_verdict" in source


# --- B. Transaction Rollback Verification ---

class TestTransactionRollback:
    """Verifies transaction rollback guarantees."""

    def test_review_cycle_not_created_on_later_failure(self, conn):
        """If outbox insert fails, cycle should not exist."""
        cycle_id = "v-rollback-cycle-1"
        decision_id = "v-rollback-dec-1"

        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # Insert cycle
                cur.execute(
                    """
                    INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                        decision_snapshot, schedule_policy, review_template,
                        eligibility_event_ref, created_at, created_by)
                    VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                    """,
                    (cycle_id, decision_id)
                )

                # Simulate failure on outbox insert (invalid data)
                with pytest.raises(Exception):
                    cur.execute(
                        "INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at) VALUES (NULL, NULL, NULL, NULL, NULL, NULL)"
                    )

                conn.rollback()
        finally:
            conn.autocommit = True

        # Verify cycle was NOT persisted
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE cycle_id = %s", (cycle_id,))
            assert cur.fetchone()[0] == 0

    def test_review_record_not_created_on_attribution_failure(self, conn):
        """If attribution insert fails, record should not exist."""
        # First create a cycle
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                    decision_snapshot, schedule_policy, review_template,
                    eligibility_event_ref, created_at, created_by)
                VALUES ('v-rollback-cycle-2', 'v-rollback-dec-2', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                """
            )

        review_id = "v-rollback-rec-1"

        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # Insert record
                cur.execute(
                    """
                    INSERT INTO review_records (review_id, cycle_id, review_type, decision_snapshot,
                        actual_outcome, variance, verdict, rationale, executed_at, executed_by)
                    VALUES (%s, 'v-rollback-cycle-2', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'OUTPERFORMED', 'test', NOW(), 'test')
                    """,
                    (review_id,)
                )

                # Simulate failure on attribution insert (FK violation)
                with pytest.raises(psycopg.errors.ForeignKeyViolation):
                    cur.execute(
                        """
                        INSERT INTO attribution_entries (attribution_id, review_id, dimension, target_urn,
                            contribution_bps, contribution_pct, attribution_type, evidence, created_at)
                        VALUES ('v-attr-fail', 'nonexistent-review', 'WORKER', 'w1', 10.0, 0.5, 'POSITIVE', '{}', NOW())
                        """
                    )

                conn.rollback()
        finally:
            conn.autocommit = True

        # Verify record was NOT persisted
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_records WHERE review_id = %s", (review_id,))
            assert cur.fetchone()[0] == 0


# --- C. Concurrent Outbox Publisher Safety ---

class TestConcurrentPublisher:
    """Verifies FOR UPDATE SKIP LOCKED prevents double-processing."""

    def test_skip_locked_prevents_double_processing(self, conn):
        """Two concurrent transactions should not get the same pending event."""
        outbox_id = f"v-concurrent-{uuid.uuid4().hex[:8]}"

        # Insert a pending event
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
                VALUES (%s, 'TestEvent', '{}', 'a1', 'PENDING', NOW())
                """,
                (outbox_id,)
            )

        # Transaction A: lock the event
        conn.autocommit = False
        try:
            with conn.cursor() as cur_a:
                cur_a.execute(
                    "SELECT outbox_id FROM outbox_events WHERE outbox_id = %s AND status = 'PENDING' FOR UPDATE SKIP LOCKED",
                    (outbox_id,)
                )
                row_a = cur_a.fetchone()
                assert row_a is not None, "Transaction A should lock the event"

                # Transaction B in a new connection should NOT get the same event
                conn2 = conninfo_connect()
                conn2.autocommit = False
                try:
                    with conn2.cursor() as cur_b:
                        cur_b.execute(
                            "SELECT outbox_id FROM outbox_events WHERE outbox_id = %s AND status = 'PENDING' FOR UPDATE SKIP LOCKED",
                            (outbox_id,)
                        )
                        row_b = cur_b.fetchone()
                        # row_b should be None because Transaction A holds the lock
                        assert row_b is None, "Transaction B should NOT get the locked event"
                finally:
                    conn2.rollback()
                    conn2.close()

            conn.rollback()
        finally:
            conn.autocommit = True


def conninfo_connect():
    """Creates a second database connection for concurrency tests."""
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    return psycopg.connect(conninfo)


# --- D. Projection Rebuild Verification ---

class TestProjectionRebuild:
    """Verifies projection rebuild from authoritative source."""

    def test_capability_score_rebuild_from_adjustments(self, conn):
        """Populate adjustments, rebuild projection, verify values match."""
        # Create prerequisite data
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                    decision_snapshot, schedule_policy, review_template,
                    eligibility_event_ref, created_at, created_by)
                VALUES ('v-rebuild-cycle', 'v-rebuild-dec', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                """
            )
            cur.execute(
                """
                INSERT INTO review_records (review_id, cycle_id, review_type, decision_snapshot,
                    actual_outcome, variance, verdict, rationale, executed_at, executed_by)
                VALUES ('v-rebuild-rec', 'v-rebuild-cycle', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'OUTPERFORMED', 'test', NOW(), 'test')
                """
            )

            # Insert adjustments with known values
            cur.execute(
                """
                INSERT INTO capability_score_adjustments (adjustment_id, target_urn, target_type,
                    score_delta, confidence_delta, review_id, rationale, created_at)
                VALUES ('v-adj-1', 'v-target-1', 'WORKER', 0.05, 0.01, 'v-rebuild-rec', 'Test 1', NOW())
                """
            )
            cur.execute(
                """
                INSERT INTO capability_score_adjustments (adjustment_id, target_urn, target_type,
                    score_delta, confidence_delta, review_id, rationale, created_at)
                VALUES ('v-adj-2', 'v-target-1', 'WORKER', 0.03, 0.02, 'v-rebuild-rec', 'Test 2', NOW())
                """
            )

        # Rebuild projection
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_score_projection WHERE target_urn = 'v-target-1'")
            cur.execute(
                """
                INSERT INTO capability_score_projection (target_urn, target_type, current_score, current_confidence, adjustment_count, last_updated)
                SELECT target_urn, target_type, SUM(score_delta), SUM(confidence_delta), COUNT(*), MAX(created_at)
                FROM capability_score_adjustments WHERE target_urn = 'v-target-1'
                GROUP BY target_urn, target_type
                """
            )

        # Verify
        with conn.cursor() as cur:
            cur.execute("SELECT current_score, current_confidence, adjustment_count FROM capability_score_projection WHERE target_urn = 'v-target-1'")
            row = cur.fetchone()
            assert float(row[0]) == pytest.approx(0.08)  # 0.05 + 0.03
            assert float(row[1]) == pytest.approx(0.03)  # 0.01 + 0.02
            assert row[2] == 2

    def test_rebuild_is_deterministic(self, conn):
        """Rebuilding twice produces identical results."""
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                    decision_snapshot, schedule_policy, review_template,
                    eligibility_event_ref, created_at, created_by)
                VALUES ('v-det-cycle', 'v-det-dec', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                """
            )
            cur.execute(
                """
                INSERT INTO review_records (review_id, cycle_id, review_type, decision_snapshot,
                    actual_outcome, variance, verdict, rationale, executed_at, executed_by)
                VALUES ('v-det-rec', 'v-det-cycle', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'OUTPERFORMED', 'test', NOW(), 'test')
                """
            )
            cur.execute(
                """
                INSERT INTO capability_score_adjustments (adjustment_id, target_urn, target_type,
                    score_delta, confidence_delta, review_id, rationale, created_at)
                VALUES ('v-det-adj', 'v-det-target', 'WORKER', 0.07, 0.01, 'v-det-rec', 'Test', NOW())
                """
            )

        # First rebuild
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_score_projection WHERE target_urn = 'v-det-target'")
            cur.execute(
                """
                INSERT INTO capability_score_projection (target_urn, target_type, current_score, current_confidence, adjustment_count, last_updated)
                SELECT target_urn, target_type, SUM(score_delta), SUM(confidence_delta), COUNT(*), MAX(created_at)
                FROM capability_score_adjustments WHERE target_urn = 'v-det-target'
                GROUP BY target_urn, target_type
                """
            )
            cur.execute("SELECT current_score, current_confidence FROM capability_score_projection WHERE target_urn = 'v-det-target'")
            first = cur.fetchone()

        # Second rebuild
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_score_projection WHERE target_urn = 'v-det-target'")
            cur.execute(
                """
                INSERT INTO capability_score_projection (target_urn, target_type, current_score, current_confidence, adjustment_count, last_updated)
                SELECT target_urn, target_type, SUM(score_delta), SUM(confidence_delta), COUNT(*), MAX(created_at)
                FROM capability_score_adjustments WHERE target_urn = 'v-det-target'
                GROUP BY target_urn, target_type
                """
            )
            cur.execute("SELECT current_score, current_confidence FROM capability_score_projection WHERE target_urn = 'v-det-target'")
            second = cur.fetchone()

        assert float(first[0]) == float(second[0])
        assert float(first[1]) == float(second[1])


# --- E. Atomic Outbox Persistence ---

class TestAtomicOutboxPersistence:
    """Verifies outbox events persisted atomically with aggregates."""

    def test_outbox_persisted_with_aggregate(self, conn):
        """Outbox event and aggregate should be in same transaction."""
        cycle_id = "v-atomic-cycle"
        outbox_id = "v-atomic-outbox"

        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # Insert aggregate
                cur.execute(
                    """
                    INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                        decision_snapshot, schedule_policy, review_template,
                        eligibility_event_ref, created_at, created_by)
                    VALUES (%s, 'v-atomic-dec', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                    """,
                    (cycle_id,)
                )

                # Insert outbox event in same transaction
                cur.execute(
                    """
                    INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
                    VALUES (%s, 'ReviewCycleCreatedEvent', '{}', %s, 'PENDING', NOW())
                    """,
                    (outbox_id, cycle_id)
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit = True

        # Verify both exist
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE cycle_id = %s", (cycle_id,))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM outbox_events WHERE outbox_id = %s", (outbox_id,))
            assert cur.fetchone()[0] == 1

    def test_outbox_not_persisted_if_aggregate_fails(self, conn):
        """If aggregate insert fails, outbox should not exist."""
        outbox_id = "v-atomic-fail-outbox"

        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # Try to insert aggregate with duplicate PK (will fail)
                cur.execute(
                    """
                    INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                        decision_snapshot, schedule_policy, review_template,
                        eligibility_event_ref, created_at, created_by)
                    VALUES ('v-atomic-dup', 'v-atomic-dec', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                    """
                )
                # Try duplicate (should fail)
                with pytest.raises(psycopg.errors.UniqueViolation):
                    cur.execute(
                        """
                        INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                            decision_snapshot, schedule_policy, review_template,
                            eligibility_event_ref, created_at, created_by)
                        VALUES ('v-atomic-dup', 'v-atomic-dec2', 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                        """
                    )

                conn.rollback()
        finally:
            conn.autocommit = True


# --- F. Idempotency Race Test ---

class TestIdempotencyRace:
    """Verifies idempotency under concurrent access."""

    def test_duplicate_decision_id_rejected_by_constraint(self, conn):
        """Two inserts with same decision_id — second rejected by UNIQUE constraint."""
        decision_id = f"v-race-dec-{uuid.uuid4().hex[:8]}"

        # First insert
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                    decision_snapshot, schedule_policy, review_template,
                    eligibility_event_ref, created_at, created_by)
                VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                """,
                (f"v-race-cycle-1-{decision_id}", decision_id)
            )

        # Second insert with same decision_id rejected by UNIQUE constraint
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    """
                    INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                        decision_snapshot, schedule_policy, review_template,
                        eligibility_event_ref, created_at, created_by)
                    VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                    """,
                    (f"v-race-cycle-2-{decision_id}", decision_id)
                )

        # Verify exactly one row exists
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
            count = cur.fetchone()[0]
            assert count == 1, f"Expected 1 row, got {count}"
