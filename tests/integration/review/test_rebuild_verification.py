"""Rebuild verification tests — Sprint-07 Wave-3R.

Tests rebuild() methods against real PostgreSQL database with event journal.
"""
import pytest
import json
import uuid
import psycopg
from datetime import datetime


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
def cleanup(conn):
    """Cleans up test data after each test."""
    yield
    with conn.cursor() as cur:
        cur.execute("DELETE FROM review_coverage_projection WHERE decision_id LIKE 'rb-%'")
        cur.execute("DELETE FROM review_cycle_status_projection WHERE cycle_id LIKE 'rb-%'")
        cur.execute("DELETE FROM event_journal WHERE aggregate_id LIKE 'rb-%'")


def insert_event(conn, event_type, payload, aggregate_id, sequence_id=None):
    """Inserts a test event into the event journal."""
    with conn.cursor() as cur:
        event_id = str(uuid.uuid4())
        record_id = uuid.uuid4().hex
        stream_id = f"Review-{aggregate_id}"

        # Get next stream version
        cur.execute(
            "SELECT COALESCE(MAX(stream_version), 0) + 1 FROM event_journal WHERE stream_id = %s",
            (stream_id,)
        )
        next_version = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO event_journal (id, stream_id, stream_version, event_id, event_type,
                aggregate_type, aggregate_id, payload, occurred_at, schema_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record_id, stream_id, next_version, event_id, event_type,
                "Review", aggregate_id, json.dumps(payload, default=str), datetime.utcnow(), 1,
            )
        )


# --- ReviewCoverageProjection Rebuild Tests ---

class TestReviewCoverageProjectionRebuild:
    def test_rebuild_from_empty_source(self, conn):
        """Rebuild from no events produces empty projection."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        repo = PostgresReviewCoverageProjectionRepository(conn)
        repo.rebuild()

        results = repo.list_by_status("PENDING")
        assert len(results) == 0

    def test_rebuild_from_single_eligibility_event(self, conn):
        """Single eligible event creates PENDING row."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        insert_event(conn, "ReviewEligibilityEvaluatedEvent", {
            "decision_id": "rb-dec-1",
            "eligible": True,
            "review_type": "ALLOCATION_REVIEW",
            "strategy_name": "default",
            "strategy_version": "1.0",
            "evaluation_reason": "Approved decision",
            "evaluated_at": "2026-06-20T12:00:00Z",
        }, "rb-dec-1")

        repo = PostgresReviewCoverageProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_decision_id("rb-dec-1")
        assert result is not None
        assert result.eligible is True
        assert result.review_status == "PENDING"
        assert result.strategy_name == "default"

    def test_rebuild_from_ineligible_event(self, conn):
        """Ineligible event creates NO_REVIEW row."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        insert_event(conn, "ReviewEligibilityEvaluatedEvent", {
            "decision_id": "rb-dec-2",
            "eligible": False,
            "review_type": None,
            "strategy_name": "default",
            "strategy_version": "1.0",
            "evaluation_reason": "Below threshold",
            "evaluated_at": "2026-06-20T12:00:00Z",
        }, "rb-dec-2")

        repo = PostgresReviewCoverageProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_decision_id("rb-dec-2")
        assert result is not None
        assert result.eligible is False
        assert result.review_status == "NO_REVIEW"

    def test_rebuild_with_cycle_created(self, conn):
        """Eligibility + CycleCreated updates cycle_id and due_date."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        insert_event(conn, "ReviewEligibilityEvaluatedEvent", {
            "decision_id": "rb-dec-3",
            "eligible": True,
            "review_type": "ALLOCATION_REVIEW",
            "strategy_name": "default",
            "strategy_version": "1.0",
            "evaluation_reason": "Approved",
            "evaluated_at": "2026-06-20T12:00:00Z",
        }, "rb-dec-3")

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cycle-3",
            "decision_id": "rb-dec-3",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {"review_due_date": "2026-07-20T00:00:00Z"},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-dec-3")

        repo = PostgresReviewCoverageProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_decision_id("rb-dec-3")
        assert result is not None
        assert result.cycle_id == "rb-cycle-3"
        assert result.review_due_date is not None
        assert result.review_status == "PENDING"

    def test_rebuild_with_executed_event(self, conn):
        """Eligibility + CycleCreated + Executed updates status to EXECUTED."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        insert_event(conn, "ReviewEligibilityEvaluatedEvent", {
            "decision_id": "rb-dec-4",
            "eligible": True,
            "review_type": "ALLOCATION_REVIEW",
            "strategy_name": "default",
            "strategy_version": "1.0",
            "evaluation_reason": "Approved",
            "evaluated_at": "2026-06-20T12:00:00Z",
        }, "rb-dec-4")

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cycle-4",
            "decision_id": "rb-dec-4",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {"review_due_date": "2026-07-20T00:00:00Z"},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-dec-4")

        insert_event(conn, "ReviewExecutedEvent", {
            "review_id": "rb-rec-4",
            "cycle_id": "rb-cycle-4",
            "review_type": "ALLOCATION_REVIEW",
            "actual_outcome": {},
            "variance": {},
            "verdict": "OUTPERFORMED",
            "rationale": "Exceeded expectations",
            "executed_by": "test",
            "executed_at": "2026-06-25T12:00:00Z",
            "event_sequence": 2,
        }, "rb-cycle-4")

        repo = PostgresReviewCoverageProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_decision_id("rb-dec-4")
        assert result is not None
        assert result.review_status == "EXECUTED"
        assert result.executed_at is not None

    def test_rebuild_deterministic(self, conn):
        """Rebuilding twice produces identical results."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        insert_event(conn, "ReviewEligibilityEvaluatedEvent", {
            "decision_id": "rb-dec-det",
            "eligible": True,
            "review_type": "ALLOCATION_REVIEW",
            "strategy_name": "default",
            "strategy_version": "1.0",
            "evaluation_reason": "Approved",
            "evaluated_at": "2026-06-20T12:00:00Z",
        }, "rb-dec-det")

        repo = PostgresReviewCoverageProjectionRepository(conn)

        # First rebuild
        repo.rebuild()
        first = repo.get_by_decision_id("rb-dec-det")

        # Second rebuild
        repo.rebuild()
        second = repo.get_by_decision_id("rb-dec-det")

        assert first.eligible == second.eligible
        assert first.review_status == second.review_status
        assert first.strategy_name == second.strategy_name

    def test_rebuild_idempotent(self, conn):
        """Rebuilding multiple times produces same result."""
        from karsa.review.infrastructure.postgres_review_coverage_projection_repository import PostgresReviewCoverageProjectionRepository

        insert_event(conn, "ReviewEligibilityEvaluatedEvent", {
            "decision_id": "rb-dec-idem",
            "eligible": True,
            "review_type": "ALLOCATION_REVIEW",
            "strategy_name": "default",
            "strategy_version": "1.0",
            "evaluation_reason": "Approved",
            "evaluated_at": "2026-06-20T12:00:00Z",
        }, "rb-dec-idem")

        repo = PostgresReviewCoverageProjectionRepository(conn)

        repo.rebuild()
        repo.rebuild()
        repo.rebuild()

        results = repo.list_by_status("PENDING")
        idem_results = [r for r in results if r.decision_id == "rb-dec-idem"]
        assert len(idem_results) == 1


# --- ReviewCycleStatusProjection Rebuild Tests ---

class TestReviewCycleStatusProjectionRebuild:
    def test_rebuild_from_empty_source(self, conn):
        """Rebuild from no events produces empty projection."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        repo = PostgresReviewCycleStatusProjectionRepository(conn)
        repo.rebuild()

        results = repo.list_by_status("CREATED")
        assert len(results) == 0

    def test_rebuild_from_created_event(self, conn):
        """Single created event creates CREATED row."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cyc-1",
            "decision_id": "rb-dec-1",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-cyc-1")

        repo = PostgresReviewCycleStatusProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_cycle_id("rb-cyc-1")
        assert result is not None
        assert result.status == "CREATED"
        assert result.event_sequence == 1

    def test_rebuild_with_due_event(self, conn):
        """Created + Due updates status to DUE."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cyc-2",
            "decision_id": "rb-dec-2",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-cyc-2")

        insert_event(conn, "ReviewDueEvent", {
            "cycle_id": "rb-cyc-2",
            "review_due_date": "2026-07-20T00:00:00Z",
            "days_until_due": 30,
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 10,
        }, "rb-cyc-2")

        repo = PostgresReviewCycleStatusProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_cycle_id("rb-cyc-2")
        assert result.status == "DUE"
        assert result.event_sequence == 10

    def test_rebuild_with_overdue_event(self, conn):
        """Created + Due + Overdue updates status to OVERDUE."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cyc-3",
            "decision_id": "rb-dec-3",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-cyc-3")

        insert_event(conn, "ReviewDueEvent", {
            "cycle_id": "rb-cyc-3",
            "review_due_date": "2026-07-20T00:00:00Z",
            "days_until_due": 0,
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 10,
        }, "rb-cyc-3")

        insert_event(conn, "ReviewOverdueEvent", {
            "cycle_id": "rb-cyc-3",
            "days_overdue": 5,
            "original_due_date": "2026-07-20T00:00:00Z",
            "detected_at": "2026-07-25T12:00:00Z",
            "event_sequence": 20,
        }, "rb-cyc-3")

        repo = PostgresReviewCycleStatusProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_cycle_id("rb-cyc-3")
        assert result.status == "OVERDUE"
        assert result.event_sequence == 20

    def test_rebuild_with_executed_event(self, conn):
        """Created + Executed updates status to EXECUTED."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cyc-4",
            "decision_id": "rb-dec-4",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-cyc-4")

        insert_event(conn, "ReviewExecutedEvent", {
            "review_id": "rb-rec-4",
            "cycle_id": "rb-cyc-4",
            "review_type": "ALLOCATION_REVIEW",
            "actual_outcome": {},
            "variance": {},
            "verdict": "OUTPERFORMED",
            "rationale": "Exceeded",
            "executed_by": "test",
            "executed_at": "2026-06-25T12:00:00Z",
            "event_sequence": 10,
        }, "rb-cyc-4")

        repo = PostgresReviewCycleStatusProjectionRepository(conn)
        repo.rebuild()

        result = repo.get_by_cycle_id("rb-cyc-4")
        assert result.status == "EXECUTED"
        assert result.review_id == "rb-rec-4"
        assert result.executed_at is not None

    def test_rebuild_deterministic(self, conn):
        """Rebuilding twice produces identical results."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cyc-det",
            "decision_id": "rb-dec-det",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-cyc-det")

        repo = PostgresReviewCycleStatusProjectionRepository(conn)

        # First rebuild
        repo.rebuild()
        first = repo.get_by_cycle_id("rb-cyc-det")

        # Second rebuild
        repo.rebuild()
        second = repo.get_by_cycle_id("rb-cyc-det")

        assert first.status == second.status
        assert first.event_sequence == second.event_sequence

    def test_rebuild_idempotent(self, conn):
        """Rebuilding multiple times produces same result."""
        from karsa.review.infrastructure.postgres_review_cycle_status_projection_repository import PostgresReviewCycleStatusProjectionRepository

        insert_event(conn, "ReviewCycleCreatedEvent", {
            "cycle_id": "rb-cyc-idem",
            "decision_id": "rb-dec-idem",
            "proposal_id": "p1",
            "journal_ref": "j1",
            "review_type": "ALLOCATION_REVIEW",
            "decision_snapshot": {},
            "schedule_policy": {},
            "review_template": {},
            "eligibility_event_ref": "e1",
            "created_by": "test",
            "created_at": "2026-06-20T12:00:00Z",
            "event_sequence": 1,
        }, "rb-cyc-idem")

        repo = PostgresReviewCycleStatusProjectionRepository(conn)

        repo.rebuild()
        repo.rebuild()
        repo.rebuild()

        results = repo.list_by_status("CREATED")
        idem_results = [r for r in results if r.cycle_id == "rb-cyc-idem"]
        assert len(idem_results) == 1
