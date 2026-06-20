"""sprint07 review_cycles

Revision ID: 71
Revises: 70
Create Date: 2026-06-20

"""
from alembic import op

revision = '71'
down_revision = '70'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review cycles — write-once ledger entry
    op.execute("""
    CREATE TABLE review_cycles (
        cycle_id VARCHAR(64) PRIMARY KEY,
        decision_id VARCHAR(64) NOT NULL,
        proposal_id VARCHAR(64),
        journal_ref VARCHAR(64) NOT NULL,
        review_type VARCHAR(32) NOT NULL,
        decision_snapshot JSONB NOT NULL,
        schedule_policy JSONB NOT NULL,
        review_template JSONB NOT NULL,
        eligibility_event_ref VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        created_by VARCHAR(64) NOT NULL
    );
    """)

    op.execute("COMMENT ON TABLE review_cycles IS 'Write-once ledger entry for review cycles. Created when a CIO Decision passes eligibility review.';")
    op.execute("COMMENT ON COLUMN review_cycles.decision_snapshot IS 'Immutable DecisionSnapshot JSONB captured at cycle creation.';")
    op.execute("COMMENT ON COLUMN review_cycles.schedule_policy IS 'SchedulePolicy value object as JSONB.';")
    op.execute("COMMENT ON COLUMN review_cycles.review_template IS 'ReviewTemplate value object as JSONB.';")

    # Indexes
    op.execute("CREATE INDEX ix_review_cycles_decision_id ON review_cycles(decision_id);")
    op.execute("CREATE INDEX ix_review_cycles_proposal_id ON review_cycles(proposal_id);")
    op.execute("CREATE INDEX ix_review_cycles_created_at ON review_cycles(created_at);")

    # Immutability trigger
    op.execute("""
    CREATE OR REPLACE FUNCTION block_review_cycles_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'review_cycles is immutable';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_block_review_cycles_update
        BEFORE UPDATE ON review_cycles
        FOR EACH ROW EXECUTE FUNCTION block_review_cycles_mutation();
    """)

    op.execute("""
    CREATE TRIGGER trg_block_review_cycles_delete
        BEFORE DELETE ON review_cycles
        FOR EACH ROW EXECUTE FUNCTION block_review_cycles_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_review_cycles_delete ON review_cycles;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_review_cycles_update ON review_cycles;")
    op.execute("DROP FUNCTION IF EXISTS block_review_cycles_mutation();")
    op.execute("DROP TABLE IF EXISTS review_cycles;")
