"""sprint07 capability_score_adjustments

Revision ID: 74
Revises: 72
Create Date: 2026-06-20

"""
from alembic import op

revision = '74'
down_revision = '73'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Capability score adjustments — write-once, delta only
    op.execute("""
    CREATE TABLE capability_score_adjustments (
        adjustment_id VARCHAR(64) PRIMARY KEY,
        target_urn VARCHAR(256) NOT NULL,
        target_type VARCHAR(32) NOT NULL,
        score_delta NUMERIC(10, 6) NOT NULL,
        confidence_delta NUMERIC(6, 4) NOT NULL,
        review_id VARCHAR(64) NOT NULL,
        rationale TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT fk_capability_score_adj_review
            FOREIGN KEY (review_id) REFERENCES review_records(review_id)
    );
    """)

    op.execute("COMMENT ON TABLE capability_score_adjustments IS 'Write-once ledger entry for capability score adjustments. Stores only deltas. Current score derived from projection.';")
    op.execute("COMMENT ON COLUMN capability_score_adjustments.target_type IS 'WORKER, THESIS, or STRATEGY.';")
    op.execute("COMMENT ON COLUMN capability_score_adjustments.score_delta IS 'Score change in decimal. Positive = improvement, negative = degradation.';")

    # Indexes
    op.execute("CREATE INDEX ix_capability_score_adj_target_urn ON capability_score_adjustments(target_urn);")
    op.execute("CREATE INDEX ix_capability_score_adj_review_id ON capability_score_adjustments(review_id);")
    op.execute("CREATE INDEX ix_capability_score_adj_created_at ON capability_score_adjustments(created_at);")

    # Immutability trigger
    op.execute("""
    CREATE OR REPLACE FUNCTION block_capability_score_adj_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'capability_score_adjustments is immutable';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_block_capability_score_adj_update
        BEFORE UPDATE ON capability_score_adjustments
        FOR EACH ROW EXECUTE FUNCTION block_capability_score_adj_mutation();
    """)

    op.execute("""
    CREATE TRIGGER trg_block_capability_score_adj_delete
        BEFORE DELETE ON capability_score_adjustments
        FOR EACH ROW EXECUTE FUNCTION block_capability_score_adj_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_capability_score_adj_delete ON capability_score_adjustments;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_capability_score_adj_update ON capability_score_adjustments;")
    op.execute("DROP FUNCTION IF EXISTS block_capability_score_adj_mutation();")
    op.execute("DROP TABLE IF EXISTS capability_score_adjustments;")
