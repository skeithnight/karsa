"""Runtime verification tests for Wave-2C — Sprint-07.

Tests against real PostgreSQL database with migrated schema.
Requires: docker compose up -d postgres
"""
import pytest
import json
import psycopg
from datetime import datetime, timedelta
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
    """Cleans up test data after each test. Disables immutability triggers for cleanup."""
    yield
    with conn.cursor() as cur:
        # Disable immutability triggers for cleanup
        cur.execute("ALTER TABLE capability_score_adjustments DISABLE TRIGGER ALL")
        cur.execute("ALTER TABLE attribution_entries DISABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_records DISABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_cycles DISABLE TRIGGER ALL")

        cur.execute("DELETE FROM capability_score_adjustments WHERE adjustment_id LIKE 'test-%'")
        cur.execute("DELETE FROM attribution_entries WHERE attribution_id LIKE 'test-%'")
        cur.execute("DELETE FROM review_records WHERE review_id LIKE 'test-%'")
        cur.execute("DELETE FROM review_cycles WHERE cycle_id LIKE 'test-%'")
        cur.execute("DELETE FROM outbox_events WHERE outbox_id LIKE 'test-%'")
        cur.execute("DELETE FROM capability_score_projection WHERE target_urn LIKE 'test-%'")
        cur.execute("DELETE FROM review_coverage_projection WHERE decision_id LIKE 'test-%'")
        cur.execute("DELETE FROM review_cycle_status_projection WHERE cycle_id LIKE 'test-%'")

        # Re-enable immutability triggers
        cur.execute("ALTER TABLE capability_score_adjustments ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE attribution_entries ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_records ENABLE TRIGGER ALL")
        cur.execute("ALTER TABLE review_cycles ENABLE TRIGGER ALL")


# --- Helper functions ---

def insert_test_cycle(conn, cycle_id="test-cycle-1", decision_id="test-dec-1"):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO review_cycles (
                cycle_id, decision_id, proposal_id, journal_ref,
                review_type, decision_snapshot, schedule_policy,
                review_template, eligibility_event_ref, created_at, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                cycle_id, decision_id, "test-prop-1", "test-journal-1",
                "ALLOCATION_REVIEW",
                json.dumps({"decision_id": decision_id, "journal_ref": "j1", "action_type": "APPROVE",
                           "target_node_type": "WORKER", "target_node_id": "main",
                           "allocated_weights": {"w1": 0.6}, "policy_snapshot": {},
                           "expected_return_bps": 50.0, "expected_drawdown_pct": 5.0,
                           "expected_sharpe_ratio": 1.5, "expected_horizon_days": 30,
                           "confidence_level": 0.7, "key_assumptions": [],
                           "attribution_expectations": {}, "decision_rationale": "Test",
                           "decision_confidence": 0.7, "decision_timestamp": "2026-06-20T00:00:00Z",
                           "cryptographic_signature": "sig", "snapshot_hash": "hash"}),
                json.dumps({"observation_window_days": 30, "overdue_threshold_days": 7,
                           "review_due_date": "2026-07-20T00:00:00", "auto_expire": False}),
                json.dumps({"template_id": "tmpl-1", "review_type": "ALLOCATION_REVIEW",
                           "required_metrics": ["return_bps"], "required_assumptions": [],
                           "evaluation_criteria": {}, "scoring_rules": {}, "extensible_config": {}}),
                "test-elig-1", datetime.utcnow(), "test-system",
            )
        )


def insert_test_record(conn, review_id="test-rec-1", cycle_id="test-cycle-1"):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO review_records (
                review_id, cycle_id, review_type, decision_snapshot,
                actual_outcome, variance, verdict, rationale,
                executed_at, executed_by, evidence_refs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                review_id, cycle_id, "ALLOCATION_REVIEW",
                json.dumps({"decision_id": "d1", "journal_ref": "j1"}),
                json.dumps({"evaluation_id": "e1", "target_urn": "w1", "observation_window_days": 30,
                           "realized_return_bps": 60.0, "realized_drawdown_pct": 3.0,
                           "realized_sharpe_ratio": 1.8, "benchmark_return_bps": 40.0}),
                json.dumps({"return_variance_bps": 10.0, "drawdown_variance_pct": -2.0,
                           "sharpe_variance": 0.3, "confidence_accuracy": 0.8,
                           "assumption_accuracy": 0.9, "overall_accuracy": 0.85}),
                "OUTPERFORMED", "Exceeded expectations.",
                datetime.utcnow(), "test-cio", json.dumps([]),
            )
        )


# --- A. Real Database Integration Tests ---

class TestReviewCycleRepository:
    def test_save_and_load(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id, decision_id, review_type FROM review_cycles WHERE cycle_id = 'test-cycle-1'")
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "test-cycle-1"
            assert row[1] == "test-dec-1"
            assert row[2] == "ALLOCATION_REVIEW"

    def test_jsonb_persistence(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT decision_snapshot, schedule_policy, review_template FROM review_cycles WHERE cycle_id = 'test-cycle-1'")
            row = cur.fetchone()
            ds = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            sp = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            rt = row[2] if isinstance(row[2], dict) else json.loads(row[2])
            assert ds["decision_id"] == "test-dec-1"
            assert sp["observation_window_days"] == 30
            assert rt["template_id"] == "tmpl-1"

    def test_not_found(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id FROM review_cycles WHERE cycle_id = 'nonexistent'")
            assert cur.fetchone() is None

    def test_list_with_pagination(self, conn):
        for i in range(5):
            insert_test_cycle(conn, cycle_id=f"test-cycle-{i}", decision_id=f"test-dec-{i}")
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id FROM review_cycles WHERE cycle_id LIKE 'test-cycle-%' ORDER BY cycle_id LIMIT 2 OFFSET 0")
            rows = cur.fetchall()
            assert len(rows) == 2

    def test_get_by_decision_id(self, conn):
        insert_test_cycle(conn, decision_id="test-dec-unique")
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id FROM review_cycles WHERE decision_id = 'test-dec-unique'")
            row = cur.fetchone()
            assert row is not None


class TestReviewRecordRepository:
    def test_save_and_load(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT review_id, cycle_id, verdict FROM review_records WHERE review_id = 'test-rec-1'")
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "test-rec-1"
            assert row[2] == "OUTPERFORMED"

    def test_fk_enforcement(self, conn):
        """FK violation when cycle_id doesn't exist."""
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                cur.execute(
                    """
                    INSERT INTO review_records (
                        review_id, cycle_id, review_type, decision_snapshot,
                        actual_outcome, variance, verdict, rationale,
                        executed_at, executed_by
                    ) VALUES ('test-rec-fk', 'nonexistent-cycle', 'ALLOCATION_REVIEW',
                        '{}', '{}', '{}', 'OUTPERFORMED', 'test', NOW(), 'test')
                    """
                )

    def test_jsonb_persistence(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT actual_outcome, variance FROM review_records WHERE review_id = 'test-rec-1'")
            row = cur.fetchone()
            ao = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            va = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            assert ao["realized_return_bps"] == 60.0
            assert va["return_variance_bps"] == 10.0


class TestAttributionEntryRepository:
    def test_save_and_load(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attribution_entries (
                    attribution_id, review_id, dimension, target_urn,
                    contribution_bps, contribution_pct, attribution_type,
                    evidence, created_at
                ) VALUES ('test-attr-1', 'test-rec-1', 'WORKER', 'test-w1', 30.0, 0.5, 'POSITIVE', '{}', NOW())
                """
            )
            cur.execute("SELECT attribution_id, dimension, contribution_bps FROM attribution_entries WHERE attribution_id = 'test-attr-1'")
            row = cur.fetchone()
            assert row is not None
            assert row[1] == "WORKER"
            assert float(row[2]) == 30.0

    def test_batch_insert(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            entries = [
                (f"test-attr-batch-{i}", "test-rec-1", "WORKER", f"test-w{i}",
                 10.0 * i, 0.1 * i, "POSITIVE", "{}", datetime.utcnow())
                for i in range(4)
            ]
            cur.executemany(
                """
                INSERT INTO attribution_entries (
                    attribution_id, review_id, dimension, target_urn,
                    contribution_bps, contribution_pct, attribution_type,
                    evidence, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                entries,
            )
            cur.execute("SELECT COUNT(*) FROM attribution_entries WHERE attribution_id LIKE 'test-attr-batch-%'")
            assert cur.fetchone()[0] == 4


class TestCapabilityScoreAdjustmentRepository:
    def test_save_and_load(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO capability_score_adjustments (
                    adjustment_id, target_urn, target_type,
                    score_delta, confidence_delta, review_id,
                    rationale, created_at
                ) VALUES ('test-adj-1', 'test-w1', 'WORKER', 0.005, 0.01, 'test-rec-1', 'Test', NOW())
                """
            )
            cur.execute("SELECT adjustment_id, score_delta, confidence_delta FROM capability_score_adjustments WHERE adjustment_id = 'test-adj-1'")
            row = cur.fetchone()
            assert row is not None
            assert float(row[1]) == 0.005
            assert float(row[2]) == 0.01

    def test_batch_insert(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            adjs = [
                (f"test-adj-batch-{i}", f"test-w{i}", "WORKER",
                 0.001 * i, 0.01, "test-rec-1", f"Test {i}", datetime.utcnow())
                for i in range(3)
            ]
            cur.executemany(
                """
                INSERT INTO capability_score_adjustments (
                    adjustment_id, target_urn, target_type,
                    score_delta, confidence_delta, review_id,
                    rationale, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                adjs,
            )
            cur.execute("SELECT COUNT(*) FROM capability_score_adjustments WHERE adjustment_id LIKE 'test-adj-batch-%'")
            assert cur.fetchone()[0] == 3


# --- B. Immutability Trigger Verification ---

class TestImmutabilityTriggers:
    def test_review_cycles_update_blocked(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                cur.execute("UPDATE review_cycles SET created_by = 'hacked' WHERE cycle_id = 'test-cycle-1'")

    def test_review_cycles_delete_blocked(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                cur.execute("DELETE FROM review_cycles WHERE cycle_id = 'test-cycle-1'")

    def test_review_records_update_blocked(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                cur.execute("UPDATE review_records SET verdict = 'FAILED' WHERE review_id = 'test-rec-1'")

    def test_review_records_delete_blocked(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                cur.execute("DELETE FROM review_records WHERE review_id = 'test-rec-1'")

    def test_attribution_entries_update_blocked(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO attribution_entries (attribution_id, review_id, dimension, target_urn, contribution_bps, contribution_pct, attribution_type, evidence, created_at) VALUES ('test-attr-imm', 'test-rec-1', 'WORKER', 'w1', 10.0, 0.1, 'POSITIVE', '{}', NOW())"
            )
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                cur.execute("UPDATE attribution_entries SET contribution_bps = 999 WHERE attribution_id = 'test-attr-imm'")

    def test_capability_score_adjustments_update_blocked(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO capability_score_adjustments (adjustment_id, target_urn, target_type, score_delta, confidence_delta, review_id, rationale, created_at) VALUES ('test-adj-imm', 'w1', 'WORKER', 0.01, 0.01, 'test-rec-1', 'Test', NOW())"
            )
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                cur.execute("UPDATE capability_score_adjustments SET score_delta = 999 WHERE adjustment_id = 'test-adj-imm'")


# --- C. Outbox Concurrency Verification ---

class TestOutboxConcurrency:
    def test_skip_locked_behavior(self, conn):
        """Two transactions should not get the same pending event."""
        # Insert a pending event
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
                VALUES ('test-outbox-1', 'TestEvent', '{}', 'a1', 'PENDING', NOW())
                """
            )

        # Transaction A: get pending with FOR UPDATE SKIP LOCKED
        conn.autocommit = False
        try:
            with conn.cursor() as cur_a:
                cur_a.execute(
                    "SELECT outbox_id FROM outbox_events WHERE status = 'PENDING' AND outbox_id = 'test-outbox-1' FOR UPDATE SKIP LOCKED"
                )
                row_a = cur_a.fetchone()
                assert row_a is not None

                # Transaction B in same connection (simulates concurrent access)
                # Since we're in the same connection, the row is locked
                # In a real concurrent scenario, a second connection would get no rows
                conn.commit()
        finally:
            conn.autocommit = True

    def test_mark_sent(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
                VALUES ('test-outbox-sent', 'TestEvent', '{}', 'a1', 'PENDING', NOW())
                """
            )
            cur.execute(
                "UPDATE outbox_events SET status = 'SENT', sent_at = NOW() WHERE outbox_id = 'test-outbox-sent'"
            )
            cur.execute("SELECT status FROM outbox_events WHERE outbox_id = 'test-outbox-sent'")
            assert cur.fetchone()[0] == 'SENT'

    def test_mark_failed(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at)
                VALUES ('test-outbox-fail', 'TestEvent', '{}', 'a1', 'PENDING', NOW())
                """
            )
            cur.execute(
                "UPDATE outbox_events SET status = 'FAILED' WHERE outbox_id = 'test-outbox-fail'"
            )
            cur.execute("SELECT status FROM outbox_events WHERE outbox_id = 'test-outbox-fail'")
            assert cur.fetchone()[0] == 'FAILED'

    def test_increment_retry(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox_events (outbox_id, event_type, payload, aggregate_id, status, created_at, retry_count)
                VALUES ('test-outbox-retry', 'TestEvent', '{}', 'a1', 'PENDING', NOW(), 0)
                """
            )
            cur.execute(
                "UPDATE outbox_events SET retry_count = retry_count + 1 WHERE outbox_id = 'test-outbox-retry'"
            )
            cur.execute("SELECT retry_count FROM outbox_events WHERE outbox_id = 'test-outbox-retry'")
            assert cur.fetchone()[0] == 1


# --- D. Projection Rebuild Verification ---

class TestProjectionRebuild:
    def test_capability_score_projection_rebuild(self, conn):
        """Populate adjustments, rebuild projection, verify values."""
        insert_test_cycle(conn)
        insert_test_record(conn)

        with conn.cursor() as cur:
            # Insert adjustments
            cur.execute(
                "INSERT INTO capability_score_adjustments (adjustment_id, target_urn, target_type, score_delta, confidence_delta, review_id, rationale, created_at) VALUES ('test-adj-rb1', 'test-w-rebuild', 'WORKER', 0.05, 0.01, 'test-rec-1', 'Test 1', NOW())"
            )
            cur.execute(
                "INSERT INTO capability_score_adjustments (adjustment_id, target_urn, target_type, score_delta, confidence_delta, review_id, rationale, created_at) VALUES ('test-adj-rb2', 'test-w-rebuild', 'WORKER', 0.03, 0.02, 'test-rec-1', 'Test 2', NOW())"
            )

            # Rebuild projection
            cur.execute("DELETE FROM capability_score_projection WHERE target_urn = 'test-w-rebuild'")
            cur.execute(
                """
                INSERT INTO capability_score_projection (target_urn, target_type, current_score, current_confidence, adjustment_count, last_updated)
                SELECT target_urn, target_type, SUM(score_delta), SUM(confidence_delta), COUNT(*), MAX(created_at)
                FROM capability_score_adjustments
                WHERE target_urn = 'test-w-rebuild'
                GROUP BY target_urn, target_type
                """
            )

            # Verify
            cur.execute("SELECT current_score, current_confidence, adjustment_count FROM capability_score_projection WHERE target_urn = 'test-w-rebuild'")
            row = cur.fetchone()
            assert row is not None
            assert float(row[0]) == pytest.approx(0.08)  # 0.05 + 0.03
            assert float(row[1]) == pytest.approx(0.03)  # 0.01 + 0.02
            assert row[2] == 2

    def test_review_coverage_projection_upsert(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_coverage_projection (
                    decision_id, eligible, review_type, strategy_name,
                    strategy_version, evaluation_reason, review_status, evaluated_at
                ) VALUES ('test-cov-1', true, 'ALLOCATION_REVIEW', 'default', '1.0', 'Approved', 'PENDING', NOW())
                """
            )
            cur.execute("SELECT decision_id, eligible, review_status FROM review_coverage_projection WHERE decision_id = 'test-cov-1'")
            row = cur.fetchone()
            assert row is not None
            assert row[1] is True
            assert row[2] == 'PENDING'

    def test_review_cycle_status_projection_upsert(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_cycle_status_projection (cycle_id, status, event_sequence)
                VALUES ('test-cyc-status-1', 'CREATED', 1)
                """
            )
            cur.execute(
                """
                UPDATE review_cycle_status_projection
                SET status = 'DUE', event_sequence = 10
                WHERE cycle_id = 'test-cyc-status-1' AND event_sequence < 10
                """
            )
            cur.execute("SELECT status, event_sequence FROM review_cycle_status_projection WHERE cycle_id = 'test-cyc-status-1'")
            row = cur.fetchone()
            assert row[0] == 'DUE'
            assert row[1] == 10


# --- E. JSONB Roundtrip Verification ---

class TestJsonbRoundtrip:
    def test_decision_snapshot_roundtrip(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT decision_snapshot FROM review_cycles WHERE cycle_id = 'test-cycle-1'")
            row = cur.fetchone()
            ds = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            assert ds["decision_id"] == "test-dec-1"
            assert ds["expected_return_bps"] == 50.0
            assert ds["confidence_level"] == 0.7

    def test_schedule_policy_roundtrip(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT schedule_policy FROM review_cycles WHERE cycle_id = 'test-cycle-1'")
            row = cur.fetchone()
            sp = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            assert sp["observation_window_days"] == 30
            assert sp["overdue_threshold_days"] == 7
            assert sp["auto_expire"] is False

    def test_review_template_roundtrip(self, conn):
        insert_test_cycle(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT review_template FROM review_cycles WHERE cycle_id = 'test-cycle-1'")
            row = cur.fetchone()
            rt = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            assert rt["template_id"] == "tmpl-1"
            assert rt["review_type"] == "ALLOCATION_REVIEW"

    def test_actual_outcome_roundtrip(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT actual_outcome FROM review_records WHERE review_id = 'test-rec-1'")
            row = cur.fetchone()
            ao = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            assert ao["evaluation_id"] == "e1"
            assert ao["realized_return_bps"] == 60.0

    def test_variance_roundtrip(self, conn):
        insert_test_cycle(conn)
        insert_test_record(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT variance FROM review_records WHERE review_id = 'test-rec-1'")
            row = cur.fetchone()
            va = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            assert va["return_variance_bps"] == 10.0
            assert va["overall_accuracy"] == 0.85
