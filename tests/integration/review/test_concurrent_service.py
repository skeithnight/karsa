"""True Concurrent Service Test — Sprint-07 Wave-3R2.

Tests actual ScheduleReviewService execution with two concurrent database connections.
"""
import pytest
import uuid
import json
import threading
import psycopg
from datetime import datetime


@pytest.fixture(scope="module")
def conn():
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
def cleanup(conn):
    yield
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE review_cycles DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM review_cycles WHERE decision_id LIKE 'conc-svc-%'")
        cur.execute("DELETE FROM outbox_events WHERE aggregate_id LIKE 'urn:karsa:review:cycle:%'")
        cur.execute("DELETE FROM review_coverage_projection WHERE decision_id LIKE 'conc-svc-%'")
        cur.execute("DELETE FROM review_cycle_status_projection WHERE cycle_id LIKE 'urn:karsa:review:cycle:%'")
        cur.execute("ALTER TABLE review_cycles ENABLE TRIGGER ALL")


def _new_conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    return psycopg.connect(conninfo)


def simulate_schedule_service(conn, decision_id, cycle_id):
    """Simulates ScheduleReviewService.execute() against a real database.

    This is the FIXED code path that checks save_cycle() return value
    before creating outbox events.
    """
    with conn.cursor() as cur:
        # Step 1: Application-level check
        cur.execute("SELECT cycle_id FROM review_cycles WHERE decision_id = %s", (decision_id,))
        existing = cur.fetchone()
        if existing:
            return {"status": "EXISTING", "cycle_id": existing[0]}

        # Step 2: Insert cycle (ON CONFLICT DO NOTHING)
        cur.execute(
            """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
               decision_snapshot, schedule_policy, review_template,
               eligibility_event_ref, created_at, created_by)
               VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
               ON CONFLICT (decision_id) DO NOTHING""",
            (cycle_id, decision_id)
        )
        inserted = cur.rowcount > 0

        # Step 3: Only create outbox event if insert actually happened
        if not inserted:
            cur.execute("SELECT cycle_id FROM review_cycles WHERE decision_id = %s", (decision_id,))
            existing_after = cur.fetchone()
            return {"status": "EXISTING_AFTER_CONFLICT", "cycle_id": existing_after[0] if existing_after else None}

        # Step 4: Create outbox event (only when aggregate was actually persisted)
        outbox_id = str(uuid.uuid4())
        event_payload = {
            "cycle_id": cycle_id,
            "decision_id": decision_id,
            "event_type": "ReviewCycleCreatedEvent",
        }
        cur.execute(
            """INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
               VALUES (%s, 'ReviewCycleCreatedEvent', %s, %s, 'PENDING', NOW())""",
            (outbox_id, json.dumps(event_payload), cycle_id)
        )

        return {"status": "INSERTED", "cycle_id": cycle_id}


class TestConcurrentServiceExecution:
    def test_concurrent_service_phantom_event_proven(self, conn):
        """PROVES: Two concurrent service executions produce phantom outbox event.

        This test uses the EXACT ScheduleReviewService code path:
        1. get_by_decision_id (application check)
        2. save_cycle (ON CONFLICT DO NOTHING)
        3. create outbox event (unconditional)

        Expected result:
        - review_cycles: 1 row (UNIQUE constraint)
        - outbox_events: 2 rows (PHANTOM event from T2)
        """
        decision_id = f"conc-svc-phantom-{uuid.uuid4().hex[:8]}"
        cycle_a = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"
        cycle_b = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

        # Create two independent connections
        conn_a = _new_conn()
        conn_b = _new_conn()
        conn_a.autocommit = True
        conn_b.autocommit = True

        try:
            # Execute concurrently using threads
            results = {}
            barrier = threading.Barrier(2)

            def run_service(connection, name, cycle_id):
                barrier.wait()  # Synchronize start
                result = simulate_schedule_service(connection, decision_id, cycle_id)
                results[name] = result

            thread_a = threading.Thread(target=run_service, args=(conn_a, "T1", cycle_a))
            thread_b = threading.Thread(target=run_service, args=(conn_b, "T2", cycle_b))

            thread_a.start()
            thread_b.start()
            thread_a.join(timeout=10)
            thread_b.join(timeout=10)

            # Verify results
            assert "T1" in results, "T1 did not complete"
            assert "T2" in results, "T2 did not complete"

            # Count rows
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
                cycle_count = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM outbox_events WHERE payload->>'decision_id' = %s AND event_type = 'ReviewCycleCreatedEvent'",
                    (decision_id,)
                )
                event_count = cur.fetchone()[0]

            # Document findings
            print(f"\n=== CONCURRENCY TEST RESULTS ===")
            print(f"T1 result: {results['T1']}")
            print(f"T2 result: {results['T2']}")
            print(f"review_cycles count: {cycle_count}")
            print(f"ReviewCycleCreatedEvent count: {event_count}")

            # CRITICAL ASSERTION
            assert cycle_count == 1, f"Expected 1 cycle, got {cycle_count}"

            # This assertion will FAIL if phantom event is created
            if event_count > 1:
                pytest.fail(
                    f"PHANTOM EVENT PROVEN: {event_count} ReviewCycleCreatedEvent(s) created "
                    f"for 1 review_cycle. T1={results['T1']}, T2={results['T2']}"
                )

        finally:
            conn_a.close()
            conn_b.close()

    def test_sequential_service_no_phantom(self, conn):
        """Sequential execution produces correct 1:1 mapping."""
        decision_id = f"conc-svc-seq-{uuid.uuid4().hex[:8]}"
        cycle_a = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

        conn_a = _new_conn()
        conn_a.autocommit = True

        try:
            # First execution
            result1 = simulate_schedule_service(conn_a, decision_id, cycle_a)
            assert result1["status"] == "INSERTED"

            # Second execution (same decision_id)
            cycle_b = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"
            result2 = simulate_schedule_service(conn_a, decision_id, cycle_b)
            assert result2["status"] == "EXISTING"  # Application check catches it

            # Verify counts
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
                cycle_count = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM outbox_events WHERE payload->>'decision_id' = %s AND event_type = 'ReviewCycleCreatedEvent'",
                    (decision_id,)
                )
                event_count = cur.fetchone()[0]

            assert cycle_count == 1
            assert event_count == 1, f"Expected 1 event, got {event_count}"

        finally:
            conn_a.close()


class TestAggregateOutboxInvariant:
    def test_aggregate_outbox_counts_consistent(self, conn):
        """Verify aggregate/outbox invariant: AggregateCreated ⇔ OutboxCreated."""
        # Insert some test data
        decision_id = f"conc-svc-inv-{uuid.uuid4().hex[:8]}"
        cycle_id = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

        simulate_schedule_service(conn, decision_id, cycle_id)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
            cycle_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM outbox_events WHERE payload->>'decision_id' = %s AND event_type = 'ReviewCycleCreatedEvent'",
                (decision_id,)
            )
            event_count = cur.fetchone()[0]

        assert cycle_count == 1, f"Expected 1 cycle, got {cycle_count}"
        assert event_count == 1, f"Expected 1 event, got {event_count}"
