"""sprint07 review_records

Revision ID: 72
Revises: 71
Create Date: 2026-06-20

"""
from alembic import op

revision = '72'
down_revision = '71'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review records — write-once ledger entry
    op.execute("""
    CREATE TABLE review_records (
        review_id VARCHAR(64) PRIMARY KEY,
        cycle_id VARCHAR(64) NOT NULL,
        review_type VARCHAR(32) NOT NULL,
        decision_snapshot JSONB NOT NULL,
        actual_outcome JSONB NOT NULL,
        variance JSONB NOT NULL,
        verdict VARCHAR(32) NOT NULL,
        rationale TEXT NOT NULL,
        executed_at TIMESTAMPTZ NOT NULL,
        executed_by VARCHAR(64) NOT NULL,
        evidence_refs JSONB DEFAULT '[]'::jsonb,
        CONSTRAINT fk_review_records_cycle
            FOREIGN KEY (cycle_id) REFERENCES review_cycles(cycle_id)
    );
    """)

    op.execute("COMMENT ON TABLE review_records IS 'Write-once ledger entry for review executions. Created when a review is executed against actual outcomes.';")
    op.execute("COMMENT ON COLUMN review_records.actual_outcome IS 'ActualOutcomeSnapshot JSONB from PerformanceEvaluationCompletedEvent.';")
    op.execute("COMMENT ON COLUMN review_records.variance IS 'VarianceAnalysis JSONB computed from expected vs actual.';")

    # Indexes
    op.execute("CREATE INDEX ix_review_records_cycle_id ON review_records(cycle_id);")
    op.execute("CREATE INDEX ix_review_records_verdict ON review_records(verdict);")
    op.execute("CREATE INDEX ix_review_records_executed_at ON review_records(executed_at);")

    # Immutability trigger
    op.execute("""
    CREATE OR REPLACE FUNCTION block_review_records_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'review_records is immutable';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_block_review_records_update
        BEFORE UPDATE ON review_records
        FOR EACH ROW EXECUTE FUNCTION block_review_records_mutation();
    """)

    op.execute("""
    CREATE TRIGGER trg_block_review_records_delete
        BEFORE DELETE ON review_records
        FOR EACH ROW EXECUTE FUNCTION block_review_records_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_review_records_delete ON review_records;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_review_records_update ON review_records;")
    op.execute("DROP FUNCTION IF EXISTS block_review_records_mutation();")
    op.execute("DROP TABLE IF EXISTS review_records;")
