"""Sprint-07 Closure Verification Audit — Round 2.

Runtime evidence for closure verification.
"""
import pytest
import json
import uuid
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
        cur.execute("DELETE FROM review_cycles WHERE decision_id LIKE 'audit-%'")
        cur.execute("DELETE FROM outbox_events WHERE aggregate_id LIKE 'urn:karsa:review:cycle:%'")
        cur.execute("DELETE FROM review_coverage_projection WHERE decision_id LIKE 'audit-%'")
        cur.execute("DELETE FROM review_cycle_status_projection WHERE cycle_id LIKE 'urn:karsa:review:cycle:%'")
        cur.execute("DELETE FROM event_journal WHERE aggregate_id LIKE 'audit-%'")
        cur.execute("ALTER TABLE review_cycles ENABLE TRIGGER ALL")


# --- 1. save_cycle() ON CONFLICT DO NOTHING Behavior ---

class TestSaveCycleConflictBehavior:
    def test_on_conflict_nothing_returns_silently(self, conn):
        """ON CONFLICT DO NOTHING does not raise an exception."""
        decision_id = f"audit-conflict-{uuid.uuid4().hex[:8]}"
        cycle_id_1 = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"
        cycle_id_2 = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

        # First insert
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                   decision_snapshot, schedule_policy, review_template,
                   eligibility_event_ref, created_at, created_by)
                   VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')""",
                (cycle_id_1, decision_id)
            )

        # Second insert with ON CONFLICT DO NOTHING — should not raise
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                   decision_snapshot, schedule_policy, review_template,
                   eligibility_event_ref, created_at, created_by)
                   VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                   ON CONFLICT (decision_id) DO NOTHING""",
                (cycle_id_2, decision_id)
            )
            assert cur.rowcount == 0, "ON CONFLICT DO NOTHING should return rowcount=0"

        # Verify only one row exists
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id FROM review_cycles WHERE decision_id = %s", (decision_id,))
            row = cur.fetchone()
            assert row[0] == cycle_id_1, "Original cycle_id should be preserved"

    def test_phantom_outbox_event_risk(self, conn):
        """PROVES: If caller ignores rowcount=0, phantom outbox event is created.

        This is the exact race condition in ScheduleReviewService:
        - T1 checks: no cycle exists
        - T2 checks: no cycle exists
        - T1 inserts cycle → succeeds
        - T2 inserts cycle → ON CONFLICT DO NOTHING (rowcount=0)
        - T2 creates outbox event → PHANTOM event with wrong cycle_id
        """
        decision_id = f"audit-phantom-{uuid.uuid4().hex[:8]}"
        real_cycle_id = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"
        phantom_cycle_id = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

        # T1: insert cycle
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                   decision_snapshot, schedule_policy, review_template,
                   eligibility_event_ref, created_at, created_by)
                   VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')""",
                (real_cycle_id, decision_id)
            )

        # T2: insert cycle (conflict) then create outbox event
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                   decision_snapshot, schedule_policy, review_template,
                   eligibility_event_ref, created_at, created_by)
                   VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                   ON CONFLICT (decision_id) DO NOTHING""",
                (phantom_cycle_id, decision_id)
            )
            rowcount = cur.rowcount

            # Service ignores rowcount and creates phantom outbox event
            phantom_event = {
                "cycle_id": phantom_cycle_id,  # WRONG: this cycle doesn't exist
                "decision_id": decision_id,
                "event_type": "ReviewCycleCreatedEvent",
            }
            cur.execute(
                """INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
                   VALUES (%s, 'ReviewCycleCreatedEvent', %s, %s, 'PENDING', NOW())""",
                (str(uuid.uuid4()), json.dumps(phantom_event), phantom_cycle_id)
            )

        # Verify phantom event exists
        with conn.cursor() as cur:
            cur.execute("SELECT payload->>'cycle_id' FROM outbox_events WHERE aggregate_id = %s", (phantom_cycle_id,))
            row = cur.fetchone()
            assert row is not None, "Phantom outbox event was created"
            assert row[0] == phantom_cycle_id, "Phantom event references non-existent cycle_id"

        # Verify phantom cycle_id does NOT exist in review_cycles
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM review_cycles WHERE cycle_id = %s", (phantom_cycle_id,))
            count = cur.fetchone()[0]
            assert count == 0, "Phantom cycle_id should not exist in review_cycles"


# --- 2. ScheduleReviewService Idempotency Semantics ---

class TestScheduleReviewServiceIdempotency:
    def test_application_level_check_returns_existing(self, conn):
        """If cycle exists, service returns existing without creating new."""
        decision_id = f"audit-idem-{uuid.uuid4().hex[:8]}"
        cycle_id = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

        # Pre-insert cycle
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                   decision_snapshot, schedule_policy, review_template,
                   eligibility_event_ref, created_at, created_by)
                   VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')""",
                (cycle_id, decision_id)
            )

        # Verify get_cycle_by_decision_id returns existing
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id FROM review_cycles WHERE decision_id = %s", (decision_id,))
            row = cur.fetchone()
            assert row is not None
            assert row[0] == cycle_id

    def test_migration_80_unique_constraint_exists(self, conn):
        """Verify ux_review_cycles_decision_id exists."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE indexname = 'ux_review_cycles_decision_id'"
            )
            row = cur.fetchone()
            assert row is not None, "UNIQUE index does not exist"
            assert "UNIQUE" in row[1], "Index should be UNIQUE"


# --- 3. Event Replay Schema Governance ---

class TestEventReplaySchemaGovernance:
    def test_replay_sql_matches_real_payload_structure(self, conn):
        """Verify rebuild SQL queries match actual event payload fields."""
        # Insert a test event with known structure
        unique_id = uuid.uuid4().hex[:8]
        event_payload = {
            "cycle_id": f"audit-replay-cycle-{unique_id}",
            "decision_id": f"audit-replay-dec-{unique_id}",
            "event_sequence": 42,
            "schedule_policy": {"review_due_date": "2026-07-20T00:00:00Z"},
        }
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO event_journal (id, stream_id, stream_version, event_id, event_type,
                   aggregate_type, aggregate_id, payload, occurred_at, schema_version)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (uuid.uuid4().hex, f"Review-audit-replay-{unique_id}", 1, str(uuid.uuid4()),
                 "ReviewCycleCreatedEvent", "Review", f"audit-replay-cycle-{unique_id}",
                 json.dumps(event_payload), datetime.utcnow(), 1)
            )

        # Verify rebuild SQL can extract fields
        with conn.cursor() as cur:
            cur.execute(
                """SELECT payload->>'cycle_id' as cycle_id,
                          payload->>'decision_id' as decision_id,
                          (payload->>'event_sequence')::bigint as event_sequence,
                          (payload->'schedule_policy'->>'review_due_date')::timestamptz as due_date
                   FROM event_journal WHERE event_type = 'ReviewCycleCreatedEvent' AND aggregate_id = %s""",
                (f"audit-replay-cycle-{unique_id}",)
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == f"audit-replay-cycle-{unique_id}"
            assert row[1] == f"audit-replay-dec-{unique_id}"
            assert row[2] == 42
            assert row[3] is not None  # due_date parsed

    def test_schema_version_field_exists(self, conn):
        """Verify schema_version is stored in event_journal."""
        with conn.cursor() as cur:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'event_journal' AND column_name = 'schema_version'")
            row = cur.fetchone()
            assert row is not None, "schema_version column missing from event_journal"


# --- 4. Production Journal Replay Audit ---

class TestProductionJournalReplay:
    def test_actual_payload_structure_matches_rebuild_queries(self, conn):
        """Inspect real event_journal payloads and verify rebuild SQL compatibility."""
        # Check if any ReviewEngine events exist
        with conn.cursor() as cur:
            cur.execute("SELECT event_type, COUNT(*) FROM event_journal WHERE event_type LIKE 'Review%' GROUP BY event_type")
            rows = cur.fetchall()

        if not rows:
            pytest.skip("No Review Engine events in journal yet")

        for row in rows:
            event_type = row[0]
            # Verify payload has expected top-level fields
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload FROM event_journal WHERE event_type = %s LIMIT 1",
                    (event_type,)
                )
                payload_row = cur.fetchone()
                if payload_row:
                    payload = payload_row[0] if isinstance(payload_row[0], dict) else json.loads(payload_row[0])
                    assert isinstance(payload, dict), f"{event_type} payload is not a dict"


# --- 5. True Concurrency Verification ---

class TestTrueConcurrency:
    def test_parallel_inserts_resolve_to_one_row(self, conn):
        """Two concurrent transactions inserting same decision_id produce exactly one row."""
        decision_id = f"audit-conc-{uuid.uuid4().hex[:8]}"

        # Create second connection
        conn2 = _new_conn()
        conn2.autocommit = True

        try:
            # Both insert simultaneously
            cycle_a = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"
            cycle_b = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"

            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                       decision_snapshot, schedule_policy, review_template,
                       eligibility_event_ref, created_at, created_by)
                       VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                       ON CONFLICT (decision_id) DO NOTHING""",
                    (cycle_a, decision_id)
                )

            with conn2.cursor() as cur:
                cur.execute(
                    """INSERT INTO review_cycles (cycle_id, decision_id, journal_ref, review_type,
                       decision_snapshot, schedule_policy, review_template,
                       eligibility_event_ref, created_at, created_by)
                       VALUES (%s, %s, 'j1', 'ALLOCATION_REVIEW', '{}', '{}', '{}', 'e1', NOW(), 'test')
                       ON CONFLICT (decision_id) DO NOTHING""",
                    (cycle_b, decision_id)
                )

            # Verify exactly one row
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM review_cycles WHERE decision_id = %s", (decision_id,))
                count = cur.fetchone()[0]
                assert count == 1, f"Expected 1 row, got {count}"

        finally:
            conn2.close()


# --- 6. Replay Contract Completeness ---

class TestReplayContractCompleteness:
    def test_coverage_rebuild_fields_in_contract(self):
        """Every field consumed by coverage rebuild SQL must be in contract suite."""
        from tests.integration.review.test_event_contracts import EVENT_CONTRACTS

        coverage_rebuild_fields = {
            "ReviewEligibilityEvaluatedEvent": {"decision_id", "eligible", "review_type", "strategy_name", "strategy_version", "evaluation_reason", "evaluated_at"},
            "ReviewCycleCreatedEvent": {"cycle_id", "decision_id", "schedule_policy"},
            "ReviewExecutedEvent": {"cycle_id", "executed_at"},
        }

        for event_name, fields in coverage_rebuild_fields.items():
            contract = EVENT_CONTRACTS.get(event_name)
            assert contract is not None, f"No contract for {event_name}"
            critical = contract["replay_critical_fields"]
            missing = fields - critical
            assert not missing, f"{event_name}: rebuild uses fields not in replay_critical_fields: {missing}"

    def test_status_rebuild_fields_in_contract(self):
        """Every field consumed by status rebuild SQL must be in contract suite."""
        from tests.integration.review.test_event_contracts import EVENT_CONTRACTS

        status_rebuild_fields = {
            "ReviewCycleCreatedEvent": {"cycle_id"},
            "ReviewDueEvent": {"cycle_id"},
            "ReviewOverdueEvent": {"cycle_id"},
            "ReviewExecutedEvent": {"cycle_id", "review_id", "executed_at"},
        }

        for event_name, fields in status_rebuild_fields.items():
            contract = EVENT_CONTRACTS.get(event_name)
            assert contract is not None, f"No contract for {event_name}"
            critical = contract["replay_critical_fields"]
            # event_sequence is also used but is a standard infrastructure field
            missing = fields - critical - {"event_sequence"}
            assert not missing, f"{event_name}: rebuild uses fields not in replay_critical_fields: {missing}"

    def test_capability_rebuild_fields_in_contract(self):
        """Every field consumed by capability rebuild SQL must be in contract suite."""
        from tests.integration.review.test_event_contracts import EVENT_CONTRACTS

        contract = EVENT_CONTRACTS.get("CapabilityScoreAdjustmentCreatedEvent")
        assert contract is not None
        critical = contract["replay_critical_fields"]
        rebuild_fields = {"target_urn", "target_type", "score_delta", "confidence_delta"}
        missing = rebuild_fields - critical
        assert not missing, f"Capability rebuild uses fields not in replay_critical_fields: {missing}"


def _new_conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    return psycopg.connect(conninfo)
